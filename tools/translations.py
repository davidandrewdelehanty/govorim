#!/usr/bin/env python3
"""The "Translations" shelf: English novels in public-domain Russian translation,
with the English original alongside.

The Russian comes from Russian Wikisource, which hosts only what is public
domain in Russia. tools/translations/list.tsv names one translation per novel,
chosen so that it was printed before 1931 (public domain in the US) and its
translator died by 1955 or is anonymous (public domain in Russia). The English
original comes from Project Gutenberg.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/translations.py --probe     # match Gutenberg ids, read each page's date; fetch nothing else
    python3 tools/translations.py             # build the FB2s + catalogue entries, download the English
    python3 tools/translations.py --only twain-tom-sawyer dickens-chimes

Needs the network (ru.wikisource.org, ws-export.wmcloud.org, gutenberg.org),
so it runs in WSL. Re-running is safe: the Wikisource EPUBs are cached in
.ws-cache/, the Gutenberg catalogue and texts in tools/translations/, and
anything already downloaded is skipped.

What it leaves behind:
  public/books/novel/<slug>.fb2        the Russian, one per novel (category "Translations")
  tools/translations/en/<slug>.txt     the English, Gutenberg plain text
  tools/translations/resolved.json     Gutenberg id + Wikisource date evidence per slug
The pre-reform spelling, the English alignment and the catalogue details
(translator, English title, note) are done afterwards by
tools/translations_build.py, which needs no network.
"""
import csv, io, json, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request

DIR = "tools/translations"
LIST = os.path.join(DIR, "list.tsv")
EN_DIR = os.path.join(DIR, "en")
RESOLVED = os.path.join(DIR, "resolved.json")
CATALOG = os.path.join(DIR, "pg_catalog.csv")
CAT_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
WS_API = "https://ru.wikisource.org/w/api.php"
UA = "govorim-app/1.0 (library import; contact via github)"
COLS = ["slug", "page", "author", "title", "en_title", "en_author", "gid", "translator", "year", "blurb"]


def rows():
    out = []
    with io.open(LIST, encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t"):
            if not r or r[0].startswith("#"):
                continue
            out.append(dict(zip(COLS, (r + [""] * len(COLS))[:len(COLS)])))
    return out


def get(url, tries=4, timeout=120):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"^(the|a|an) ", "", re.sub(r"\s+", " ", s).strip())
    return s


