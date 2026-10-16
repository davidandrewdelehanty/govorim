#!/usr/bin/env python3
"""Second half of the Translations shelf: no network needed.

tools/translations.py fetched the Russian (FB2s built from Wikisource) and
the English originals (Gutenberg plain text). This finishes each book:

  1. Spelling. Most of these translations were printed before 1918 and
     Wikisource keeps the old orthography (ѣ, і, ѳ, ѵ, the final ъ, -аго,
     -ыя, разсказ). That is a hurdle a learner should not have to clear to
     read Dickens, so the FB2 is rewritten in modern spelling. The original
     is kept in tools/translations/fb2-orig/.
  2. English. The Gutenberg text is cut into paragraphs and aligned with the
     Russian ones across the WHOLE book as one stream (Gale–Church on
     paragraph length), then scattered back into the reader's chapters.
     Translators of that era abridged freely, so a skipped English paragraph
     is a cheap move rather than a mismatch, and it is kept: it flows into
     the English column beside the nearest Russian paragraph. Chapter
     headings on the English side are dropped, and act as anchors at the
     Russian chapter breaks.
  3. Catalogue. parallelEn, enTitle, translator, translationNote.

    python3 tools/translations_build.py                 # every book that has both halves
    python3 tools/translations_build.py --only twain-tom-sawyer
    python3 tools/translations_build.py --report        # coverage only, writes nothing

Writes public/books/<slug>-en/NN.json, one per reader chapter (as cut by
tools/reader_chapters.py), keyed by the paragraph's index in that chapter.
"""
import csv, io, json, math, os, re, shutil, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reader_chapters import reader_chapters

DIR = "tools/translations"
LIST = os.path.join(DIR, "list.tsv")
EN_DIR = os.path.join(DIR, "en")
ORIG = os.path.join(DIR, "fb2-orig")
BOOKS = "public/books"
MANIFEST = "private/books/index.json"
REPORT = os.path.join(DIR, "report.tsv")
COLS = ["slug", "page", "author", "title", "en_title", "en_author", "gid", "translator", "year", "blurb"]
EN_NAME = {"Dickens": "Charles Dickens", "Twain": "Mark Twain", "Scott": "Walter Scott", "Defoe": "Daniel Defoe",
           "Cooper": "James Fenimore Cooper", "London": "Jack London", "Jerome": "Jerome K. Jerome",
           "Conrad": "Joseph Conrad", "Galsworthy": "John Galsworthy", "Alcott": "Louisa May Alcott",
           "Carroll": "Lewis Carroll", "Kipling": "Rudyard Kipling", "Stevenson": "Robert Louis Stevenson",
           "Dreiser": "Theodore Dreiser", "Hardy": "Thomas Hardy", "Reid": "Mayne Reid",
           "Thackeray": "William Makepeace Thackeray", "Marryat": "Frederick Marryat",
           "Burnett": "Frances Hodgson Burnett", "Bellamy": "Edward Bellamy",
           "Bulwer-Lytton": "Edward Bulwer-Lytton", "Stowe": "Harriet Beecher Stowe",
           "Haggard": "H. Rider Haggard", "Stoker": "Bram Stoker", "Wells": "H. G. Wells",
           "Doyle": "Arthur Conan Doyle", "Wilde": "Oscar Wilde", "Trollope": "Anthony Trollope"}


# ------------------------------------------------------------ 1. spelling --
LOW = "а-яё"
PRE_REFORM = re.compile(r"[ѣѢіІѳѲѵѴ]|[бвгджзклмнпрстфхцчшщ]ъ(?![а-яё])")
PREFIX_S = re.compile(r"(?<![а-яё])((?:не|по|ни|до|пре|при)?)(из(?=[кпстфхцчшщ])|воз(?=[кпстфхцшщ])|вз(?=[кпстфхцчшщ])|раз(?=[кпстфхцчшщ])|роз(?=[кпстфхцчшщ])|без(?=[кпстфхцчшщ])|чрез(?=[кпстфхцчшщ])|через(?=[кпстфхцчшщ]))", re.I)
NAMES = {"Чикаго", "Сантьяго", "Тобаго", "Яго", "Сантъяго"}


