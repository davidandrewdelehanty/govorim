#!/usr/bin/env python3
"""Seven new books on the Translations shelf, each with its English beside it:

  Сервантес  «Дон-Кихот Ламанчский» — В. А. Карелин's translation, in its two
             parts; English: John Ormsby (Gutenberg 996), cut at "Volume II"
  Дюма       «Три мушкетёра» — the 1904 Суворин edition, two volumes;
             English: Gutenberg 1257, cut where the Russian second volume begins
  Верн       «Двадцать тысяч льё под водой» (Марко Вовчок, 1870) and «Дети
             капитана Гранта» (М. А. Бекетова)
  Данте      «Ад» — Д. Е. Мин's translation (1855), canto by canto;
             English: Longfellow (Gutenberg 1001)

The rows are in tools/translations/list.tsv and Мин's cantos in
tools/translations/chapters.json; this runs the usual two steps
(tools/translations.py, tools/translations_build.py) for these slugs only, with
the English cut to the right part in between, then adds pictures and Russian
descriptions from Wikipedia.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/new_translations.py
    python3 tools/gen_stress_maps.py
    for b in cervantes-don-quixote-1 cervantes-don-quixote-2 dumas-musketeers-1 dumas-musketeers-2 \\
             verne-twenty-thousand-leagues verne-children-of-captain-grant; do
      python3 tools/make_case_drills.py --book $b.fb2; done
"""
import io, json, os, re, subprocess, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from reader_chapters import reader_chapters

SLUGS = ["cervantes-don-quixote-1", "cervantes-don-quixote-2", "dumas-musketeers-1", "dumas-musketeers-2",
         "verne-twenty-thousand-leagues", "verne-children-of-captain-grant", "dante-inferno"]
EN = "tools/translations/en"
MANIFEST = "private/books/index.json"
C = lambda f: "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(f.replace(" ", "_")) + "?width=500"
WP = lambda t: "https://ru.wikipedia.org/wiki/" + t.replace(" ", "_")

DQ = ("«Хитроумный идальго Дон Кихот Ламанчский» Мигеля де Сервантеса — одно из наиболее популярных произведений "
      "мировой литературы. Настоящее имя героя — Алонсо Кихано.")
MU = ("«Три мушкетёра» — историко-приключенческий роман Александра Дюма, впервые опубликованный в парижской газете "
      "Le Siècle в 1844 году. Книга посвящена приключениям молодого дворянина по имени д’Артаньян, отправившегося в "
      "Париж, чтобы стать мушкетёром, и трёх его друзей-мушкетёров Атоса, Портоса и Арамиса в период между 1625 и 1628 годами.")
META = {
    "cervantes-don-quixote-1": ("Don Quixote 6.jpg", DQ, WP("Дон Кихот")),
    "cervantes-don-quixote-2": ("Quixote sancho panza dore.jpg", DQ, WP("Дон Кихот")),
    "dumas-musketeers-1": ("Dartagnan-musketeers - Maurice Leloir.jpg", MU, WP("Три мушкетёра")),
    "dumas-musketeers-2": ("Les Trois Mousquetaires, Leloir - All for one, one for all oath⁠.jpg", MU, WP("Три мушкетёра")),
    "verne-twenty-thousand-leagues": ("'Twenty Thousand Leagues Under the Sea' by Neuville and Riou 061.jpg",
        "«Двадцать тысяч лье под водой» — классический научно-фантастический роман французского писателя Жюля Верна, "
        "впервые опубликованный в 1869—1870 годах. В старых русских переводах — «Восемьдесят тысяч вёрст под водой».",
        WP("Двадцать тысяч льё под водой")),
    "verne-children-of-captain-grant": ("'The Children of Captain Grant' by Édouard Riou 012.jpg",
        "«Дети капитана Гранта» — приключенческий роман французского писателя Жюля Верна. Лорд и леди Гленарван, майор "
        "Мак-Наббс, Жак Паганель, Мэри и Роберт Грант, Джон Манглс в поисках потерпевшего кораблекрушение капитана Гранта "
        "путешествуют вокруг Земли по Южной Америке, Австралии и Новой Зеландии.", WP("Дети капитана Гранта")),
    "dante-inferno": ("Gustave Doré - Dante Alighieri - Inferno - Plate 9 (Canto III - Charon).jpg",
        "Ад в «Божественной комедии» Данте — строгая система в загробном мире с точки зрения католического христианства, "
        "представленная в виде девяти кругов, окружающих вмороженного в лёд Люцифера.", WP("Ад (Божественная комедия)")),
}

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman(s):
    n = 0
    for i, ch in enumerate(s):
        v = ROMAN[ch]
        n += -v if i + 1 < len(s) and ROMAN[s[i + 1]] > v else v
    return n


