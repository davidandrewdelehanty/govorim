#!/usr/bin/env python3
"""Andersen and the Brothers Grimm on the Fairytales shelf (also listed under
Translations), Russian beside English, tale by tale. Runs in WSL (network).

  Андерсен  81 tales in А. В. Ганзен's translation (the classic Russian one,
            1890s), from Russian Wikisource; English: H. P. Paull's
            translation, "Fairy Tales of Hans Christian Andersen" (Gutenberg
            27200).
  Гримм     122 tales in П. Н. Полевой's translation (1890s); English:
            Margaret Hunt's "Household Tales" (1884, Gutenberg 5314), matched
            by the tales' numbers in the Grimms' collection (KHM).

Which tales, which Wikisource page holds each, and the English title or KHM
number for each are in tools/tales_config.json. Tales that Wikisource splits
into parts («Калоши счастья», «Дева льдов») are joined back into one chapter.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/tales.py
    python3 tools/gen_stress_maps.py
    python3 tools/make_case_drills.py --book andersen-skazki.fb2 --min-per-chapter 1
    python3 tools/make_case_drills.py --book grimm-skazki.fb2 --min-per-chapter 1
"""
import html, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from add_wikisource import api_html, API, UA
from reader_chapters import reader_chapters
from translations_build import modernise_fb2

MANIFEST = "private/books/index.json"
BOOKS = "public/books"
CACHE = ".ws-cache/tales"
EN_DIR = "tools/translations/en"
C = lambda f: "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(f.replace(" ", "_")) + "?width=500"

BOOKS_META = {
    "andersen-skazki": dict(
        key="andersen", title="Сказки и истории", author="Андерсен Х.К.", translator="А. В. Ганзен", year=1894,
        gid=27200, enTitle="Fairy Tales", enAuthor="Hans Christian Andersen (tr. H. P. Paull)",
        cover="Vilhelm Pedersen-Little mermaid.jpg",
        blurb="Ханс Кристиан Андерсен — датский писатель, автор всемирно известных сказок для детей и взрослых: "
              "«Гадкий утёнок», «Новое платье короля», «Дюймовочка», «Стойкий оловянный солдатик», «Снежная королева» "
              "и многих других. Здесь — в классическом переводе А. В. Ганзен.",
        blurbSrc="https://ru.wikipedia.org/wiki/Андерсен,_Ханс_Кристиан",
        note=("Neither column is the original: Andersen wrote in Danish. The Russian is Anna Ganzen's translation "
              "(1890s), the English H. P. Paull's (1872), both in the public domain and both made from the Danish, so "
              "they differ in detail; each tale runs complete in its own column. Swipe right on the text to read them "
              "side by side, or tap the EN button on the right.")),
    "grimm-skazki": dict(
        key="grimm", title="Сказки братьев Гримм", author="Гримм Я. и В.", translator="П. Н. Полевой", year=1893,
        gid=5314, enTitle="Household Tales", enAuthor="Brothers Grimm (tr. Margaret Hunt)",
        cover="Hänsel und Gretel.jpg",
        blurb="Братья Гримм (Якоб и Вильгельм) — немецкие языковеды и исследователи немецкой народной культуры. "
              "Собирали фольклор и опубликовали несколько сборников под названием «Сказки братьев Гримм», которые "
              "стали весьма популярными. Здесь — в переводе П. Н. Полевого.",
        blurbSrc="https://ru.wikipedia.org/wiki/Братья_Гримм",
        note=("Neither column is the original: the Grimms wrote in German. The Russian is П. Н. Полевой's translation "
              "(1890s), the English Margaret Hunt's (1884), both in the public domain and both made from the German, "
              "so they differ in detail; each tale runs complete in its own column. Swipe right on the text to read "
              "them side by side, or tap the EN button on the right.")),
}


def get(url):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            time.sleep(10 * (i + 1))
    raise RuntimeError("could not fetch " + url)


def text_len(h):
    return len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")))


def subpages(title):
    q = urllib.parse.urlencode({"action": "query", "list": "allpages", "aplimit": "100", "format": "json",
                                "apprefix": title + "/"})
    j = json.loads(get(API + "?" + q))
    return [p["title"] for p in j["query"]["allpages"]]


def page_html(title):
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, re.sub(r'[\\/:*?"<>| ]', "_", title) + ".html")
    if os.path.exists(fp) and os.path.getsize(fp) > 100:
        return io.open(fp, encoding="utf-8").read()
    h = api_html(title)
    io.open(fp, "w", encoding="utf-8").write(h)
    time.sleep(0.8)
    return h


def tale_html(title):
    """The tale's text; if the page is only a contents page, its numbered parts joined in order."""
    h = page_html(title)
    if text_len(h) > 2500:
        return h
    subs = subpages(title.split("/")[0] if "/" in title and "(ВТ" in title else title)
    parts = [s for s in subs if re.search(r"/(?:Глава\s+)?\d+$", s)]
    if parts:
        parts.sort(key=lambda s: int(re.search(r"(\d+)$", s).group(1)))
        return "\n".join(page_html(p) for p in parts)
    for pref in ("(ВТ:Ё)", "(ВТ)"):
        alt = [s for s in subs if s.endswith(pref)]
        if alt:
            return page_html(alt[0])
    return h


