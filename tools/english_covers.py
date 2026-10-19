#!/usr/bin/env python3
"""Better covers for the English library: paintings and illustrations of
scenes from each book, and stills or posters from its silent-era films, in
place of Project Gutenberg's plain printed covers.

Public domain and CC0 only — every candidate's licence is read from Commons
and anything else is passed over. (That rules out stills from modern films;
films made before 1930 are public domain in the US and many have stills.)

Where it looks, for each English-library book:
  1. Wikidata: the work itself (found by title + author) — its picture, its
     Commons category and that category's subcategories of illustrations,
     paintings, scenes and films.
  2. Wikidata: films based on the work released before 1930 — their posters,
     stills and Commons categories.
  3. Commons search: the title with "painting", "illustration", "film".
Candidates are scored on where they came from and on their filenames (title
pages, covers, maps, text and author portraits lose), then the best few are
downloaded small and judged by eye-like measures — colour, contrast, how much
of the picture is blank paper — and the winner is saved 700 px wide into
public/books/img/cv-<hash>.jpg and set as the book's cover. The Gutenberg
cover's path is kept as coverGutenberg.

It also writes a review page, private/cover_review/index.html: every book
with its pick and the runners-up. Open it in a browser, click a different
picture (or "Keep Gutenberg") wherever you prefer one, press "Save choices",
then:
    python3 tools/english_covers.py --apply /mnt/c/Users/david/Downloads/cover_choices.json

Resumable. One request at a time, backing off on 429.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/english_covers.py              # all books still on a Gutenberg cover
    python3 tools/english_covers.py --slug cranford --redo
"""
import argparse, hashlib, html, io, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MANIFEST = "private/books/index.json"
IMG = "public/books/img"
STATE = "tools/english_covers_state.json"
REVIEW = "private/cover_review"
UA = "SamovarLibraryCovers/1.0 (https://samovar.live; public-domain book covers) python-urllib"
CM = "https://commons.wikimedia.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
try:
    from PIL import Image, ImageStat
except Exception:
    print("Needs Pillow:  pip3 install --break-system-packages pillow"); sys.exit(1)

_last = [0.0]