def modern(t):
    """Old orthography → modern. Word-level rules only where they are safe:
    -аго/-яго (genitive adjective), -ыя (plural adjective), ея/оне/одне,
    and з→с in the prefixes before a voiceless consonant."""
    t = (t.replace("ѣ", "е").replace("Ѣ", "Е").replace("і", "и").replace("І", "И")
          .replace("ѳ", "ф").replace("Ѳ", "Ф").replace("ѵ", "и").replace("Ѵ", "И"))
    t = re.sub(r"(?<=[бвгджзклмнпрстфхцчшщБВГДЖЗКЛМНПРСТФХЦЧШЩ])[ъЪ](?![а-яёА-ЯЁ])", "", t)
    W = r"(?<![А-ЯЁа-яё])([А-ЯЁа-яё][а-яё]{%d,}%s)%s(?![а-яё])"
    keep = lambda f: (lambda m: m.group(0) if m.group(0) in NAMES else f(m))
    t = re.sub(W % (1, "[жшчщ]", "аго"), keep(lambda m: m.group(1) + "его"), t)
    t = re.sub(W % (1, "", "аго"), keep(lambda m: m.group(1) + "ого"), t)
    t = re.sub(W % (1, "", "яго"), keep(lambda m: m.group(1) + "его"), t)
    t = re.sub(W % (2, "", "ыя"), lambda m: m.group(1) + "ые", t)
    t = re.sub(W % (1, "(?:ск|цк|[кжшчщ])", "ия"), lambda m: m.group(1) + "ие", t)
    t = re.sub(r"(?<![А-ЯЁа-яё])ея(?![а-яё])", "её", t)
    t = re.sub(r"(?<![А-ЯЁа-яё])Ея(?![а-яё])", "Её", t)
    t = re.sub(r"(?<![А-ЯЁа-яё])оне(?![а-яё])", "они", t)
    t = re.sub(r"(?<![А-ЯЁа-яё])одне(?![а-яё])", "одни", t)
    t = PREFIX_S.sub(lambda m: m.group(1) + m.group(2)[:-1] + ("с" if m.group(2)[-1] == "з" else "С"), t)
    return t


def modernise_fb2(slug):
    path = os.path.join(BOOKS, "novel", slug + ".fb2")
    raw = io.open(path, encoding="utf-8").read()
    if not PRE_REFORM.search(raw):
        return False
    os.makedirs(ORIG, exist_ok=True)
    keep = os.path.join(ORIG, slug + ".fb2")
    if not os.path.exists(keep):
        shutil.copy(path, keep)
    # text only, never inside a tag (tags and attributes are ASCII anyway)
    out = re.sub(r">([^<]+)<", lambda m: ">" + modern(m.group(1)) + "<", raw)
    io.open(path, "w", encoding="utf-8", newline="\n").write(out)
    return True


# ------------------------------------------------------------ 2. english --
HEAD_RE = re.compile(r"^(?:(?:chapter|stave|book|part|volume|canto|letter)\s+[\w.\-]+|[ivxlc]+\.?|\d+\.?)"
                     r"(?:[.:—–-]\s*.{0,80})?$", re.I)


