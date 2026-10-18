#!/usr/bin/env python3
"""Homer on the Translations shelf: Гнедич's «Илиада» (1829) and Жуковский's
«Одиссея» (1849), with Samuel Butler's English prose beside them, book by book.
Runs in WSL (network). Nothing is machine-written.

  Russian  Russian Wikisource, via tools/add_wikisource.py (EPUB -> FB2).
           Both translators died long ago (1833, 1852); pre-reform spelling
           is modernised by the same rules as the rest of the shelf.
  English  Samuel Butler's prose translations (Iliad 1898, Odyssey 1900),
           Project Gutenberg 2199 and 1727. Butler's book summaries and his
           Odyssey footnotes are left out, so the column is Homer only.

Neither side is the original — both are translated from Homer's Greek — so the
English is placed beside the Russian by position within each book (песнь N =
BOOK N), not paragraph by paragraph: Гнедич's hexameter lines are short
paragraphs, Butler's prose paragraphs are long, and each runs complete.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/homer.py
    python3 tools/gen_stress_maps.py
    python3 tools/make_case_drills.py --book homer-iliada.fb2
    python3 tools/make_case_drills.py --book homer-odisseya.fb2
"""
import io, json, os, re, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from reader_chapters import reader_chapters
from translations_build import modernise_fb2

UA = {"User-Agent": "govorim-app/1.0 (library import; contact via github)"}
MANIFEST = "private/books/index.json"
BOOKS = "public/books"
EN_DIR = "tools/translations/en"
CMN = "https://commons.wikimedia.org/wiki/Special:FilePath/%s?width=500"

WORKS = [
    dict(slug="homer-iliada", page="Илиада (Гомер; Гнедич)", title="Илиада", en_title="The Iliad", gid=2199,
         translator="Н. И. Гнедич", year=1829, en_year=1898,
         cover="Hector_and_Andromache_by_A.Losenko.jpg",
         blurb="«Илиада» — древнейший из сохранившихся памятников древнегреческой литературы, эпическая поэма, "
               "приписываемая Гомеру, посвящённая событиям Троянской войны. В её основу, судя по всему, "
               "легли фольклорные сказания о подвигах древних героев.",
         blurbSrc="https://ru.wikipedia.org/wiki/Илиада"),
    dict(slug="homer-odisseya", page="Одиссея (Гомер; Жуковский)", title="Одиссея", en_title="The Odyssey", gid=1727,
         translator="В. А. Жуковский", year=1849, en_year=1900,
         cover="John_William_Waterhouse_-_Ulysses_and_the_Sirens_(1891).jpg",
         blurb="«Одиссея» — вторая после «Илиады» классическая поэма, приписываемая древнегреческому поэту Гомеру. "
               "Рассказывает о приключениях мифического героя, царя Итаки по имени Одиссей, во время его "
               "возвращения на родину по окончании Троянской войны, а также о приключениях его жены Пенелопы, "
               "ожидавшей Одиссея на Итаке.",
         blurbSrc="https://ru.wikipedia.org/wiki/Одиссея"),
]

ORD = ["перв", "втор", "трет", "четверт", "пят", "шест", "седьм", "восьм", "девят", "десят",
       "одиннадцат", "двенадцат", "тринадцат", "четырнадцат", "пятнадцат", "шестнадцат",
       "семнадцат", "восемнадцат", "девятнадцат", "двадцат"]


def book_no(heading):
    """«Песнь двадцать четвёртая» -> 24; anything that is not a песнь -> None."""
    h = heading.lower().replace("ё", "е")
    m = re.search(r"песнь\s+(.+)", h)
    if not m:
        return None
    w = m.group(1).split()
    if w[0].startswith("двадцат") and len(w) > 1:
        for i, s in sorted(enumerate(ORD[:9]), key=lambda a: -len(a[1])):
            if w[1].startswith(s):
                return 21 + i
        return 20          # «Песнь двадцатая. Битва богов» — the next word is the title
    for i, s in sorted(enumerate(ORD), key=lambda a: -len(a[1])):   # пятнадцатая before пятая
        if w[0].startswith(s):
            return i + 1
    return None


def clean_fb2(slug):
    path = os.path.join(BOOKS, "novel", slug + ".fb2")
    raw = io.open(path, encoding="utf-8").read()
    n0 = len(raw)
    # Wikisource's own synopsis page and any notes section are not Homer.
    raw = re.sub(r"<section>\s*<title>\s*<p>[^<]*(?:Краткое содержание|Примечани)[^<]*</p>.*?</section>", "",
                 raw, flags=re.S)
    raw = re.sub(r"\s*\[\d{1,4}\]", "", raw)          # footnote marks
    io.open(path, "w", encoding="utf-8", newline="\n").write(raw)
    return n0 - len(raw)


