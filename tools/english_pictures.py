#!/usr/bin/env python3
"""Portraits for the English library's authors, and better covers where
Wikidata has a picture of the work itself — copied onto our own site.

  * every author of an English-library book (lang "en") that has no portrait:
    Wikidata's image (P18) of the person with that name (a human, and the
    life years must agree when Gutenberg gave them), resized to 500 px into
    public/books/img/au-<id>.jpg; listed in src/authors-en.json, which
    src/authors.js merges into its AUTHORS
  * every English-library book whose cover is Gutenberg's (img/pg<N>.jpg,
    often just the title printed on a plain ground): Wikidata's image of the
    literary work (a first edition, a frontispiece), when there is one, the
    same way; the catalogue's cover is pointed at it

Public-domain and free images only (whatever Commons holds under P18).
Resumable; polite to Wikimedia (one request at a time, backing off on 429).

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/english_pictures.py
"""
import hashlib, io, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MANIFEST = "private/books/index.json"
OUT_JSON = "src/authors-en.json"
IMG = "public/books/img"
STATE = "tools/english_pictures_state.json"
UA = "SamovarLibraryImages/1.1 (https://samovar.live; one-off copy of portraits and covers) python-urllib"
WD = "https://www.wikidata.org/w/api.php"
CM = "https://commons.wikimedia.org/w/api.php"
try:
    from PIL import Image
except Exception:
    Image = None

_last = [0.0]


def get(url, tries=6, binary=False):
    for i in range(tries):
        wait = _last[0] + 0.6 - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=60).read()
            return data if binary else json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            ra = 0
            try:
                ra = int(e.headers.get("Retry-After") or 0)
            except Exception:
                pass
            time.sleep(ra or (10 * (i + 1) if e.code == 429 else 3 * (i + 1)))
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def wd_search(text, extra=""):
    q = urllib.parse.urlencode({"action": "query", "list": "search", "format": "json", "srlimit": 5,
                                "srsearch": (text + " " + extra).strip()})
    j = get(WD + "?" + q)
    return [h["title"] for h in ((j or {}).get("query", {}).get("search") or [])]


def wd_entities(ids):
    if not ids:
        return {}
    q = urllib.parse.urlencode({"action": "wbgetentities", "format": "json", "ids": "|".join(ids),
                                "props": "claims|labels", "languages": "en"})
    j = get(WD + "?" + q)
    return (j or {}).get("entities") or {}


def claim_vals(ent, p):
    out = []
    for c in (ent.get("claims") or {}).get(p, []):
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if v is not None:
            out.append(v)
    return out


def year_of(v):
    m = re.match(r"[+-]?(\d{1,4})-", (v or {}).get("time", ""))
    return int(m.group(1)) if m else None


def save_thumb(filename, prefix, width=500):
    name = "%s-%s.jpg" % (prefix, hashlib.sha1(filename.encode("utf-8")).hexdigest()[:14])
    path = os.path.join(IMG, name)
    if os.path.exists(path):
        return "img/" + name
    q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url",
                                "iiurlwidth": width, "titles": "File:" + filename})
    j = get(CM + "?" + q)
    try:
        ii = list(j["query"]["pages"].values())[0]["imageinfo"][0]
        url = ii.get("thumburl") or ii["url"]
    except Exception:
        return None
    data = get(url, binary=True)
    if not data:
        return None
    os.makedirs(IMG, exist_ok=True)
    try:
        if Image is None:
            raise RuntimeError
        im = Image.open(io.BytesIO(data)).convert("RGB")
        if im.width > width:
            im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
        im.save(path, "JPEG", quality=82, optimize=True, progressive=True)
    except Exception:
        open(path, "wb").write(data)
    return "img/" + name


