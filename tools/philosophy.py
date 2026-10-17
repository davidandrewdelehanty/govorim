#!/usr/bin/env python3
"""The Philosophy shelf: Plato, Aristotle, Nietzsche, Machiavelli,
Schopenhauer, Epictetus, and the Russian philosophers — Чаадаев, Соловьёв,
Бердяев, Шестов, Розанов, Фёдоров, Кропоткин, Бакунин, Герцен, Леонтьев —
Russian beside English where both exist. Runs in
WSL (network); nothing is machine-written.

  Russian  public-domain translations on Russian Wikisource (Карпов's Plato,
           Новосадский's Aristotle, Антоновский's Nietzsche, Курочкин's
           Machiavelli, Губский's Schopenhauer, Энгельгардт's Epictetus).
  English  public-domain translations from Project Gutenberg (Jowett, Butcher,
           Common, Marriott), with the translator's introduction and any
           appendix left out so both columns hold just the work.

Each Russian dialogue goes through tools/add_wikisource.py (Wikisource EPUB →
FB2, catalogue entry), then gets a clean-up pass for what Wikisource's
Карпов pages carry that a reader should not see: a Lua error banner from
their template, the scan page numbers «[355]», the Stephanus margin letters
(«B.Сокр.»), and Карпов's endnotes. Pre-reform spelling is modernised by
the same rules as the Translations shelf. The English flows beside it in its
own column, cut into the reader's chapters by length (no line-up — each side
reads at its own pace).

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/philosophy.py                 # all four
    python3 tools/philosophy.py --only plato-fedon
    python3 tools/gen_stress_maps.py            # stress marks for the new texts
"""
import io, json, os, re, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from reader_chapters import reader_chapters
from translations_build import modernise_fb2, en_paragraphs, EN_DIR

UA = {"User-Agent": "govorim-app/1.0 (library import; contact via github)"}
MANIFEST = "private/books/index.json"
BOOKS = "public/books"