def andersen_en(path, titles):
    L = [l.rstrip() for l in io.open(path, encoding="utf-8-sig", errors="replace").read().replace("\r", "").split("\n")]
    s = next(i for i, l in enumerate(L) if "*** START" in l)
    e = next(i for i, l in enumerate(L) if "*** END" in l)
    L = L[s:e]
    ts = set(titles)
    pos = {}
    for i, l in enumerate(L):
        if l.strip() in ts:
            pos[l.strip()] = i                 # the last occurrence: the tale itself, not the contents list
    out = {}
    starts = sorted(pos.values())
    for t, i in pos.items():
        nxt = next((j for j in starts if j > i), len(L))
        out[t] = paras(L[i + 1:nxt])
    return out


def grimm_en(path):
    L = io.open(path, encoding="utf-8-sig", errors="replace").read().replace("\r", "").split("\n")
    s = next(i for i, l in enumerate(L) if "*** START" in l)
    e = next(i for i, l in enumerate(L) if "*** END" in l)
    L = L[s:e]
    heads = [(i, int(m.group(1))) for i, l in enumerate(L)
             for m in [re.match(r"^(?:Legend )?(\d{1,3}) ([^()]+)$", l.strip())] if m and not l.startswith(" ")]
    out = {}
    for k, (i, n) in enumerate(heads):
        if n in out:
            continue
        nxt = heads[k + 1][0] if k + 1 < len(heads) else len(L)
        out[n] = paras(L[i + 1:nxt])
    return out


def paras(lines):
    t = "\n".join(lines)
    ps = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", t)]
    ps = [re.sub(r"\[(?:Illustration|Footnote)[^\]]*\]?", "", p).strip() for p in ps]
    return [p for p in ps if p and not re.fullmatch(r"[*.\s\-—_=]+", p)]


def norm(s):
    return re.sub(r"[^а-яё]", "", s.lower().replace("ё", "е"))


def main():
    cfg = json.load(io.open("tools/tales_config.json", encoding="utf-8"))
    a = sys.argv[1:]
    only = a[a.index("--only") + 1:] if "--only" in a else None
    for slug, meta in BOOKS_META.items():
        if only and slug not in only:
            continue
        items = cfg[meta["key"]]
        print("== %s: %d tales" % (slug, len(items)), flush=True)
        pairs = []
        for i, it in enumerate(items, 1):
            h = tale_html(it[0])
            if text_len(h) < 300:
                print("   !! nothing on %s" % it[0]); continue
            pairs.append({"page": it[1], "html": h})
            print("\r   Russian: %d/%d" % (i, len(items)), end="", flush=True)
        print()
        pj = os.path.join(CACHE, slug + ".json")
        io.open(pj, "w", encoding="utf-8").write(json.dumps({slug: pairs}, ensure_ascii=False))
        lst = os.path.join(CACHE, slug + ".tsv")
        io.open(lst, "w", encoding="utf-8").write("\t".join(
            [slug, items[0][0], meta["author"], meta["title"], "Fairytales", ""]) + "\n")
        subprocess.call([sys.executable, "tools/add_wikisource.py", "--list", lst, "--allow-duplicate", "--html-json", pj])
        fb2 = os.path.join(BOOKS, "novel", slug + ".fb2")
        if not os.path.exists(fb2):
            print("   !! import failed"); continue
        print("   spelling modernised" if modernise_fb2(slug) else "   spelling already modern")

        en_path = os.path.join(EN_DIR, slug + ".txt")
        if not os.path.exists(en_path):
            io.open(en_path, "w", encoding="utf-8").write(
                get("https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (meta["gid"], meta["gid"])))
        if meta["key"] == "andersen":
            en = andersen_en(en_path, cfg["andersen_titles"])
            by_ru = {norm(it[1]): (en.get(it[2]) if it[2] else None) for it in items}
        else:
            en = grimm_en(en_path)
            by_ru = {norm(it[1]): en.get(it[2]) for it in items}
        chs, how = reader_chapters(fb2)
        d = os.path.join(BOOKS, slug + "-en")
        os.makedirs(d, exist_ok=True)
        got = 0
        for ci, c in enumerate(chs, 1):
            ps = by_ru.get(norm(c["heading"]))
            if ps:
                got += 1
            io.open(os.path.join(d, "%02d.json" % ci), "w", encoding="utf-8").write(
                json.dumps({"0": "\n\n".join(ps)} if ps else {}, ensure_ascii=False))
        print("   reader chapters: %d (%s); with English: %d" % (len(chs), how, got))
        unmatched = [c["heading"] for c in chs if norm(c["heading"]) not in by_ru]
        if unmatched:
            print("   !! chapters not matched to a tale: %s" % unmatched[:10])

        idx = json.load(io.open(MANIFEST, encoding="utf-8"))
        for b in idx:
            if b.get("slug") == slug:
                b.update({"category": "Fairytales", "alsoIn": ["Translations"], "author": meta["author"],
                          "title": meta["title"], "translator": meta["translator"], "year": meta["year"],
                          "parallelEn": slug + "-en", "enTitle": meta["enTitle"], "enAuthor": meta["enAuthor"],
                          "translationNote": meta["note"], "cover": C(meta["cover"]), "public": True,
                          "blurb": meta["blurb"], "blurbSrc": meta["blurbSrc"], "blurbLang": "ru"})
                print("   catalogued: %s words" % format(b.get("words", 0), ","))
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\nDone. Next: python3 tools/gen_stress_maps.py, then the case drills (see the top of this file).")


if __name__ == "__main__":
    main()