def en_paragraphs(slug):
    raw = io.open(os.path.join(EN_DIR, slug + ".txt"), encoding="utf-8-sig", errors="replace").read()
    raw = raw.replace("\r\n", "\n")
    m = re.search(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG[^\n]*\n", raw, re.I)
    if m:
        raw = raw[m.end():]
    m = re.search(r"\n\s*\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG", raw, re.I)
    if m:
        raw = raw[:m.start()]
    m = re.search(r"\n\s*End of (?:the )?Project Gutenberg", raw, re.I)
    if m:
        raw = raw[:m.start()]
    out = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        t = " ".join(lines)
        t = re.sub(r"\[(?:Illustration|Footnote|Sidenote)[^\]]*\]?", " ", t, flags=re.I)
        t = re.sub(r"\[\d+\]", "", t)
        t = re.sub(r"(?<![\w*])_([^_]+)_(?!\w)", r"\1", t)
        t = re.sub(r"\s+", " ", t).strip()
        if not t or re.fullmatch(r"[*.\s\-—_=]+", t):
            continue
        # A table of contents arrives as one paragraph ("CHAPTER I. … CHAPTER II. …")
        # or as a bare "Contents" line; neither is text the Russian translates.
        if re.fullmatch(r"(?i)(table of )?contents\.?", t) or len(re.findall(r"\b(?:CHAPTER|Chapter|STAVE|BOOK)\s+[IVXLC\d]+\b", t)) >= 3:
            continue
        out.append(t)
    return out


def is_heading(t):
    s = t.strip()
    if len(s) > 90:
        return False
    if HEAD_RE.match(s):
        return True
    letters = re.sub(r"[^A-Za-z]", "", s)
    return len(s) <= 60 and len(letters) >= 3 and letters.isupper() and not s.endswith(("!", "?", "”", '"'))



# Anchors: proper names and numbers both texts carry. Names are reduced to a
# consonant skeleton both alphabets can reach — Гек/Huck, Пиквик/Pickwick,
# Базаров/Bazarov — and weighted by rarity, so a minor character named once
# pins the alignment hard and the hero named everywhere barely counts.
RU_LAT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                  ["a","b","v","g","d","e","e","zh","z","i","i","k","l","m","n","o","p","r","s","t","u","f","h","ts","ch","sh","sh","","y","","e","yu","ya"]))


def skel(lat):
    s = lat.lower()
    for a, b in (("tch", "ch"), ("sch", "sh"), ("ck", "k"), ("ph", "f"), ("th", "t"), ("kh", "h"), ("zh", "S"), ("sh", "S"),
                 ("ch", "C"), ("ce", "se"), ("ci", "si"), ("cy", "sy"), ("ts", "s"), ("tz", "s"), ("j", "dS"), ("x", "ks"), ("qu", "kv"), ("q", "k"), ("w", "v"),
                 ("c", "k"), ("h", "g"), ("z", "s"), ("f", "v")):
        s = s.replace(a, b)
    s = re.sub(r"[aeiouy'\W\d_]", "", s)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s


def name_keys(paras, ru):
    """Per paragraph, the set of anchor keys. A capitalised word counts as a
    name only if the text never uses it in lower case."""
    word = re.compile(r"[А-ЯЁа-яё]+" if ru else r"[A-Za-z]+")
    lower = set()
    for p in paras:
        for w in word.findall(p):
            if w[0].islower():
                lower.add(w)
    out = []
    for p in paras:
        ks = set()
        for w in word.findall(p):
            if len(w) < 3 or not w[0].isupper() or w.lower() in lower or w.isupper() and len(w) > 4:
                continue
            lat = "".join(RU_LAT.get(c, c) for c in w.lower()) if ru else w
            sk = skel(lat)
            if len(sk) >= 2:
                ks.add(sk[:3])
        for d in re.findall(r"\b\d{2,4}\b", p):
            ks.add("#" + d)
        out.append(ks)
    return out


# Gale–Church in log space with a Gaussian length model. RU runs ~1.1× the
# English in characters; the ratio is re-estimated from the first pass.
MOVES = [(1, 1, 0.0), (2, 1, 2.3), (1, 2, 2.3), (2, 2, 4.0), (3, 1, 4.5), (1, 3, 4.5), (4, 1, 5.5), (5, 1, 6.5), (6, 1, 7.5)]
S2 = 6.8
ANCHOR = 1.0
SKIP_EN = (2.0, 0.001)