# slug, Wikisource page, author (catalogue form), Russian title, translator,
# year, English title, English author, Gutenberg id (None = Russian only),
# where the English begins and ends (see english_range).
WORKS = [
    ("plato-evtifron",  "Эвтифрон (Платон; Карпов)",         "Платон", "Евтифрон",         "В. Н. Карпов", "1863",
     "Euthyphro", "Plato", 1642, ("persons", None)),
    ("plato-apologiya", "Апология Сократа (Платон; Карпов)", "Платон", "Апология Сократа", "В. Н. Карпов", "1863",
     "Apology", "Plato", 1656, ("after-last", r"APOLOGY", None)),
    ("plato-kriton",    "Критон (Платон; Карпов)",           "Платон", "Критон",           "В. Н. Карпов", "1863",
     "Crito", "Plato", 1657, ("persons", None)),
    ("plato-fedon",     "Федон (Платон; Карпов)",            "Платон", "Федон",            "В. Н. Карпов", "1863",
     "Phaedo", "Plato", 1658, ("persons", None)),
    ("plato-pir",       "Пир (Платон; Карпов)",              "Платон", "Пир",              "В. Н. Карпов", "1863",
     "Symposium", "Plato", 1600, ("persons", None)),
    ("aristotel-poetika", "Поэтика (Аристотель)",            "Аристотель", "Поэтика",      "Н. И. Новосадский", "1927",
     "Poetics", "Aristotle", 1974, ("after-last", r"ARISTOTLE'S POETICS", None)),
    ("nitsshe-zaratustra", "Так говорил Заратустра (Ницше; Антоновский)", "Ницше Ф.", "Так говорил Заратустра",
     "Ю. М. Антоновский", "1913", "Thus Spake Zarathustra", "Friedrich Nietzsche", 1998,
     ("from-first", r"ZARATHUSTRA[’']S PROLOGUE\.?", r"APPENDIX\.?")),
    ("makiavelli-gosudar", "Государь (Макиавелли; Курочкин)/1869 (ВТ)", "Макиавелли Н.", "Государь",
     "Н. С. Курочкин", "1869", "The Prince", "Niccolò Machiavelli", 1232,
     ("from-first", r"DEDICATION", r"DESCRIPTION OF THE METHODS ADOPTED.*")),
    ("shopengauer-aforizmy", "Афоризмы житейской мудрости (Шопенгауэр)/ДО", "Шопенгауэр А.",
     "Афоризмы житейской мудрости", "Н. М. Губский", "1914", None, None, None, None),
    ("epiktet-pravila", "Правила Эпиктета (Эпиктет)/ДО", "Эпиктет", "Правила Эпиктета",
     "М. А. Энгельгардт", "1901", None, None, None, None),
    # Russian philosophers: written in Russian, so no translator. Kropotkin
    # wrote «Взаимная помощь» in English first (1902) — the English column is
    # his own original; «Хлеб и воля» was written in French, and its English
    # is the 1906 translation.
    ("chaadaev-pisma", "Философические письма (Чаадаев)", "Чаадаев П.Я.", "Философические письма",
     None, "1836", None, None, None, None),
    ("solovev-tri-razgovora", "Три разговора о войне, прогрессе и конце всемирной истории (Соловьёв)", "Соловьёв В.С.",
     "Три разговора о войне, прогрессе и конце всемирной истории", None, "1900", None, None, None, None),
    ("solovev-smysl-lyubvi", "Смысл любви (Соловьев)", "Соловьёв В.С.", "Смысл любви", None, "1892",
     None, None, None, None),
    ("berdyaev-smysl-istorii", "Смысл истории (Бердяев)", "Бердяев Н.А.", "Смысл истории", None, "1923",
     None, None, None, None),
    ("berdyaev-smysl-tvorchestva", "Смысл творчества (Бердяев)", "Бердяев Н.А.", "Смысл творчества", None, "1916",
     None, None, None, None),
    ("shestov-apofeoz", "Апофеоз беспочвенности (Шестов)", "Шестов Л.", "Апофеоз беспочвенности", None, "1905",
     None, None, None, None),
    ("rozanov-uedinennoe", "Уединенное (Розанов)", "Розанов В.В.", "Уединённое", None, "1912",
     None, None, None, None),
    ("rozanov-opavshie-listya", "Опавшие листья (Розанов)", "Розанов В.В.", "Опавшие листья", None, "1913",
     None, None, None, None),
    ("fedorov-obshchee-delo", "Философия общего дела (Федоров)", "Фёдоров Н.Ф.", "Философия общего дела", None, "1906",
     None, None, None, None),
    ("kropotkin-vzaimnaya-pomoshch", "Взаимная помощь как фактор эволюции (Кропоткин 1907)", "Кропоткин П.А.",
     "Взаимная помощь как фактор эволюции", None, "1907", "Mutual Aid: A Factor of Evolution", "Peter Kropotkin", 4341,
     ("from-first", r"INTRODUCTION", None)),
    ("kropotkin-khleb-i-volya", "Хлеб и воля (Кропоткин)", "Кропоткин П.А.", "Хлеб и воля", None, "1902",
     "The Conquest of Bread", "Peter Kropotkin", 23428, ("from-first", r"PREFACE", r"FOOTNOTES:")),
    ("bakunin-gosudarstvennost", "Государственность и анархия (Бакунин)", "Бакунин М.А.", "Государственность и анархия",
     None, "1873", None, None, None, None),
    ("gertsen-s-togo-berega", "С того берега (Герцен)", "Герцен А.И.", "С того берега", None, "1850",
     None, None, None, None),
    ("leontev-vizantizm", "Византизм и славянство (Леонтьев)", "Леонтьев К.Н.", "Византизм и славянство", None, "1875",
     None, None, None, None),
    # Lenin's books (his speeches have their own shelf). Russian only: the
    # English most people know is the Moscow Progress Publishers translation
    # of the 1960s, which is not clearly free; Gutenberg has one short letter.
    ("lenin-chto-delat", "Что делать? (Ленин)", "Ленин В.И.", "Что делать?", None, "1902", None, None, None, None),
    ("lenin-materializm", "Материализм и эмпириокритицизм (Ленин)", "Ленин В.И.", "Материализм и эмпириокритицизм",
     None, "1909", None, None, None, None),
    ("lenin-tri-istochnika", "Три источника и три составных части марксизма (Ленин)", "Ленин В.И.",
     "Три источника и три составных части марксизма", None, "1913", None, None, None, None),
    ("lenin-imperializm", "Империализм, как высшая стадия капитализма (Ленин)", "Ленин В.И.",
     "Империализм, как высшая стадия капитализма", None, "1917", None, None, None, None),
    ("lenin-aprelskie-tezisy", "О задачах пролетариата в данной революции (Ленин)", "Ленин В.И.",
     "О задачах пролетариата в данной революции (Апрельские тезисы)", None, "1917", None, None, None, None),
    ("lenin-gosudarstvo-i-revolyutsiya", "Государство и революция (Ленин)", "Ленин В.И.", "Государство и революция",
     None, "1917", None, None, None, None),
    ("lenin-renegat-kautskiy", "Пролетарская революция и ренегат Каутский (Ленин)", "Ленин В.И.",
     "Пролетарская революция и ренегат Каутский", None, "1918", None, None, None, None),
    ("lenin-detskaya-bolezn", "Детская болезнь «левизны» в коммунизме (Ленин)", "Ленин В.И.",
     "Детская болезнь «левизны» в коммунизме", None, "1920", None, None, None, None),
]

