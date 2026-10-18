#!/usr/bin/env python3
"""Copy every picture the library shows onto our own site, so no tile depends
on Wikimedia Commons answering at the moment a reader opens the library.

Commons limits how fast one site may pull thumbnails from it, and a library
page asks for hundreds at once — which is why many tiles came up broken.

What it does:
  * every catalogue `cover` that points at Commons  → public/books/img/<id>.jpg,
    and the catalogue entry is rewritten to "img/<id>.jpg"
  * every author portrait in src/authors.js and every leader portrait in
    App.jsx's SPEECH_LEADERS → public/books/img/<id>.jpg, listed in
    src/image-map.json, which the site checks before going to Commons

Resized to the size the tiles show (500 px wide; 1200 for the cropped
portraits) and saved as JPEG. Polite to Commons: thumbnail URLs are looked up
50 at a time through the API, then fetched one per second, backing off when
told to. Re-running skips everything already copied.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/localize_images.py
"""
import hashlib, io, json, os, re, sys, threading, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MANIFEST = "private/books/index.json"
OUT = "public/books/img"
MAP = "src/image-map.json"
# Wikimedia throttles anonymous-looking clients hard; a named tool with a way
# to reach its owner is what their robot policy asks for.
UA = "SamovarLibraryImages/1.1 (https://samovar.live; one-off copy of cover thumbnails) python-urllib"
WORKERS = 4
API = "https://commons.wikimedia.org/w/api.php"
try:
    from PIL import Image
except Exception:
    Image = None


class Pace:
    """One shared speed for all workers: quicker while Commons answers,
    halved at every 429, and paused for as long as Retry-After says."""
    def __init__(self):
        self.gap, self.next, self.lock = 0.15, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            t = max(now, self.next)
            self.next = t + self.gap
        time.sleep(max(0.0, t - now))

    def ok(self):
        with self.lock:
            self.gap = max(0.1, self.gap * 0.97)

    def slow(self, pause):
        with self.lock:
            self.gap = min(4.0, self.gap * 2)
            self.next = max(self.next, time.time() + pause)


PACE = Pace()


def get(url, tries=8):
    for i in range(tries):
        PACE.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=60).read()
            PACE.ok()
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            try:
                ra = int(e.headers.get("Retry-After") or 0)
            except Exception:
                ra = 0
            pause = ra or (5 * (i + 1) if e.code == 429 else 2 * (i + 1))
            PACE.slow(pause)
            if e.code == 429 and i == 0:
                print("      429 — slowing to one every %.1fs" % PACE.gap, flush=True)
        except Exception:
            PACE.slow(2 * (i + 1))
    return None


def file_of(url):
    """Commons file name from a Special:FilePath URL."""
    m = re.search(r"Special:FilePath/([^?#]+)", url)
    return urllib.parse.unquote(m.group(1)).replace("_", " ") if m else None


def local_name(f, w):
    return hashlib.sha1(("%s|%d" % (f, w)).encode("utf-8")).hexdigest()[:16] + ".jpg"


def thumb_urls(files, width):
    """{file: thumbnail url} via the API, 50 files a request."""
    out = {}
    files = list(files)
    for i in range(0, len(files), 50):
        chunk = files[i:i + 50]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url",
                                    "iiurlwidth": width, "titles": "|".join("File:" + f for f in chunk)})
        raw = get(API + "?" + q)
        if not raw:
            continue
        j = json.loads(raw)
        back = {n["to"]: n["from"] for n in (j.get("query", {}).get("normalized") or [])}
        for pg in (j.get("query", {}).get("pages") or {}).values():
            title = pg.get("title", "")
            asked = back.get(title, title)[5:]
            ii = (pg.get("imageinfo") or [{}])[0]
            u = ii.get("thumburl") or ii.get("url")
            if u:
                out[asked] = u
    return out


def save(data, path, width):
    if Image is not None:
        try:
            im = Image.open(io.BytesIO(data))
            im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
            im.save(path, "JPEG", quality=82, optimize=True, progressive=True)
            return True
        except Exception:
            pass
    open(path, "wb").write(data)
    return True