def english_books(path):
    """Butler's text -> 24 lists of paragraphs (summaries and footnotes dropped)."""
    t = io.open(path, encoding="utf-8").read().replace("\r\n", "\n")
    e = t.find("*** END")
    t = t[:e] if e > 0 else t
    t = re.sub(r"\[\d+\]\s*\[.*?\]", "", t, flags=re.S)     # Odyssey footnote bodies
    t = re.sub(r"\[\d+\]", "", t)                           # their marks in the text
    heads = [m for m in re.finditer(r"(?m)^\s*BOOK\s+([IVXL]+)\.?\s*$", t)]
    heads = heads[-24:]
    out = []
    for i, m in enumerate(heads):
        body = t[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(t)]
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body)]
        paras = [p for p in paras if p]
        if paras:
            paras = paras[1:]      # Butler's summary of the book
        out.append(paras)
    return out


def fetch_english(slug, gid):
    os.makedirs(EN_DIR, exist_ok=True)
    out = os.path.join(EN_DIR, slug + ".txt")
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        return out
    for url in ("https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (gid, gid),
                "https://www.gutenberg.org/ebooks/%d.txt.utf-8" % gid):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                data = r.read().decode("utf-8", errors="replace")
            if len(data) > 100000:
                io.open(out, "w", encoding="utf-8").write(data)
                return out
        except Exception as e:
            print("   %s: %s" % (url, e))
        time.sleep(2)
    return None


def place(w, books):
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    entry = next(b for b in idx if b.get("slug") == w["slug"])
    chs, how = reader_chapters(os.path.join(BOOKS, entry["filename"]))
    d = os.path.join(BOOKS, w["slug"] + "-en")
    os.makedirs(d, exist_ok=True)
    placed = 0
    for ci, c in enumerate(chs, 1):
        n = book_no(c["heading"])
        res = {}
        if n and n <= len(books) and c["paras"]:
            en = books[n - 1]
            tot = sum(len(p) for p in en) or 1
            nru = len(c["paras"])
            run = 0
            for p in en:
                mid = (run + len(p) / 2) / tot
                k = str(min(nru - 1, int(mid * nru)))
                res[k] = (res[k] + "\n\n" + p) if k in res else p
                run += len(p)
            placed += 1
        io.open(os.path.join(d, "%02d.json" % ci), "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False))
    return len(chs), placed, [c["heading"] for c in chs]


def catalogue(w):
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    for b in idx:
        if b.get("slug") == w["slug"]:
            b.update({
                "category": "Translations", "author": "Гомер", "title": w["title"], "year": w["year"],
                "translator": w["translator"], "parallelEn": w["slug"] + "-en",
                "enTitle": w["en_title"], "enAuthor": "Homer (tr. Samuel Butler)",
                "cover": CMN % w["cover"], "public": True,
                "blurb": w["blurb"], "blurbSrc": w["blurbSrc"], "blurbLang": "ru",
                "translationNote": (
                    "Neither column is the original: Homer composed in ancient Greek. The Russian is %s's verse "
                    "translation (%d), the English Samuel Butler's prose translation (%d), both in the public "
                    "domain, and both made from the Greek. Each runs complete, book beside песнь, with the English "
                    "placed by position within each book rather than line by line. Swipe right on the text to read "
                    "them side by side, or tap the EN button on the right." % (w["translator"], w["year"], w["en_year"])),
            })
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")


def main():
    for w in WORKS:
        print("== %s — %s" % (w["slug"], w["page"]), flush=True)
        fb2 = os.path.join(BOOKS, "novel", w["slug"] + ".fb2")
        r = subprocess.run([sys.executable, "tools/add_wikisource.py", w["page"], "--slug", w["slug"],
                            "--title", w["title"], "--author", "Гомер", "--category", "Translations",
                            "--allow-duplicate"])
        if r.returncode != 0 or not os.path.exists(fb2):
            print("   Russian import failed — skipped"); continue
        print("   removed %d characters of Wikisource apparatus" % clean_fb2(w["slug"]))
        print("   spelling modernised" if modernise_fb2(w["slug"]) else "   spelling already modern")
        en = fetch_english(w["slug"], w["gid"])
        if not en:
            print("   English download failed"); continue
        books = english_books(en)
        print("   English: %d books, %d paragraphs; starts «%s…»" % (len(books), sum(map(len, books)),
                                                                     books[0][0][:60] if books and books[0] else ""))
        catalogue(w)
        n, placed, heads = place(w, books)
        print("   reader chapters: %d, with English: %d" % (n, placed))
        if placed != 24:
            print("   !! chapter headings were: %s" % heads)
    print("\nDone. Next: python3 tools/gen_stress_maps.py, then the case drills (see the top of this file).")


if __name__ == "__main__":
    main()