EN_BY = {1642: "Benjamin Jowett (1871, revised 1892)", 1656: "Benjamin Jowett (1871, revised 1892)",
         1657: "Benjamin Jowett (1871, revised 1892)", 1658: "Benjamin Jowett (1871, revised 1892)",
         1600: "Benjamin Jowett (1871, revised 1892)", 1974: "S. H. Butcher (1895)",
         1998: "Thomas Common (1909)", 1232: "W. K. Marriott (1908)"}
ORIGINALS = {4341: ("The English is Kropotkin's own: he wrote «Mutual Aid» in English (1902), and the Russian "
                    "is his Russian edition of 1907. Each runs complete in its own column. Swipe right on the "
                    "text to read them side by side, or tap the EN button on the right."),
             23428: ("Kropotkin wrote «La Conquête du pain» in French (1892); the Russian is the edition of 1902 "
                     "and the English the translation of 1906, both in the public domain. Each runs complete in "
                     "its own column. Swipe right on the text to read them side by side, or tap the EN button on "
                     "the right.")}


def note_for(translator, year, gid):
    if gid in ORIGINALS:
        return ORIGINALS[gid]
    return ("The English is the translation by %s and the Russian is %s's (%s), both in the public "
            "domain and both made from the original — so neither is a crib of the other, and each runs "
            "complete in its own column. Swipe right on the text to read them side by side, or tap the "
            "EN button on the right." % (EN_BY.get(gid, "a public-domain translator"), translator, year))


def dedupe_sections(raw):
    """Wikisource's EPUB lists a page once per heading inside it, so a page
    with six numbered sections arrived six times over («Государство и
    революция» came in at four times its length). Keep the first copy of
    each section body, and title it by the heading the page itself opens
    with («Глава I. Классовое общество и государство») rather than the
    last sub-heading the table of contents happened to name."""
    seen, out, dropped = set(), [], 0
    pos = 0
    for m in re.finditer(r"<section>(.*?)</section>", raw, flags=re.S):
        out.append(raw[pos:m.start()])
        pos = m.end()
        inner = m.group(1)
        body = re.sub(r"<title>.*?</title>", "", inner, count=1, flags=re.S)
        key = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
        if key and key in seen:
            dropped += 1
            continue
        seen.add(key)
        out.append("<section>" + inner + "</section>")
    out.append(raw[pos:])
    return tidy_titles("".join(out)), dropped


def tidy_titles(raw):
    """A section whose page opens with its own bold heading: drop that line
    from the text (the title already says it), and where the title ran on
    into the first sub-heading («Глава I Классовое общество и государство.
    1. Государство — продукт…»), cut it back to the chapter's own name."""
    def fix(m):
        title, body = m.group(1), m.group(2)
        tt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title)).strip()
        f = re.match(r"\s*<p><strong>([^<]{2,160})</strong></p>", body)
        if not f:
            return m.group(0)
        head = re.sub(r"\s+", " ", f.group(1)).strip()
        if not tt.startswith(head):
            return m.group(0)
        if re.search(r"\. \d+\. ", tt[len(head):len(head) + 6] + " "):
            tt = head
        return "<section>\n<title><p>%s</p></title>%s" % (tt, body[f.end():])
    return re.sub(r"<section>\s*<title>(.*?)</title>(.*?)(?=</section>)", fix, raw, flags=re.S)