def align(ru, en, chap_start, ratio=1.1):
    n, m = len(ru), len(en)
    lr = np.array([len(x) for x in ru], dtype=np.float64)
    le = np.array([len(x) for x in en], dtype=np.float64)
    cr = np.concatenate([[0], np.cumsum(lr)])
    ce = np.concatenate([[0], np.cumsum(le)])
    head = np.array([is_heading(x) for x in en])
    # cost of skipping English paragraph j (translator left it out)
    skip_en = SKIP_EN[0] + SKIP_EN[1] * le
    skip_en_head_at_break = np.where(head, 0.0, skip_en)
    skip_en_head_else = np.where(head, 1.0, skip_en)
    S_brk = np.concatenate([[0], np.cumsum(skip_en_head_at_break)])
    S_else = np.concatenate([[0], np.cumsum(skip_en_head_else)])
    INF = 1e18
    D = [None] * (n + 1)
    back = np.zeros((n + 1, m + 1), dtype=np.int8)   # 0 start, 1..9 MOVES, 30 skip-ru, 31 skip-en
    D[0] = np.zeros(m + 1)                           # free English prefix (title page, contents)
    D[0] = D[0] + 0.0
    starts = set(chap_start)
    # The title, the translator's name and other short lines before the first
    # real paragraph have no English; skipping them is nearly free.
    lead = 0
    while lead < n and lr[lead] < 200:
        lead += 1
    if lead > 15:
        lead = 0
    rk, ek = name_keys(ru, True), name_keys(en, False)
    df = {}
    for ks in ek:
        for k in ks:
            df[k] = df.get(k, 0) + 1
    inv = {}
    for j, ks in enumerate(ek):
        for k in ks:
            if df[k] <= max(3, m // 8):
                inv.setdefault(k, []).append(j)
    idf = {k: math.log(m / df[k]) for k in inv}
    for i in range(1, n + 1):
        row = np.full(m + 1, INF)
        code = np.zeros(m + 1, dtype=np.int8)
        # skip a Russian paragraph (translator's own note, an added heading)
        c = D[i - 1] + (0.2 if i <= lead else 4.0 + 0.0015 * lr[i - 1])
        better = c < row; row[better] = c[better]; code[better] = 30
        for k, (a, b, pen) in enumerate(MOVES, 1):
            if i - a < 0:
                continue
            prev = D[i - a]
            lru = cr[i] - cr[i - a]
            cand = np.full(m + 1, INF)
            lenn = ce[b:] - ce[:-b] if b else None
            mean = (lenn + lru / ratio) / 2.0
            delta = (lru - ratio * lenn) / np.sqrt(S2 * np.maximum(mean, 1.0))
            cand[b:] = prev[:-b] + pen + 0.5 * np.minimum(delta * delta, 400.0)
            keys = set().union(*rk[i - a:i])
            if keys:
                bonus = np.zeros(m + 1)
                for kk in keys:
                    for e in inv.get(kk, ()):
                        bonus[e + 1:e + 1 + b] += idf[kk]
                cand -= ANCHOR * np.minimum(bonus, 12.0)
            better = cand < row; row[better] = cand[better]; code[better] = k
        # skip English paragraphs: row[j] = min_k (row[k] + S[j] - S[k])
        S = S_brk if i in starts else S_else
        base = row - S
        run = np.minimum.accumulate(base) + S
        better = run < row - 1e-9
        row = np.where(better, run, row); code[better] = 31
        D[i] = row
        back[i] = code
        if i >= 7:
            D[i - 7] = None
    # free English suffix (notes, appendices, the Gutenberg licence)
    j = int(np.argmin(D[n]))
    pairs, i = [], n
    while i > 0:
        k = back[i, j]
        if k == 31:
            pairs.append(("en", None, j - 1)); j -= 1
        elif k == 30:
            pairs.append(("ru", i - 1, None)); i -= 1
        else:
            a, b, _ = MOVES[k - 1]
            pairs.append(("pair", list(range(i - a, i)), list(range(j - b, j)))); i -= a; j -= b
    pairs.reverse()
    return pairs, j


# Front matter the TRANSLATOR wrote has no English. An author's own preface
# does, so only these are taken out by name; the rest are listed per book in
# tools/translations/ru_skip.json.
TRANSLATOR_FM = re.compile(r"к русскому переводу|от переводчика|от издател|от редакци|исторический очерк|вместо предисловия|биографи", re.I)


def ru_skipped(slug, heading):
    try:
        extra = json.load(io.open(os.path.join(DIR, "ru_skip.json"), encoding="utf-8")).get(slug, [])
    except FileNotFoundError:
        extra = []
    h = (heading or "").strip()
    return bool(TRANSLATOR_FM.search(h)) or any(h.startswith(x) for x in extra)


def build_en(slug, ru_chs, en, report_only=False):
    flat, chap_start, owner = [], [], []
    for ci, c in enumerate(ru_chs):
        if ru_skipped(slug, c["heading"]):
            continue
        chap_start.append(len(flat))
        for pi, p in enumerate(c["paras"]):
            flat.append(p); owner.append((ci, pi))
    if not flat or not en:
        return None
    pairs, _ = align(flat, en, chap_start)
    # re-estimate the length ratio from the confident 1-1 pairs, align again
    rs = [(len(flat[r[0]]), len(en[e[0]])) for kind, r, e in pairs if kind == "pair" and len(r) == 1 and len(e) == 1]
    if len(rs) > 50:
        ratio = float(np.median([a / max(b, 1) for a, b in rs]))
        ratio = min(max(ratio, 0.8), 1.5)
        pairs, _ = align(flat, en, chap_start, ratio)
    else:
        ratio = 1.1
    out = [dict() for _ in ru_chs]
    got = [None] * len(flat)
    pend = []                                  # skipped English waiting for a home
    matched_ru = matched_en = skipped_en = 0
    last = None
    for kind, r, e in pairs:
        if kind == "en":
            t = en[e]
            if not is_heading(t):
                skipped_en += 1
                if last is None:
                    pend.append(t)
                else:
                    got[last] = (got[last] + "\n\n" + t) if got[last] else t
            continue
        if kind == "ru":
            continue
        txt = "\n\n".join(en[x] for x in e if not is_heading(en[x]))
        if pend:
            txt = "\n\n".join(pend + ([txt] if txt else [])); pend = []
        if not txt:
            continue
        got[r[0]] = (got[r[0]] + "\n\n" + txt) if got[r[0]] else txt
        last = r[0]
        matched_ru += len(r); matched_en += len(e)
    for g, t in enumerate(got):
        if t:
            ci, pi = owner[g]
            out[ci][str(pi)] = t
    stats = {"ru": len(flat), "en": len(en), "ru_matched": matched_ru, "en_matched": matched_en,
             "en_skipped": skipped_en, "ratio": round(ratio, 3),
             "chapters_without_en": sum(1 for o in out if not o)}
    return out, stats


# ------------------------------------------------------------ 3. catalogue --
def note_for(r):
    au = EN_NAME.get(r["en_author"], r["en_author"])
    yr = (" (%s)" % r["year"]) if r["year"] else ""
    who = "an anonymous translator" if r["translator"] in ("", "аноним") else r["translator"]
    return ("Here the English is the original: %s's %s, from Project Gutenberg. The Russian is the "
            "translation by %s%s, now in the public domain, with its pre-reform spelling modernised. "
            "Translators of that era often abridged or retold freely, so the Russian may leave out what "
            "the English keeps; the English column always runs complete. Swipe right on the text to read "
            "it beside the Russian, or tap the EN button on the right."
            % (au, r["en_title"], who, yr))


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1:] if "--only" in a else None
    report_only = "--report" in a
    with io.open(LIST, encoding="utf-8") as f:
        rows = [dict(zip(COLS, (x + [""] * 10)[:10])) for x in csv.reader(f, delimiter="\t") if x and not x[0].startswith("#")]
    if only:
        rows = [r for r in rows if r["slug"] in only]
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): b for b in idx}
    lines = []
    for r in rows:
        s = r["slug"]
        fb2 = os.path.join(BOOKS, "novel", s + ".fb2")
        txt = os.path.join(EN_DIR, s + ".txt")
        if not os.path.exists(fb2) or not os.path.exists(txt):
            print("-- %-28s %s" % (s, "no FB2" if not os.path.exists(fb2) else "no English")); continue
        t0 = time.time()
        if "--catalogue-only" in a:
            b = by.get(s)
            if b is not None and os.path.isdir(os.path.join(BOOKS, s + "-en")):
                b.update({"category": "Translations", "parallelEn": s + "-en", "enTitle": r["en_title"],
                          "translator": r["translator"] if r["translator"] != "аноним" else "anonymous",
                          "enAuthor": EN_NAME.get(r["en_author"], r["en_author"]),
                          "translationNote": note_for(r), "public": True})
                if r["blurb"] and not b.get("blurb"):
                    b["blurb"] = r["blurb"]
            continue
        mod = False if report_only else modernise_fb2(s)
        chs, how = reader_chapters(fb2)
        en = en_paragraphs(s)
        res = build_en(s, chs, en)
        if not res:
            print("!! %-28s nothing to align" % s); continue
        out, st = res
        cov = st["ru_matched"] / max(st["ru"], 1)
        line = "%-28s %3d ch  ru %5d  en %5d  RU with EN %5.1f%%  EN skipped %5d  ratio %.2f  %s%4.0fs" % (
            s, len(chs), st["ru"], st["en"], 100 * cov, st["en_skipped"], st["ratio"],
            "modernised  " if mod else "", time.time() - t0)
        print(line, flush=True)
        lines.append([s, len(chs), st["ru"], st["en"], round(100 * cov, 1), st["en_skipped"], st["ratio"], st["chapters_without_en"]])
        if report_only:
            continue
        d = os.path.join(BOOKS, s + "-en")
        os.makedirs(d, exist_ok=True)
        for i, o in enumerate(out, 1):
            io.open(os.path.join(d, ("%02d" % i) + ".json"), "w", encoding="utf-8").write(
                json.dumps(o, ensure_ascii=False, indent=0))
        # files left from an earlier build with more chapters: emptied, not deleted
        for f in os.listdir(d):
            m = re.fullmatch(r"(\d+)\.json", f)
            if m and int(m.group(1)) > len(out):
                io.open(os.path.join(d, f), "w", encoding="utf-8").write("{}")
        b = by.get(s)
        if b is not None:
            b.update({"category": "Translations", "parallelEn": s + "-en", "enTitle": r["en_title"],
                      "translator": r["translator"] if r["translator"] != "аноним" else "anonymous",
                      "enAuthor": EN_NAME.get(r["en_author"], r["en_author"]),
                      "translationNote": note_for(r), "public": True})
            if r["blurb"] and not b.get("blurb"):
                b["blurb"] = r["blurb"]
        else:
            print("   (no catalogue entry for %s — run tools/translations.py first)" % s)
    if not report_only:
        bak = MANIFEST + ".bak-translations"
        if not os.path.exists(bak):
            shutil.copy(MANIFEST, bak)
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    with io.open(REPORT, "w", encoding="utf-8") as f:
        f.write("slug\tchapters\tru_paras\ten_paras\tru_with_en_%\ten_skipped\tratio\tchapters_without_en\n")
        for l in lines:
            f.write("\t".join(map(str, l)) + "\n")
    print("\n%d book(s); report → %s" % (len(lines), REPORT))


if __name__ == "__main__":
    main()