def get(url, tries=6, binary=False, gap=0.5):
    for i in range(tries):
        wait = _last[0] + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json" if not binary else "*/*"})
            data = urllib.request.urlopen(req, timeout=60).read()
            return data if binary else json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404):
                return None
            ra = 0
            try:
                ra = int(e.headers.get("Retry-After") or 0)
            except Exception:
                pass
            time.sleep(ra or (15 * (i + 1) if e.code == 429 else 4 * (i + 1)))
        except Exception:
            time.sleep(4 * (i + 1))
    return None


def sparql(q):
    j = get(SPARQL + "?" + urllib.parse.urlencode({"query": q, "format": "json"}), gap=1.0)
    return ((j or {}).get("results") or {}).get("bindings") or []


def short_title(t):
    t = re.sub(r"\s*[—–-]+\s*(Complete|Volume.*|Vol\..*)$", "", t or "", flags=re.I)
    t = re.sub(r",?\s*\(?(Illustrated|Unabridged|Complete)\)?$", "", t, flags=re.I)
    t = re.split(r"\s*[:;]\s*|,\s+(?:or|and)\s+|\s+\(", t)[0]
    t = re.sub(r",.*$", "", t) if len(t) > 40 else t
    return t.strip(" .,")


def surname(a):
    a = re.sub(r"\(.*?\)", "", a or "").strip()
    parts = [p for p in re.split(r"\s+", a) if p and not re.match(r"^(jr|sr|ii|iii)\.?$", p, re.I)]
    return parts[-1].strip(".,") if parts else ""


def file_of(url_or_name):
    s = urllib.parse.unquote(str(url_or_name))
    s = s.rsplit("/", 1)[-1] if "/" in s else s
    return s.replace("_", " ").replace("File:", "")


# ── Wikidata ────────────────────────────────────────────────────────────────
def find_work(title, author):
    sn = surname(author).lower()
    q = """SELECT ?w ?img ?cat WHERE {
  SERVICE wikibase:mwapi { bd:serviceParam wikibase:endpoint "www.wikidata.org";
    wikibase:api "EntitySearch"; mwapi:search "%s"; mwapi:language "en".
    ?w wikibase:apiOutputItem mwapi:item. }
  ?w wdt:P50 ?a. ?a rdfs:label ?al. FILTER(LANG(?al) = "en")
  FILTER(CONTAINS(LCASE(?al), "%s"))
  OPTIONAL { ?w wdt:P18 ?img }
  OPTIONAL { ?w wdt:P373 ?cat }
} LIMIT 10""" % (title.replace('"', ''), sn.replace('"', ''))
    rows = sparql(q)
    if not rows:
        return None
    qid = rows[0]["w"]["value"].rsplit("/", 1)[-1]
    imgs = sorted({file_of(r["img"]["value"]) for r in rows if r["w"]["value"].endswith(qid) and "img" in r})
    cats = sorted({r["cat"]["value"] for r in rows if r["w"]["value"].endswith(qid) and "cat" in r})
    return {"qid": qid, "imgs": imgs, "cats": cats}


def silent_films(qid):
    q = """SELECT ?f ?d ?img ?cat WHERE {
  ?f wdt:P144 wd:%s; wdt:P31/wdt:P279* wd:Q11424; wdt:P577 ?d.
  FILTER(YEAR(?d) < 1930)
  OPTIONAL { ?f wdt:P18 ?img } OPTIONAL { ?f wdt:P373 ?cat }
} LIMIT 30""" % qid
    imgs, cats = set(), set()
    for r in sparql(q):
        if "img" in r: imgs.add(file_of(r["img"]["value"]))
        if "cat" in r: cats.add(r["cat"]["value"])
    return sorted(imgs), sorted(cats)


# ── Commons ─────────────────────────────────────────────────────────────────
GOOD_SUB = re.compile(r"illustrat|painting|scene|film|still|art\b|artwork|depict|adaptation|engraving|drawing|lithograph|poster|frontispiece|characters", re.I)


def cat_files(cat, depth=1, limit=80):
    out = []
    q = urllib.parse.urlencode({"action": "query", "format": "json", "list": "categorymembers",
                                "cmtitle": "Category:" + cat, "cmtype": "file|subcat", "cmlimit": 200})
    j = get(CM + "?" + q)
    subs = []
    for m in ((j or {}).get("query") or {}).get("categorymembers") or []:
        t = m.get("title", "")
        if t.startswith("File:"):
            out.append(t[5:])
        elif t.startswith("Category:") and depth > 0 and GOOD_SUB.search(t):
            subs.append(t[9:])
    for s in subs[:6]:
        out += cat_files(s, depth - 1, limit)
    return out[:limit]


def commons_search(text, n=20):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "list": "search", "srnamespace": 6,
                                "srlimit": n, "srsearch": text + " filetype:bitmap"})
    j = get(CM + "?" + q)
    return [h["title"][5:] for h in ((j or {}).get("query") or {}).get("search") or []]


FREE = re.compile(r"public\s*domain|^pd\b|^pd-|cc0|cc[- ]zero|no restrictions", re.I)


def infos(files):
    out = {}
    files = list(dict.fromkeys(files))
    for i in range(0, len(files), 40):
        q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo",
                                    "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 360,
                                    "iiextmetadatafilter": "LicenseShortName|License|ImageDescription|Categories",
                                    "titles": "|".join("File:" + f for f in files[i:i + 40])})
        j = get(CM + "?" + q)
        for p in (((j or {}).get("query") or {}).get("pages") or {}).values():
            ii = (p.get("imageinfo") or [None])[0]
            if not ii:
                continue
            em = ii.get("extmetadata") or {}
            lic = ((em.get("LicenseShortName") or {}).get("value") or "") + " " + ((em.get("License") or {}).get("value") or "")
            out[p["title"][5:]] = {
                "w": ii.get("width") or 0, "h": ii.get("height") or 0, "mime": ii.get("mime") or "",
                "thumb": ii.get("thumburl") or ii.get("url"), "url": ii.get("url"),
                "free": bool(FREE.search(lic)), "lic": lic.strip()[:60],
                "desc": re.sub(r"<[^>]+>", " ", (em.get("ImageDescription") or {}).get("value") or "")[:300],
                "cats": (em.get("Categories") or {}).get("value") or "",
            }
    return out


BAD = re.compile(r"title[ _-]?page|titlepage|\bcover\b|dust ?jacket|\bpage\b|\bp\. ?\d|\bpp?\d{2,}|\btext\b|\bletter\b|manuscript|\bmap\b|signature|autograph|\bgrave\b|plaque|stamp|\bcoin\b|logo|first edition|\bedition\b|advert|\bspine\b|binding|bookplate|\bscan\b|\bocr\b|\bpdf\b|djvu|\bchart\b|diagram|\bhouse\b|birthplace|memorial|tomb|\bstatue\b", re.I)
PORTRAIT = re.compile(r"portrait|photograph of|\bphoto\b|daguerreotype|carte de visite", re.I)
NICE = re.compile(r"painting|oil on|canvas|watercolou?r|illustrat|scene|\bstill\b|film|poster|lobby card|engraving|plate|drawing|etching|gouache|tempera", re.I)


def meta_score(name, info, src_bonus, title, sn, searched=False):
    if not info or not info["free"]:
        return None
    if searched:
        # A bare search hit is only trusted when it names the author, or sits
        # in a Commons category named for the book — otherwise "Cranford"
        # finds Cranford, New Jersey and "Walden" a painting of phlox.
        blob = (name + " " + info["desc"] + " " + info["cats"]).lower()
        bookcat = any(title.lower() in c.lower() and re.search(r"novel|book|illustrat|film|play|poem|story|stories|tale", c, re.I)
                      for c in info["cats"].split("|"))
        if not ((sn and sn.lower() in blob) or bookcat):
            return None
    if not re.match(r"image/(jpeg|png|webp)", info["mime"]):
        return None
    w, h = info["w"], info["h"]
    if w < 380 or h < 380:
        return None
    ar = w / float(h)
    if ar > 2.4 or ar < 0.35:
        return None
    text = name + " " + info["desc"] + " " + info["cats"]
    s = src_bonus
    if BAD.search(name):
        s -= 6
    if re.search(r"houghton|\bfolio\b|\bleaf\b|\bp \d+\b|photograph of a|aerial|\bsite\b", name, re.I):
        s -= 3
    if PORTRAIT.search(name) and sn and sn.lower() in name.lower():
        s -= 6
    if NICE.search(text):
        s += 2
    if re.search(r"film|still|poster|lobby", text, re.I):
        s += 1.5
    tw = [x for x in re.findall(r"[a-z]{4,}", title.lower()) if x not in ("that", "with", "from", "this", "their", "complete", "adventures")]
    if tw and any(x in text.lower() for x in tw):
        s += 1.5
    s += min(2.0, (w * h) / 2.0e6)            # resolution, up to +2
    if 0.6 <= ar <= 1.5:
        s += 0.8
    return s


def look(data):
    """How the picture looks: colour, contrast, and how much is blank paper."""
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None
    sm = im.resize((64, 64))
    px = list(sm.get_flattened_data()) if hasattr(sm, "get_flattened_data") else list(sm.getdata())
    rg = [abs(r - g) for r, g, b in px]
    yb = [abs(0.5 * (r + g) - b) for r, g, b in px]
    mean = lambda a: sum(a) / float(len(a))
    sd = lambda a: (sum((x - mean(a)) ** 2 for x in a) / len(a)) ** 0.5
    colourful = (sd(rg) ** 2 + sd(yb) ** 2) ** 0.5 + 0.3 * (mean(rg) ** 2 + mean(yb) ** 2) ** 0.5
    grey = ImageStat.Stat(sm.convert("L"))
    contrast = grey.stddev[0]
    paper = sum(1 for r, g, b in px if r > 225 and g > 220 and b > 205) / float(len(px))
    dark = sum(1 for r, g, b in px if r + g + b < 45) / float(len(px))
    return colourful * 0.06 + contrast * 0.035 - paper * 4.0 - max(0, dark - 0.5) * 3


def save_cover(name, info, width=700):
    out = "cv-%s.jpg" % hashlib.sha1(name.encode("utf-8")).hexdigest()[:14]
    path = os.path.join(IMG, out)
    if os.path.exists(path):
        return "img/" + out
    q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url",
                                "iiurlwidth": min(width * 2, max(width, info.get("w") or width)), "titles": "File:" + name})
    j = get(CM + "?" + q)
    try:
        ii = list(j["query"]["pages"].values())[0]["imageinfo"][0]
        url = ii.get("thumburl") or ii["url"]
    except Exception:
        return None
    data = get(url, binary=True)
    if not data:
        return None
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        if im.width > width:
            im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
        os.makedirs(IMG, exist_ok=True)
        im.save(path, "JPEG", quality=84, optimize=True, progressive=True)
    except Exception:
        return None
    return "img/" + out


def candidates_for(b):
    title = short_title(b.get("title") or "")
    author = b.get("author") or ""
    sn = surname(author)
    pool = {}                                   # name -> source bonus
    searched = set()                            # names found only by search

    def add(names, bonus, by_search=False):
        for n in names:
            if by_search and n not in pool:
                searched.add(n)
            elif not by_search:
                searched.discard(n)
            pool[n] = max(pool.get(n, -99), bonus)

    work = find_work(title, author)
    if work:
        add(work["imgs"], 1.0)                  # often a first edition — fine as a fallback
        for c in work["cats"]:
            add(cat_files(c), 2.0)
        fi, fc = silent_films(work["qid"])
        add(fi, 4.0)
        for c in fc:
            add(cat_files(c), 3.5)
    add(commons_search('"%s" %s painting' % (title, sn)), 1.5, True)
    add(commons_search('"%s" %s illustration' % (title, sn)), 1.5, True)
    add(commons_search('"%s" film still' % title, 12), 1.0, True)
    if not pool:
        return title, []
    inf = infos(list(pool.keys())[:160])
    scored = []
    for n, bonus in pool.items():
        s = meta_score(n, inf.get(n), bonus, title, sn, n in searched)
        if s is not None:
            scored.append((s, n))
    scored.sort(reverse=True)
    out = []
    os.makedirs(os.path.join(REVIEW, "c"), exist_ok=True)
    for s, n in scored[:7]:
        data = get(inf[n]["thumb"], binary=True)
        if not data:
            continue
        v = look(data)
        if v is None:
            continue
        th = "c/%s.jpg" % hashlib.sha1(n.encode("utf-8")).hexdigest()[:14]
        try:
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.thumbnail((300, 400))
            im.save(os.path.join(REVIEW, th), "JPEG", quality=78)
        except Exception:
            continue
        out.append({"file": n, "score": round(s + v, 2), "meta": round(s, 2), "look": round(v, 2),
                    "w": inf[n]["w"], "h": inf[n]["h"], "lic": inf[n]["lic"], "thumb": th})
    out.sort(key=lambda c: -c["score"])
    return title, out


def write_review(state, books):
    rows = []
    for b in books:
        st = state.get(b["slug"])
        if not st:
            continue
        cands = st.get("cands") or []
        pick = st.get("pick")
        gut = b.get("coverGutenberg") or (b.get("cover") if (b.get("cover") or "").startswith("img/pg") else "")
        cells = []
        if gut:
            cells.append('<label class="c%s"><input type="radio" name="%s" value="__gutenberg__"%s><img src="../../public/books/%s"><span>Keep Gutenberg</span></label>' % (
                "" if pick else " on", html.escape(b["slug"]), "" if pick else " checked", html.escape(gut)))
        for c in cands:
            on = c["file"] == pick
            cells.append('<label class="c%s"><input type="radio" name="%s" value="%s"%s><img src="%s" loading="lazy"><span>%s · %s</span></label>' % (
                " on" if on else "", html.escape(b["slug"]), html.escape(c["file"], quote=True), " checked" if on else "",
                html.escape(c["thumb"]), c["score"], html.escape(c["file"][:60])))
        rows.append('<section><h2>%s <small>%s</small></h2><div class="row">%s</div></section>' % (
            html.escape(b.get("title") or ""), html.escape(b.get("author") or ""), "".join(cells)))
    page = """<!doctype html><meta charset="utf-8"><title>Cover review</title>
<style>body{font:14px system-ui;background:#1b1712;color:#eee;margin:0;padding:20px 24px}
h1{font-weight:600}h2{font:600 17px Georgia,serif;margin:22px 0 8px}h2 small{font-weight:400;opacity:.6}
.row{display:flex;gap:10px;overflow-x:auto;padding-bottom:6px}
label{flex:0 0 150px;cursor:pointer;border:3px solid transparent;border-radius:6px;background:#2a241c;padding:4px}
label.on{border-color:#e0a040}label img{width:100%;aspect-ratio:3/4;object-fit:cover;display:block;border-radius:3px}
label span{display:block;font-size:11px;opacity:.65;margin-top:4px;word-break:break-all}input{display:none}
#bar{position:sticky;top:0;background:#1b1712;padding:10px 0;z-index:2;border-bottom:1px solid #444}
button{font:600 14px system-ui;padding:9px 16px;border-radius:6px;border:0;background:#e0a040;cursor:pointer}</style>
<div id="bar"><h1 style="display:inline;margin-right:16px">Cover review</h1>
<button onclick="save()">Save choices</button> <span id="n"></span></div>
%%ROWS%%
<script>
document.addEventListener('change',function(e){var r=e.target;if(r.type!=='radio')return;
document.querySelectorAll('input[name="'+CSS.escape(r.name)+'"]').forEach(function(x){x.parentNode.classList.toggle('on',x.checked)});});
function save(){var o={};document.querySelectorAll('input[type=radio]:checked').forEach(function(x){o[x.name]=x.value});
var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(o,null,1)],{type:'application/json'}));
a.download='cover_choices.json';a.click();document.getElementById('n').textContent='Saved '+Object.keys(o).length+' choices to Downloads.';}
</script>""".replace("%%ROWS%%", "\n".join(rows))
    os.makedirs(REVIEW, exist_ok=True)
    io.open(os.path.join(REVIEW, "index.html"), "w", encoding="utf-8").write(page)


def set_covers(changes):
    fresh = json.load(io.open(MANIFEST, encoding="utf-8"))
    for b in fresh:
        s = b.get("slug")
        if s not in changes:
            continue
        new = changes[s]
        gut = b.get("coverGutenberg") or (b.get("cover") if re.match(r"^img/(pg|wk-)", b.get("cover") or "") else "")
        if new == "__gutenberg__":
            if b.get("coverGutenberg"):
                b["cover"] = b["coverGutenberg"]
            continue
        if gut and not b.get("coverGutenberg"):
            b["coverGutenberg"] = gut
        b["cover"] = new
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(fresh, ensure_ascii=False, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--apply", help="cover_choices.json saved from the review page")
    ap.add_argument("--min-score", type=float, default=3.0, help="below this, keep Gutenberg's cover")
    a = ap.parse_args()
    state = json.load(io.open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    books = [b for b in idx if b.get("lang") == "en"]

    if a.apply:
        choices = json.load(io.open(a.apply, encoding="utf-8"))
        changes = {}
        for slug, f in choices.items():
            st = state.get(slug)
            if not st or f == st.get("pick") or (f == "__gutenberg__" and not st.get("pick")):
                continue
            if f == "__gutenberg__":
                changes[slug] = f; st["pick"] = None; continue
            c = next((c for c in st.get("cands") or [] if c["file"] == f), None)
            path = save_cover(f, c or {})
            if path:
                changes[slug] = path; st["pick"] = f
                print("%-40s → %s" % (slug[:40], f[:60]), flush=True)
        set_covers(changes)
        io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))
        write_review(state, json.load(io.open(MANIFEST, encoding="utf-8")))
        print("Applied %d change(s)." % len(changes))
        return

    todo = [b for b in books if (not a.slug or b["slug"] == a.slug)
            and (a.slug or re.match(r"^img/(pg|wk-|cv-)", b.get("cover") or ""))
            and (a.redo or b["slug"] not in state)]
    if a.max:
        todo = todo[:a.max]
    print("%d book(s) to find pictures for" % len(todo), flush=True)
    changes, got = {}, 0
    for i, b in enumerate(todo, 1):
        try:
            title, cands = candidates_for(b)
        except Exception as e:
            print("[%d/%d] %s — error %s" % (i, len(todo), b.get("title"), e), flush=True)
            continue
        pick = cands[0] if cands and cands[0]["score"] >= a.min_score else None
        path = save_cover(pick["file"], pick) if pick else None
        state[b["slug"]] = {"title": title, "cands": cands, "pick": pick["file"] if path else None}
        if path:
            changes[b["slug"]] = path; got += 1
        elif (b.get("cover") or "").startswith("img/cv-"):
            changes[b["slug"]] = "__gutenberg__"       # an earlier pick no longer stands
        print("[%d/%d] %-42s %s" % (i, len(todo), (b.get("title") or "")[:42],
              ("✓ %s  (%.1f)" % (pick["file"][:50], pick["score"])) if path else
              ("— %d candidate(s), none good enough" % len(cands) if cands else "— nothing found")), flush=True)
        if i % 10 == 0 or i == len(todo):
            set_covers(changes); changes = {}
            io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))
            write_review(state, json.load(io.open(MANIFEST, encoding="utf-8")))
    set_covers(changes)
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))
    write_review(state, json.load(io.open(MANIFEST, encoding="utf-8")))
    print("\nDone: %d new cover(s). Review: private/cover_review/index.html" % got)


if __name__ == "__main__":
    main()