def clean_fb2(slug):
    """What Wikisource's Карпов pages carry that is not Plato."""
    path = os.path.join(BOOKS, "novel", slug + ".fb2")
    raw = io.open(path, encoding="utf-8").read()
    n0 = len(raw)
    # The template's Lua error banner, wherever it landed.
    raw = re.sub(r"<p>[^<]*Ошибка Lua[^<]*</p>", "", raw)
    raw = re.sub(r"Ошибка Lua в [^.<]*?\(a nil value\)\.?\s*", "", raw)
    # Scan page numbers «[355]» and footnote marks «[3]» left in the text.
    raw = re.sub(r"\s*\[\d{1,4}\]", "", raw)
    # Stephanus margin letters: a Latin capital A–E and a full stop, glued to
    # the Russian that follows («B.Сокр.», «C. Эвт.»).
    raw = re.sub(r"(?<![A-Za-zА-Яа-яЁё])[A-E]\.\s*(?=[А-ЯЁ«—])", "", raw)
    # Карпов's endnotes: a section headed «Примечания» to the end of the body.
    raw = re.sub(r"<section>\s*<title>\s*<p>\s*Примечания\s*</p>\s*</title>.*?</section>", "", raw, flags=re.S)
    raw, dup = dedupe_sections(raw)
    # A one-page work has the Wikisource page name as its only chapter title.
    w = next((x for x in WORKS if x[0] == slug), None)
    if w:
        raw = raw.replace("<title><p>%s</p></title>" % w[1], "<title><p>%s</p></title>" % w[3])
    if dup:
        print("   dropped %d repeated section(s)" % dup)
    io.open(path, "w", encoding="utf-8", newline="\n").write(raw)
    return n0 - len(raw)


def fetch_english(slug, gid):
    os.makedirs(EN_DIR, exist_ok=True)
    out = os.path.join(EN_DIR, slug + ".txt")
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        return out
    for url in ("https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (gid, gid),
                "https://www.gutenberg.org/files/%d/%d-0.txt" % (gid, gid),
                "https://www.gutenberg.org/files/%d/%d.txt" % (gid, gid)):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                data = r.read().decode("utf-8", errors="replace")
            if len(data) > 2000:
                io.open(out, "w", encoding="utf-8").write(data)
                return out
        except Exception as e:
            print("   %s: %s" % (url, e))
        time.sleep(2)
    return None


def english_range(paras, rule):
    """Only the work itself: the translator's introduction, contents pages,
    appendices and the extra pieces Gutenberg bundles are left out.
      ("persons", None)          Plato: from the first speaker after
                                 «PERSONS OF THE DIALOGUE»
      ("after-last", head, end)  from just after the LAST paragraph equal to head
      ("from-first", head, end)  from the FIRST paragraph equal to head that is
                                 followed by text (not a contents line)
    and up to (not including) the last paragraph matching end, if given."""
    kind, head = rule[0], rule[1]
    endre = rule[2] if len(rule) > 2 else None
    up = lambda p: p.strip().upper()
    start = None
    if kind == "persons":
        for i, p in enumerate(paras):
            if re.match(r"(?i)^persons of the dialogue", p):
                for j in range(i + 1, len(paras)):
                    if re.match(r"^[A-Z][A-Z ]{2,}:", paras[j]) and not re.match(r"^(SCENE|PERSONS|PLACE)", paras[j]):
                        start = j
                        break
                break
    elif kind == "after-last":
        hits = [i for i, p in enumerate(paras) if re.fullmatch(head, up(p))]
        if hits:
            start = hits[-1] + 1
    elif kind == "from-first":
        hits = [i for i, p in enumerate(paras) if re.fullmatch(head, up(p))]
        # the contents page lists the same headings; the real one is the last
        # occurrence before the text it heads (a long paragraph soon after)
        for i in hits:
            if any(len(q) > 150 for q in paras[i + 1:i + 3]):
                start = i
                break
    if start is None:
        print("   !! English start not found — using the whole Gutenberg text; check it")
        start = 0
    stop = len(paras)
    if endre:
        ends = [i for i, p in enumerate(paras) if i > start and re.fullmatch(endre, up(p))]
        if ends:
            stop = ends[-1]
    return paras[start:stop]