def to_roman(n):
    out = ""
    for v, r in ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += r; n -= v
    return out


def cut(slug, full, start_re, keep_after):
    """Keep the part of a Gutenberg text before (or from) the LAST line matching start_re."""
    path = os.path.join(EN, slug + ".txt")
    marker = os.path.join(EN, slug + ".cut")
    if os.path.exists(marker):
        return "already cut"
    t = full.replace("\r\n", "\n")
    ms = list(re.finditer(start_re, t, flags=re.M))
    if not ms:
        return "!! no split point found — English left whole"
    at = ms[-1].start()
    part = t[at:] if keep_after else t[:at]
    io.open(path, "w", encoding="utf-8").write(part)
    io.open(marker, "w").write(start_re)
    return "cut at %d of %d characters" % (at, len(t))


def main():
    r = subprocess.call([sys.executable, "tools/translations.py", "--only"] + SLUGS)
    # The two-part books share one English text: keep each part's half.
    for slug, rx, after in (("cervantes-don-quixote-1", r"^\s*Volume II\s*$", False),
                            ("cervantes-don-quixote-2", r"^\s*Volume II\s*$", True)):
        p = os.path.join(EN, slug + ".txt")
        if os.path.exists(p):
            print("  %s: %s" % (slug, cut(slug, io.open(p, encoding="utf-8-sig", errors="replace").read(), rx, after)))
    # The Russian second volume numbers its chapters from I again, so where it
    # opens in the English is one past the first volume's last chapter.
    fb2 = "public/books/novel/dumas-musketeers-1.fb2"
    if os.path.exists(fb2):
        chs, _ = reader_chapters(fb2)
        n = None
        for c in chs:
            h = c["heading"].strip()
            m = re.match(r"^(?:Глава\s+)?([IVXLC]{1,7}|\d{1,3})(?=[.\s]|$)", h)
            if m:
                g = m.group(1)
                k = int(g) if g.isdigit() else roman(g)
                n = max(n or 0, k + 1)
        if n:
            rx = r"^\s*Chapter %s\.?\s*$" % to_roman(n)
            for slug, after in (("dumas-musketeers-1", False), ("dumas-musketeers-2", True)):
                p = os.path.join(EN, slug + ".txt")
                if os.path.exists(p):
                    print("  %s: volume 2 opens at chapter %d; %s" % (
                        slug, n, cut(slug, io.open(p, encoding="utf-8-sig", errors="replace").read(), rx, after)))
        else:
            print("  !! could not read the first chapter number of the Russian second volume")
    subprocess.call([sys.executable, "tools/translations_build.py", "--only"] + SLUGS)
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    for b in idx:
        s = b.get("slug")
        if s in META:
            f, bl, src = META[s]
            b["cover"] = C(f)
            b.update({"blurb": bl, "blurbSrc": src, "blurbLang": "ru"})
            print("ok %-34s %s words, English: %s" % (s, format(b.get("words", 0), ","), "yes" if b.get("parallelEn") else "NO"))
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\nDone. Next: python3 tools/gen_stress_maps.py, then the case drills (see the top of this file).")


if __name__ == "__main__":
    main()