def catalog():
    if not os.path.exists(CATALOG) or os.path.getsize(CATALOG) < 1_000_000:
        print("downloading the Gutenberg catalogue …", flush=True)
        io.open(CATALOG, "wb").write(get(CAT_URL))
    out = []
    with io.open(CATALOG, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("Type") != "Text" or "en" not in (r.get("Language") or "").split("; "):
                continue
            out.append((int(r["Text#"]), r["Title"].replace("\n", " "), r.get("Authors") or ""))
    return out


SURNAME = {"Bulwer-Lytton": "lytton", "Reid": "reid, mayne", "London": "london, jack", "Doyle": "doyle, arthur conan",
           "Twain": "twain", "Carroll": "carroll", "Scott": "scott, walter", "Cooper": "cooper, james fenimore",
           "Stowe": "stowe", "Hardy": "hardy, thomas", "Wells": "wells, h. g.", "Jerome": "jerome, jerome k",
           "Burnett": "burnett, frances hodgson", "Alcott": "alcott, louisa may", "Kipling": "kipling",
           "Conrad": "conrad, joseph", "Haggard": "haggard", "Defoe": "defoe", "Dickens": "dickens",
           "Thackeray": "thackeray", "Marryat": "marryat", "Stevenson": "stevenson, robert louis",
           "Galsworthy": "galsworthy", "Dreiser": "dreiser", "Stoker": "stoker", "Wilde": "wilde",
           "Bellamy": "bellamy", "Trollope": "trollope, anthony"}


def match(row, cat):
    want = norm(row["en_title"])
    sur = SURNAME.get(row["en_author"], row["en_author"].lower())
    best = []
    for gid, title, authors in cat:
        if sur not in authors.lower():
            continue
        t = norm(title)
        if re.search(r"\b(vol(ume)?|part|tome|book) [0-9ivx]+\b", t) and not re.search(r"\b(vol|part)\b", want):
            continue
        if t == want:
            sc = 3
        elif t.startswith(want + " ") or want.startswith(t + " "):
            sc = 2
        elif want in t:
            sc = 1
        else:
            continue
        best.append((-sc, gid, title))
    best.sort()
    return best


def ws_meta(page):
    q = {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
         "titles": page, "redirects": 1, "format": "json", "formatversion": "2"}
    j = json.loads(get(WS_API + "?" + urllib.parse.urlencode(q)).decode("utf-8"))
    p = j["query"]["pages"][0]
    if p.get("missing"):
        return {"missing": True}
    wt = p["revisions"][0]["slots"]["main"]["content"]
    field = lambda k: (re.search(r"\|\s*" + k + r"\s*=([^|}\n]*(?:\{\{[^}]*\}\}[^|}\n]*)*)", wt) or [None, ""])[1].strip()
    src = " ".join([field("ИСТОЧНИК"), field("ДАТАПУБЛИКАЦИИ"), field("ДАТАСОЗДАНИЯ")])
    years = sorted({int(y) for y in re.findall(r"\b(1[789]\d\d|20[0-2]\d)\b", src)})
    return {"translator": field("ПЕРЕВОДЧИК")[:120], "source": src[:200], "years": years}


def probe(sel):
    cat = catalog()
    res = json.load(io.open(RESOLVED, encoding="utf-8")) if os.path.exists(RESOLVED) else {}
    for r in sel:
        m = match(r, cat)
        gid = int(r["gid"]) if r["gid"] else (m[0][1] if m else None)
        gt = next((t for _, g, t in m if g == gid), "(given in list.tsv)" if r["gid"] else "")
        try:
            meta = ws_meta(r["page"])
        except Exception as e:
            meta = {"error": str(e)}
        time.sleep(0.3)
        res[r["slug"]] = {"gid": gid, "gtitle": gt, "alts": [[g, t] for _, g, t in m[1:4]], **meta}
        flag = ""
        if meta.get("missing"):
            flag = "  !! Wikisource page missing"
        elif meta.get("years") and min(meta["years"]) >= 1931:
            flag = "  !! printed %d — not public domain in the US" % min(meta["years"])
        elif not meta.get("years") and not r["year"]:
            flag = "  ?  no date on the page"
        if not gid:
            flag += "  !! no Gutenberg match"
        print("%-28s pg%-6s %-46s ws:%s%s" % (r["slug"], gid or "-", (gt or "")[:46],
              ",".join(map(str, meta.get("years", [])[:3])) or "-", flag), flush=True)
    io.open(RESOLVED, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print("\n→ %s" % RESOLVED)
    return res


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1:] if "--only" in a else None
    sel = [r for r in rows() if not only or r["slug"] in only]
    os.makedirs(EN_DIR, exist_ok=True)
    if "--probe" in a:
        probe(sel); return 0
    res = json.load(io.open(RESOLVED, encoding="utf-8")) if os.path.exists(RESOLVED) else {}
    if any(r["slug"] not in res for r in sel):
        res = probe([r for r in sel if r["slug"] not in res]) or res
        res = json.load(io.open(RESOLVED, encoding="utf-8"))
    keep = []
    for r in sel:
        m = res.get(r["slug"], {})
        if r["gid"]:
            m["gid"] = int(r["gid"])
        # A page often cites the modern reprint it was transcribed from; a
        # first-publication year given in list.tsv overrides that.
        if m.get("missing") or (m.get("years") and min(m["years"]) >= 1931 and not r["year"]):
            print("skip %-28s (%s)" % (r["slug"], "page missing" if m.get("missing") else "printed %d" % min(m["years"])))
            continue
        keep.append(r)

    # 1. The Russian: Wikisource → EPUB → FB2 + catalogue entry, by add_wikisource.py.
    ws_list = os.path.join(DIR, "ws.tsv")
    with io.open(ws_list, "w", encoding="utf-8") as f:
        for r in keep:
            if os.path.exists("public/books/novel/%s.fb2" % r["slug"]) and "--rebuild" not in a:
                continue
            f.write("\t".join([r["slug"], r["page"], r["author"], r["title"], "Translations",
                               r["blurb"]]) + "\n")
    n = sum(1 for _ in io.open(ws_list, encoding="utf-8"))
    extra = []
    # Books whose chapters are subpages the EPUB export never reaches (the
    # main page is a contents or versions page): tools/translations/chapters.json
    # lists their chapter pages in order, and they are fetched one by one.
    chap_file = os.path.join(DIR, "chapters.json")
    chap = json.load(io.open(chap_file, encoding="utf-8")) if os.path.exists(chap_file) else {}
    wanted = {l.split("\t")[0] for l in io.open(ws_list, encoding="utf-8") if l.strip()}
    if any(s in chap for s in wanted):
        sys.path.insert(0, "tools")
        from add_wikisource import api_html
        cache = os.path.join(".ws-cache", "translations")
        os.makedirs(cache, exist_ok=True)
        pages = {}
        for s in sorted(wanted & set(chap)):
            got = []
            for i, t in enumerate(chap[s], 1):
                fp = os.path.join(cache, re.sub(r'[\\/:*?"<>| ]', "_", t) + ".html")
                if os.path.exists(fp) and os.path.getsize(fp) > 200:
                    h = io.open(fp, encoding="utf-8").read()
                else:
                    h = api_html(t)
                    io.open(fp, "w", encoding="utf-8").write(h)
                    time.sleep(0.4)
                got.append({"page": t, "html": h})
                print("\r  %s: %d/%d pages" % (s, i, len(chap[s])), end="", flush=True)
            print()
            pages[s] = got
        pj = os.path.join(DIR, "pages.json")
        io.open(pj, "w", encoding="utf-8").write(json.dumps(pages, ensure_ascii=False))
        extra = ["--html-json", pj]
    if n:
        print("\n== Russian: %d book(s) from Wikisource ==" % n, flush=True)
        subprocess.call([sys.executable, "tools/add_wikisource.py", "--list", ws_list, "--allow-duplicate"] + extra)

    # 2. The English: Gutenberg plain text.
    print("\n== English: Gutenberg ==", flush=True)
    got = miss = 0
    for r in keep:
        gid = (res.get(r["slug"]) or {}).get("gid")
        out = os.path.join(EN_DIR, r["slug"] + ".txt")
        if not gid:
            print("  -- %-28s no Gutenberg id (put one in column 7 of list.tsv)" % r["slug"]); miss += 1; continue
        if os.path.exists(out) and os.path.getsize(out) > 5000:
            got += 1; continue
        try:
            data = None
            for url in ("https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (gid, gid),
                        "https://www.gutenberg.org/ebooks/%d.txt.utf-8" % gid):
                try:
                    data = get(url); break
                except Exception:
                    continue
            if not data:
                raise RuntimeError("no plain text")
            io.open(out, "wb").write(data)
            print("  ok %-28s pg%d  %d KB" % (r["slug"], gid, len(data) // 1024), flush=True)
            got += 1
            time.sleep(1.5)
        except Exception as e:
            print("  !! %-28s pg%d  %s" % (r["slug"], gid, e)); miss += 1
    print("\nEnglish: %d ready, %d missing" % (got, miss))
    print("Next (no network needed): python3 tools/translations_build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