def flow_english(slug, paras):
    """One English block per reader chapter, split in proportion to the
    Russian chapters' lengths."""
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    book = next(b for b in idx if b.get("slug") == slug)
    chs, _ = reader_chapters(os.path.join(BOOKS, book["filename"]))
    sizes = [sum(len(p) for p in c["paras"]) for c in chs] or [1]
    total_ru, total_en = sum(sizes) or 1, sum(len(p) for p in paras) or 1
    groups, i, acc = [[] for _ in chs], 0, 0
    bound, ch = 0, 0
    limits = []
    run = 0
    for s in sizes:
        run += s
        limits.append(run / total_ru * total_en)
    for p in paras:
        while ch < len(chs) - 1 and acc >= limits[ch]:
            ch += 1
        groups[ch].append(p)
        acc += len(p)
    d = os.path.join(BOOKS, slug + "-en")
    os.makedirs(d, exist_ok=True)
    for n, g in enumerate(groups, 1):
        io.open(os.path.join(d, "%02d.json" % n), "w", encoding="utf-8").write(
            json.dumps({"0": "\n\n".join(g)} if g else {}, ensure_ascii=False))
    return len(chs), sum(len(g) for g in groups)


def catalogue(w):
    slug, page, author, ru_title, translator, year, en_title, en_author, gid, rule = w
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    for b in idx:
        if b.get("slug") != slug:
            continue
        b.update({"category": "Philosophy", "author": author, "title": ru_title, "public": True})
        if translator:
            b["translator"] = translator
        if year and not b.get("year"):
            b["year"] = int(year) if year.isdigit() else year
        if gid:
            b.update({"parallelEn": slug + "-en", "enTitle": en_title, "enAuthor": en_author,
                      "translationNote": note_for(translator, year, gid)})
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1:] if "--only" in a else None
    if "--dedupe" in a:
        # Repair the shelf in place, no network: repeated sections out, word
        # counts in the catalogue brought back down to the real length.
        idx = json.load(io.open(MANIFEST, encoding="utf-8"))
        by = {b.get("slug"): b for b in idx}
        for w in WORKS:
            path = os.path.join(BOOKS, "novel", w[0] + ".fb2")
            if not os.path.exists(path):
                continue
            raw = io.open(path, encoding="utf-8").read()
            new, dup = dedupe_sections(raw)
            if new != raw:
                io.open(path, "w", encoding="utf-8", newline="\n").write(new)
                chs, _ = reader_chapters(path)
                words = sum(len(p.split()) for c in chs for p in c["paras"])
                if w[0] in by:
                    by[w[0]]["words"] = words
                print("%-34s %3d repeated section(s) dropped → %d chapters, %s words" % (w[0], dup, len(chs), format(words, ",")))
                if w[8]:
                    paras = english_range(en_paragraphs(w[0]), w[9])
                    flow_english(w[0], paras)
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
        return
    for w in WORKS:
        slug, page, author, ru_title, translator, year, en_title, en_author, gid, rule = w
        if only and slug not in only:
            continue
        print("== %s — %s" % (slug, page), flush=True)
        r = subprocess.run([sys.executable, "tools/add_wikisource.py", page, "--slug", slug,
                            "--title", ru_title, "--author", author, "--category", "Philosophy",
                            "--allow-duplicate"])
        fb2 = os.path.join(BOOKS, "novel", slug + ".fb2")
        if r.returncode != 0 or not os.path.exists(fb2):
            print("   Russian import failed — skipped"); continue
        print("   cleaned %d characters of Wikisource apparatus" % clean_fb2(slug))
        print("   spelling modernised" if modernise_fb2(slug) else "   spelling already modern")
        catalogue(w)
        if not gid:
            print("   Russian only (no matching public-domain English on Gutenberg)")
            continue
        if not fetch_english(slug, gid):
            print("   English download failed — the Russian is on the shelf without it"); continue
        paras = english_range(en_paragraphs(slug), rule)
        n_ch, n_en = flow_english(slug, paras)
        print("   English: %d paragraphs over %d chapter(s)" % (n_en, n_ch))
        print("     starts: %s" % (paras[0][:90] if paras else "—"))
        print("     ends:   %s" % (paras[-1][:90] if paras else "—"))
    print("\nDone. Next: python3 tools/gen_stress_maps.py")


if __name__ == "__main__":
    main()