def main():
    os.makedirs(OUT, exist_ok=True)
    if Image is None:
        print("(Pillow is not installed: pictures are saved as Commons sends them. "
              "pip install pillow to have them resized)")
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    want = {}                                   # file -> width
    for b in idx:
        c = b.get("cover") or ""
        if c.startswith("http") and "commons.wikimedia.org" in c:
            f = file_of(c)
            if f:
                want[f] = max(want.get(f, 0), 500)
    src = io.open("src/authors.js", encoding="utf-8").read()
    for m in re.finditer(r'"?file"?\s*:\s*"([^"]+)"([^\n]*)', src):
        tail = src[m.end():m.end() + 200]
        cut = min([x for x in (tail.find("AUTHORS["), tail.find('\n  "')) if x >= 0] or [len(tail)])
        crop = "crop" in m.group(2) or "crop" in tail[:cut]
        # Commons serves its standard thumbnail sizes (…, 500, 960, …) from
        # cache and throttles odd sizes; 960 is plenty for a crop.
        want[m.group(1)] = max(want.get(m.group(1), 0), 960 if crop else 500)
    app = io.open("src/App.jsx", encoding="utf-8").read()
    blk = app[app.index("var SPEECH_LEADERS"):app.index("function speechLeaderOf")]
    for m in re.finditer(r'file:\s*"([^"]+)"', blk):
        f = m.group(1).replace("_", " ")
        want[f] = max(want.get(f, 0), 500)
        want.setdefault("__alias__" + m.group(1), 0)
    aliases = {k[9:]: k[9:].replace("_", " ") for k in list(want) if k.startswith("__alias__")}
    for k in [k for k in want if k.startswith("__alias__")]:
        del want[k]

    imap = json.load(io.open(MAP, encoding="utf-8")) if os.path.exists(MAP) else {}
    todo = {f: w for f, w in want.items() if not os.path.exists(os.path.join(OUT, local_name(f, w)))}
    print("%d pictures in use, %d to copy" % (len(want), len(todo)), flush=True)
    by_w = {}
    for f, w in todo.items():
        by_w.setdefault(w, []).append(f)
    got = miss = 0
    done_n = [0]
    lock = threading.Lock()
    for w, files in by_w.items():
        urls = thumb_urls(files, w)

        def one(f):
            u = urls.get(f)
            data = get(u) if u else None
            ok = bool(data) and save(data, os.path.join(OUT, local_name(f, w)), w)
            with lock:
                done_n[0] += 1
                if not ok:
                    print("   !! %s" % f, flush=True)
                if done_n[0] % 50 == 0:
                    print("   %d/%d copied" % (done_n[0], len(todo)), flush=True)
            return ok

        with ThreadPoolExecutor(WORKERS) as ex:
            for ok in ex.map(one, files):
                if ok:
                    got += 1
                else:
                    miss += 1
    # catalogue covers → local paths; portraits → the map
    changed = 0
    for b in idx:
        c = b.get("cover") or ""
        f = file_of(c) if c.startswith("http") else None
        if f and f in want and os.path.exists(os.path.join(OUT, local_name(f, want[f]))):
            b["cover"] = "img/" + local_name(f, want[f])
            changed += 1
    for f, w in want.items():
        p = os.path.join(OUT, local_name(f, w))
        if os.path.exists(p):
            imap[f] = "/books/img/" + local_name(f, w)
    for raw, spaced in aliases.items():
        if spaced in imap:
            imap[raw] = imap[spaced]
    io.open(MAP, "w", encoding="utf-8").write(json.dumps(imap, ensure_ascii=False, indent=0, sort_keys=True))
    # Re-read before writing: another script may have changed the catalogue.
    fresh = json.load(io.open(MANIFEST, encoding="utf-8"))
    newc = {b.get("slug") or b.get("filename"): b.get("cover") for b in idx}
    for b in fresh:
        k = b.get("slug") or b.get("filename")
        c = b.get("cover") or ""
        if c.startswith("http") and (newc.get(k) or "").startswith("img/"):
            b["cover"] = newc[k]
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(fresh, ensure_ascii=False, indent=2) + "\n")
    left = sum(1 for b in fresh if (b.get("cover") or "").startswith("http"))
    print("\ncopied %d, could not get %d; %d covers now ours, %d still on Commons; %d portraits mapped"
          % (got, miss, changed, left, len(imap)))
    if left:
        print("Run it again to pick up the rest — anything already copied is skipped.")


if __name__ == "__main__":
    main()
