#!/usr/bin/env python3
"""The Read in English library: the most-read public-domain English books on
Project Gutenberg, as English books on the site (lang "en").

What it does, in one run you can leave all day (resumable — stop it any time
and run it again; anything finished is skipped):

  1. Reads Gutenberg's "most downloaded" lists and walks down them until it
     has --count books that are
       * written in English (no translator in the record; no Russian authors —
         those are the Russian library's), text, not reference or periodicals
       * not already on the site (every English column's book is skipped, so
         Treasure Island is not listed twice)
       * one copy per work (later editions of the same title are skipped)
  2. For each: downloads the plain text, cuts Gutenberg's header and licence,
     finds the chapters (CHAPTER/BOOK/PART/ACT/SCENE/STAVE/roman numerals;
     a BOOK or PART heading becomes a tier in the Contents), or cuts it into
     parts of about 3,000 words when it has none, and writes
       public/books/english/<slug>.fb2         (<lang>en</lang>)
  3. Picture: Gutenberg's cover, resized, into public/books/img/pg<N>.jpg
     Description: the opening of the English Wikipedia article, when one is
     clearly about this book.
  4. Adds it to private/books/index.json with lang "en", category from
     Gutenberg's subjects (Novels, Novellas, Short Stories, Poetry, Plays,
     Fairytales, Philosophy, History, Religious Texts), public: true.

The site shows these only in Read in English mode; a tap on a word gives its
Russian definition, and their words count on the English leaderboard.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/english_library.py                 # 500 books
    python3 tools/english_library.py --count 50      # a smaller run first
    python3 tools/english_library.py --dry-run       # list what it would take
"""
import argparse, csv, html, io, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MANIFEST = "private/books/index.json"
OUTDIR = "public/books/english"
IMGDIR = "public/books/img"
STATE = "tools/english_library_state.json"
CATALOG = "tools/translations/pg_catalog.csv"
CAT_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
UA = "SamovarEnglishLibrary/1.0 (https://samovar.live; building a reading list from public-domain texts)"
GAP = 2.0                      # seconds between requests to one site
try:
    from PIL import Image
except Exception:
    Image = None

_last = {}


def get(url, tries=5, binary=False):
    host = urllib.parse.urlparse(url).netloc
    for i in range(tries):
        wait = _last.get(host, 0) + GAP - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=90).read()
            return data if binary else data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(10 * (i + 1) if e.code in (429, 503) else 3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.split(r"[;:]|, or,| or ", s)[0]
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"^(the|a|an) ", "", re.sub(r"\s+", " ", s).strip())
    return s


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60].strip("-") or "book"