def main():
    state = json.load(io.open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"authors": {}, "works": {}}
    out = json.load(io.open(OUT_JSON, encoding="utf-8")) if os.path.exists(OUT_JSON) else {}
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    en = [b for b in idx if b.get("lang") == "en"]
    src = io.open("src/authors.js", encoding="utf-8").read()
    have = set(re.findall(r'AUTHORS\["([^"]+)"\]', src)) | set(re.findall(r'^\s+"([^"]+)":\s*\{', src, re.M))
    # Writers the Russian side already pictures, by their English name.
    ru_en = {re.sub(r"\s*\(.*\)", "", b.get("enAuthor") or "").strip() for b in idx if b.get("lang") != "en"}

    authors = {}
    for b in en:
        a = (b.get("author") or "").strip()
        if a and a not in have and a not in ru_en:
            authors.setdefault(a, b.get("authorYears") or "")
    print("%d authors to picture" % len(authors), flush=True)
    for i, (a, years) in enumerate(sorted(authors.items()), 1):
        if a in state["authors"]:
            continue
        ys = [int(y) for y in re.findall(r"\d{3,4}", years)]
        found = None
        ids = wd_search('"%s"' % a, "haswbstatement:P31=Q5")[:5] or wd_search(a, "haswbstatement:P31=Q5")[:5]
        ents = wd_entities(ids)
        for qid in ids:
            e = ents.get(qid) or {}
            born = year_of((claim_vals(e, "P569") or [None])[0])
            died = year_of((claim_vals(e, "P570") or [None])[0])
            if ys and born and abs(born - ys[0]) > 2:
                continue
            if len(ys) > 1 and died and abs(died - ys[1]) > 2:
                continue
            imgs = claim_vals(e, "P18")
            if imgs:
                found = (imgs[0], born, died)
                break
        rec = None
        if found:
            path = save_thumb(found[0], "au")
            if path:
                y = years or ("%s–%s" % (found[1] or "", found[2] or "")).strip("–")
                rec = {"name": a, "years": y, "file": "/books/" + path}
                out[a] = rec
        state["authors"][a] = bool(rec)
        print("[%d/%d] %-40s %s" % (i, len(authors), a[:40], "portrait" if rec else "—"), flush=True)
        if i % 10 == 0:
            io.open(OUT_JSON, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
            io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))
    io.open(OUT_JSON, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))

    # Works: a picture of the book itself in place of Gutenberg's plain cover.
    changes = {}
    todo = [b for b in en if re.match(r"^img/pg\d+\.jpg$", b.get("cover") or "")]
    print("\n%d books with Gutenberg's cover" % len(todo), flush=True)
    for i, b in enumerate(todo, 1):
        s = b["slug"]
        if s in state["works"]:
            if state["works"][s]:
                changes[s] = state["works"][s]
            continue
        surname = (b.get("author") or "").split()[-1] if b.get("author") else ""
        ids = wd_search('"%s"' % b["title"], surname)[:5]
        ents = wd_entities(ids)
        pic = None
        for qid in ids:
            e = ents.get(qid) or {}
            label = (((e.get("labels") or {}).get("en") or {}).get("value") or "").lower()
            if not label or label.split(":")[0].strip() != b["title"].lower().split(":")[0].strip():
                continue
            imgs = [x for x in claim_vals(e, "P18") if not re.search(r"\.(svg|webm|ogv|pdf|djvu|tif)$", x, re.I)]
            if imgs:
                pic = imgs[0]
                break
        path = save_thumb(pic, "wk") if pic else None
        state["works"][s] = path or ""
        if path:
            changes[s] = path
        print("[%d/%d] %-45s %s" % (i, len(todo), b["title"][:45], "picture" if path else "—"), flush=True)
        if i % 10 == 0:
            io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))
    fresh = json.load(io.open(MANIFEST, encoding="utf-8"))
    for b in fresh:
        if b.get("slug") in changes and changes[b["slug"]]:
            b["coverGutenberg"] = b.get("coverGutenberg") or b.get("cover")
            b["cover"] = changes[b["slug"]]
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(fresh, ensure_ascii=False, indent=2) + "\n")
    print("\nDone: %d author portraits, %d book pictures." % (len(out), len([c for c in changes.values() if c])))


if __name__ == "__main__":
    main()