# ---------------------------------------------------------------- catalogue
def load_catalog():
    if not os.path.exists(CATALOG) or os.path.getsize(CATALOG) < 1_000_000:
        print("downloading the Gutenberg catalogue …", flush=True)
        io.open(CATALOG, "wb").write(get(CAT_URL, binary=True))
    out = {}
    with io.open(CATALOG, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                out[int(r["Text#"])] = r
            except Exception:
                pass
    return out


SKIP_SUBJ = re.compile(r"cookery|cooking|dictionar|encyclop|periodicals|indexes|bibliograph|catalogs|"
                       r"language and languages|grammar|textbooks|handbooks|manuals|thesauri|synonyms|"
                       r"etiquette|sex instruction|law -- |statutes|census|registers|erotic|pornograph|"
                       r"mathematics|calculus|arithmetic|algebra|geometry|sabotage|military art", re.I)
SKIP_TITLE = re.compile(r"\b(index|dictionary|thesaurus|manual|encyclop|magazine|journal|almanac|cookbook|erotic|"
                        r"complete works|collected works|works of|vol\.|volume \d|the bible|"
                        r"punch, or the london|notes and queries|report of)\b", re.I)
RUSSIAN = re.compile(r"tolstoy|dostoevsk|dostoyevsk|chekhov|gogol|turgenev|pushkin|lermontov|gorky|"
                     r"goncharov|bulgakov|andreyev|kuprin|bunin|leskov|saltykov", re.I)
# Writers who did not write in English. Gutenberg often leaves the translator
# off the record, so a translation would otherwise pass as an original.
FOREIGN = re.compile(
    r"\b(dumas|verne|hugo, victor|balzac|flaubert|zola|maupassant|stendhal|proust|voltaire|rousseau|"
    r"moli[eè]re|rabelais|montaigne|descartes|pascal|leroux|gaboriau|sue, eug|saint-exup|"
    r"goethe|schiller|kafka|nietzsche|kant|hegel|marx|engels|freud|hesse|mann, thomas|grimm|"
    r"spyri|wyss|andersen|ibsen|strindberg|lagerl|kierkegaard|collodi|dante|boccaccio|machiavelli|"
    r"cervantes|homer|virgil|ovid|sophocles|euripides|aeschylus|aristophanes|aristotle|plato|"
    r"marcus aurelius|epictetus|seneca|cicero|plutarch|herodotus|thucydides|augustine|"
    r"kempis|erasmus|spinoza|sun tzu|sunzi|laozi|lao-tzu|confucius|musashi|vatsyayana|"
    r"sienkiewicz|ha[sš]ek|cap|more, thomas|luther|calvin|tacitus|livy|lucretius|"
    r"apuleius|petronius|chrétien|chretien|alighieri|tolstoi)\b", re.I)


def author_display(authors):
    """'Austen, Jane, 1775-1817' → ('Jane Austen', '1775–1817', 'Austen')."""
    first = (authors or "").split(";")[0].strip()
    first = re.sub(r"\s*\[[^\]]*\]\s*$", "", first)
    m = re.match(r"^(.*?),\s*(\d{3,4}\??(?: BCE)?)?-(\d{3,4}\??)?\s*$", first)
    years = ""
    if m:
        first = m.group(1)
        years = "%s–%s" % (m.group(2) or "", m.group(3) or "")
    parts = [p.strip() for p in first.split(",") if p.strip()]
    parts = [p for p in parts if not re.match(r"^\d", p)]
    if len(parts) >= 2:
        name = parts[1] + " " + parts[0]
        name = re.sub(r"\s*\(([^)]*)\)", "", name).strip()
    else:
        name = parts[0] if parts else "Anonymous"
    return name, years.strip("–"), (parts[0] if parts else name)


def category(row, words):
    subj = (row.get("Subjects") or "") + " ; " + (row.get("Bookshelves") or "")
    s = subj.lower()
    if "drama" in s or re.search(r"\b(tragedies|comedies|plays)\b", s):
        return "Plays"
    if "poetry" in s or "poems" in s:
        return "Poetry"
    if "fairy tales" in s or "fables" in s or "folklore" in s:
        return "Fairytales"
    if "short stories" in s:
        return "Short Stories"
    if re.search(r"philosoph|ethics|political science|economics", s) and "fiction" not in s:
        return "Philosophy"
    if re.search(r"\bbible\b|christian|theology|religio", s) and "fiction" not in s:
        return "Religious Texts"
    if re.search(r"history|biograph|autobiograph|description and travel|memoir", s) and "fiction" not in s:
        return "History"
    return "Novellas" if words and words < 40000 else "Novels"


# ---------------------------------------------------------------- popular list
def popular_ids(pages):
    seen, out = set(), []
    for p in range(pages):
        start = 1 + 25 * p
        h = get("https://www.gutenberg.org/ebooks/search/?sort_order=downloads&start_index=%d" % start)
        if not h:
            continue
        got = 0
        for m in re.finditer(r'href="/ebooks/(\d+)"', h):
            n = int(m.group(1))
            if n not in seen:
                seen.add(n)
                out.append(n)
                got += 1
        print("\r  popular list: %d ids (page %d)" % (len(out), p + 1), end="", flush=True)
        if not got:
            break
    print()
    return out


# ---------------------------------------------------------------- text → chapters
HEAD = re.compile(
    r"^(?:[A-Z][A-Za-z ]{0,30}:\s*)?(?:(?:CHAPTER|Chapter|CHAP\.|Chap\.|STAVE|Stave|LETTER|Letter|ACT|Act|SCENE|Scene|CANTO|Canto|"
    r"BOOK|Book|PART|Part|VOLUME|Volume|EPILOGUE|Epilogue|PROLOGUE|Prologue|PREFACE|Preface|"
    r"INTRODUCTION|Introduction|CONCLUSION|Conclusion)\b[^\n]{0,250}"
    r"|[IVXLC]{1,7}\.(?:\s+[^\n]{1,70})?|[IVXLC]{1,7}|\d{1,3}\.?)$")
BARE = re.compile(r"^(?:[IVXLC]{1,7}|\d{1,3})\.?$|^(?:CHAPTER|Chapter|STAVE|Stave|BOOK|Book|PART|Part|CANTO|Canto)\s+[\wIVXLC]+\.?$")
TIER = re.compile(r"^(?:BOOK|Book|PART|Part|VOLUME|Volume|ACT|Act)\b")


def strip_gutenberg(t):
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG[^\n]*\n", t, re.I)
    if m:
        t = t[m.end():]
    m = re.search(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG", t, re.I)
    if m:
        t = t[:m.start()]
    # Producer credits at the top.
    t = re.sub(r"^\s*(?:Produced by|E-text prepared by|Transcribed from|This etext was)[^\n]*(?:\n[^\n]+)*\n\n", "", t, flags=re.I)
    return t.strip()


def blocks_of(t, keep_lines):
    out = []
    for b in re.split(r"\n\s*\n", t):
        lines = [l.rstrip() for l in b.split("\n") if l.strip()]
        if not lines:
            continue
        if keep_lines:
            out.append(("lines", [l.strip() for l in lines]))
        else:
            txt = " ".join(l.strip() for l in lines)
            txt = re.sub(r"_([^_]+)_", r"\1", txt)
            out.append(("p", re.sub(r"\s+", " ", txt).strip(), [l.strip() for l in lines]))
    return out


def is_head(block):
    kind, v = block[0], block[1]
    if kind == "p":
        raw = block[2] if len(block) > 2 else [v]
        # "I" / "CHAPTER IV" on its own line with the title on the next.
        if len(raw) <= 3 and len(v) < 120 and BARE.match(raw[0]):
            return True
        lim = 260 if re.match(r"^(?:CHAPTER|Chapter|CHAP|STAVE|Stave|CANTO|Canto|BOOK|Book|PART|Part)\b", v) else 100
        return len(v) < lim and bool(HEAD.match(v[:lim]))
    return len(v) <= 2 and len(" ".join(v)) < 100 and bool(HEAD.match(v[0]))


def head_text(block):
    kind, v = block[0], block[1]
    if kind == "p" and len(block) > 2 and len(block[2]) > 1 and BARE.match(block[2][0]):
        return block[2][0].rstrip(".") + ". " + " ".join(block[2][1:])
    return v if kind == "p" else " ".join(v)


def words_in(blocks):
    n = 0
    for b in blocks:
        kind, v = b[0], b[1]
        n += len((v if kind == "p" else " ".join(v)).split())
    return n


def chapters_of(text, keep_lines):
    bl = blocks_of(text, keep_lines)
    secs, cur, tier = [], {"h": "", "b": []}, ""
    skip = -1
    # A book with real CHAPTER headings uses bare numerals ("1", "IV") only
    # for breaks inside a chapter: those are not chapters.
    KW = re.compile(r"^(?:CHAPTER|Chapter|CHAP|STAVE|Stave|CANTO|Canto|LETTER|Letter)\b")
    keyword_book = sum(1 for b in bl if is_head(b) and KW.match(head_text(b))) >= 3
    BARE_NUM = re.compile(r"^(?:[IVXLC]{1,7}|\d{1,3})\.?(?:\s|$)")
    for bi, b in enumerate(bl):
        if bi == skip:
            continue
        if is_head(b) and keyword_book and BARE_NUM.match(head_text(b)) and not KW.match(head_text(b)):
            cur["b"].append(b)
            continue
        if is_head(b):
            h = head_text(b).strip().rstrip(".")
            # "1" or "CHAPTER IV" alone, its title in the next block: join them.
            if BARE.match(h) and bi + 1 < len(bl):
                nxt = head_text(bl[bi + 1]).strip()
                if 0 < len(nxt) < 80 and not re.search(r"[.!?,;\"\u201d]$", nxt) and not is_head(bl[bi + 1]):
                    h = h + ". " + nxt
                    skip = bi + 1
            if cur["b"] or cur["h"]:
                secs.append(cur)
            if TIER.match(h):
                # A higher tier (BOOK, PART, ACT…): the chapters under it carry
                # it in their heading, which the Contents shows as a level.
                tier = h
                cur = {"h": h, "b": []}
            else:
                cur = {"h": (tier + " — " + h) if tier else h, "b": []}
            continue
        cur["b"].append(b)
    secs.append(cur)
    # A contents list reads as a run of headings with nothing under them, and
    # a title page as a few lines: everything before the first section with
    # real text goes, when there is not much of it.
    first_real = next((i for i, s in enumerate(secs) if words_in(s["b"]) >= 150), None)
    if first_real is not None and sum(words_in(s["b"]) for s in secs[:first_real]) < 400:
        secs = secs[first_real:]
    # Keyed with its tier: Book the Second's CHAPTER I is not Book the First's.
    keyof = lambda h: " | ".join([" ".join(re.findall(r"[a-z0-9]+", x.lower())[:3]) for x in h.split(" — ")[:-1]] +
                                 [" ".join(re.findall(r"[a-z0-9]+", h.split(" — ")[-1].lower())[:3])])
    later = {}
    for k, s in enumerate(secs):
        later[keyof(s["h"])] = k
    secs = [s for k, s in enumerate(secs) if not s["h"] or later.get(keyof(s["h"])) == k]
    secs = [s for s in secs if words_in(s["b"]) >= 20]
    # Untitled front matter that is mostly short lines (a title page, a list
    # of contents or illustrations) is not reading.
    def listy(b):
        ws = [len((x[1] if x[0] == "p" else " ".join(x[1])).split()) for x in b]
        return ws and sum(1 for w in ws if w < 14) > 0.4 * len(ws)
    secs = [s for s in secs if s["h"] or not listy(s["b"])]
    for s in secs:
        if not s["h"]:
            s["h"] = "Opening"
    if len(secs) < 2 or sum(words_in(s["b"]) for s in secs) < 0.6 * words_in(bl):
        # No usable headings: parts of about 3,000 words.
        secs, cur, n = [], {"h": "", "b": []}, 0
        for b in bl:
            cur["b"].append(b)
            n += words_in([b])
            if n >= 3000:
                secs.append(cur)
                cur, n = {"h": "", "b": []}, 0
        if cur["b"]:
            secs.append(cur)
        for i, s in enumerate(secs, 1):
            s["h"] = "Part %d" % i
    return secs


def esc(s):
    return html.escape(s, quote=False)


def fb2(title, author, secs, poem):
    first, _, last = author.rpartition(" ")
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.1">',
           "<description><title-info>",
           "<book-title>%s</book-title>" % esc(title),
           "<author><first-name>%s</first-name><last-name>%s</last-name></author>" % (esc(first), esc(last or author)),
           "<lang>en</lang>",
           "</title-info><document-info><program-used>tools/english_library.py</program-used></document-info></description>",
           "<body>"]
    for s in secs:
        out.append("<section><title><p>%s</p></title>" % esc(s["h"]))
        for blk in s["b"]:
            kind, v = blk[0], blk[1]
            if kind == "lines" and poem:
                out.append("<poem><stanza>%s</stanza></poem>" % "".join("<v>%s</v>" % esc(l) for l in v))
            elif kind == "lines":
                out.append("<p>%s</p>" % esc(" ".join(v)))
            else:
                out.append("<p>%s</p>" % esc(v))
        out.append("</section>")
    out.append("</body></FictionBook>")
    return "\n".join(out)


# ---------------------------------------------------------------- extras
def cover(n):
    path = os.path.join(IMGDIR, "pg%d.jpg" % n)
    if os.path.exists(path):
        return "img/pg%d.jpg" % n
    data = get("https://www.gutenberg.org/cache/epub/%d/pg%d.cover.medium.jpg" % (n, n), binary=True)
    if not data or len(data) < 2000:
        return ""
    os.makedirs(IMGDIR, exist_ok=True)
    if Image is not None:
        try:
            im = Image.open(io.BytesIO(data)).convert("RGB")
            if im.width > 500:
                im = im.resize((500, round(im.height * 500 / im.width)), Image.LANCZOS)
            im.save(path, "JPEG", quality=82, optimize=True, progressive=True)
            return "img/pg%d.jpg" % n
        except Exception:
            pass
    open(path, "wb").write(data)
    return "img/pg%d.jpg" % n


def wiki_blurb(title, surname):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "list": "search", "srlimit": 3,
                                "srsearch": '"%s" %s' % (re.split(r"[;:]", title)[0].strip(), surname)})
    raw = get("https://en.wikipedia.org/w/api.php?" + q)
    if not raw:
        return None
    try:
        hits = json.loads(raw)["query"]["search"]
    except Exception:
        return None
    for h in hits:
        q2 = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "extracts", "exintro": 1,
                                     "explaintext": 1, "exsentences": 3, "redirects": 1, "titles": h["title"]})
        raw2 = get("https://en.wikipedia.org/w/api.php?" + q2)
        try:
            pg = list(json.loads(raw2)["query"]["pages"].values())[0]
        except Exception:
            continue
        ex = (pg.get("extract") or "").strip()
        if ex and surname.lower() in ex.lower() and norm(title)[:12] in norm(ex) + " " + norm(pg.get("title", "")):
            ex = re.sub(r"\s*\([^)]*\)", "", ex).strip()
            return ex[:600], "https://en.wikipedia.org/wiki/" + urllib.parse.quote(pg["title"].replace(" ", "_"))
    return None


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=500)
    ap.add_argument("--pages", type=int, default=80, help="pages of the downloads list to read (25 a page)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    state = json.load(io.open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    cat = load_catalog()
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    have_titles = {norm(b.get("enTitle") or "") for b in idx if b.get("enTitle") and b.get("lang") != "en"}
    h_auth = {norm(b.get("enTitle") or ""): (b.get("enAuthor") or "").lower() for b in idx if b.get("enTitle")}
    surname_of = lambda row: author_display(row.get("Authors"))[2].lower()
    # Books on the site already — but not this library's own books: those are
    # what it is building, and skipping them would make the clean-up below
    # take them all back off.
    have_gids = {b.get("gutenberg") for b in idx if b.get("gutenberg") and b.get("lang") != "en"}
    try:
        res = json.load(io.open("tools/translations/resolved.json", encoding="utf-8"))
        have_gids |= {v.get("gid") for v in res.values() if isinstance(v, dict) and v.get("gid")}
    except Exception:
        pass

    if "ids" not in state:
        state["ids"] = popular_ids(a.pages)
        io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))
    picked, seen_titles = [], set()
    for n in state["ids"]:
        r = cat.get(n)
        if not r or r.get("Type") != "Text" or (r.get("Language") or "").strip() != "en":
            continue
        authors = r.get("Authors") or ""
        if re.search(r"\[(Translator|Editor)\]", authors) or RUSSIAN.search(authors) or FOREIGN.search(authors):
            continue
        title = re.sub(r"\s+", " ", r.get("Title") or "").strip()
        if SKIP_TITLE.search(title) or SKIP_SUBJ.search(r.get("Subjects") or ""):
            continue
        if n in have_gids:
            continue
        key = norm(title)
        # The same book as one already on the site, under a longer title
        # ("A Christmas Carol in Prose", an illustrated Alice), or one volume
        # of a work in several.
        if re.search(r"\bvol(\.|ume)? ?\d+ \(of \d+\)", title, re.I):
            continue
        if any(len(h) > 8 and key.startswith(h + " ") and surname_of(r) in h_auth.get(h, "")
               for h in have_titles):
            continue
        if not key or key in have_titles or key in seen_titles:
            continue
        seen_titles.add(key)
        picked.append(n)
        if len(picked) >= a.count:
            break
    print("%d books chosen from %d popular titles" % (len(picked), len(state["ids"])), flush=True)
    if a.dry_run:
        for n in picked:
            r = cat[n]
            print("  %6d  %-60s %s" % (n, re.sub(r"\s+", " ", r["Title"])[:60], author_display(r.get("Authors"))[0]))
        return

    # Anything an earlier run added that the list no longer takes (a rule
    # tightened since) comes back off the catalogue.
    keep = set(picked)
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    gone = [b for b in idx if b.get("lang") == "en" and b.get("gutenberg") and b["gutenberg"] not in keep]
    if gone:
        idx = [b for b in idx if b not in gone]
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
        for b in gone:
            state.get("done", {}).pop(str(b["gutenberg"]), None)
            try:
                os.remove(os.path.join("public/books", b["filename"]))
            except Exception:
                pass
        io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))
        print("took back %d book(s) the list no longer includes" % len(gone))

    added = 0
    pending = []
    for i, n in enumerate(picked, 1):
        r = cat[n]
        title = re.sub(r"\s+", " ", r["Title"]).strip()
        short = re.split(r"\s*[;:]\s*", title)[0].strip()
        name, years, surname = author_display(r.get("Authors"))
        slug = "en-" + slugify(short + " " + surname)
        fbpath = os.path.join(OUTDIR, slug + ".fb2")
        if state.get("done", {}).get(str(n)):
            continue
        print("[%d/%d] %s — %s" % (i, len(picked), short, name), flush=True)
        raw = get("https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (n, n)) or \
              get("https://www.gutenberg.org/ebooks/%d.txt.utf-8" % n)
        if not raw:
            print("   !! no text"); continue
        if len(raw) > 4_000_000:
            print("   !! too long (%d MB) — skipped" % (len(raw) // 1_000_000)); continue
        body = strip_gutenberg(raw)
        words = len(body.split())
        catg = category(r, words)
        secs = chapters_of(body, keep_lines=catg in ("Poetry", "Plays"))
        if not secs:
            print("   !! no chapters found"); continue
        io.open(fbpath, "w", encoding="utf-8").write(fb2(short, name, secs, catg == "Poetry"))
        cov = cover(n)
        wb = wiki_blurb(short, surname)
        entry = {"filename": "english/%s.fb2" % slug, "title": short, "author": name, "category": catg,
                 "slug": slug, "public": True, "lang": "en", "words": words,
                 "enTitle": short, "enAuthor": name, "gutenberg": n,
                 "_note": "Text from Project Gutenberg: https://www.gutenberg.org/ebooks/%d" % n}
        if years:
            entry["authorYears"] = years
        if cov:
            entry["cover"] = cov
        if wb:
            entry.update({"blurb": wb[0], "blurbEn": wb[0], "blurbSrc": wb[1], "blurbLang": "en"})
        pending.append(entry)
        state.setdefault("done", {})[str(n)] = slug
        print("   %d chapters, %s words, %s%s" % (len(secs), format(words, ","), catg,
                                                 "" if cov else ", no cover"), flush=True)
        if len(pending) >= 10 or i == len(picked):
            added += flush(pending)
            pending = []
            io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))
    added += flush(pending)
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state))
    print("\nDone: %d added to the catalogue. Push public/books/english, public/books/img and the catalogue." % added)


def flush(entries):
    """Add entries to the catalogue — re-read first, so other scripts' work stays."""
    if not entries:
        return 0
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): k for k, b in enumerate(idx)}
    n = 0
    for e in entries:
        if e["slug"] in by:
            idx[by[e["slug"]]].update(e)
        else:
            idx.append(e)
            n += 1
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    return n


if __name__ == "__main__":
    main()
