#!/usr/bin/env python3
"""Turn the downloaded sources into working parallel books.

For each work in the ledger it does the four things that make a book usable:

  1. RU  — the az.lib.ru download is already FB2 inside a .zip, so it is
           unpacked as-is; a plain-text download is wrapped into a minimal FB2
           with the right title and author.
  2. EN  — pulls the work out of its Gutenberg volume. Many volumes hold
           several works ("Taras Bulba and Other Tales"), so the extractor
           slices from the work's own heading to the next work heading, using
           the fact that a chapter heading is a bare numeral and a work heading
           is not.
  3. ALIGN — pairs Russian paragraphs with English ones, chapter by chapter,
           and writes the per-chapter JSON the reader fetches.
  4. CATALOGUE — adds the entry, with a translator's note built from the
           ledger's own translator and year.

    python3 tools/ingest.py --only oblomov      # one work
    python3 tools/ingest.py --limit 5           # first five that are ready
    python3 tools/ingest.py                     # everything downloaded
    python3 tools/ingest.py --dry-run           # report, write nothing
"""
import argparse, csv, io, json, os, re, sys, zipfile, html, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.abspath(os.path.join(ROOT, "..", "govorim-sources"))
BOOKS = os.path.join(ROOT, "public", "books")
MANIFEST = os.path.join(ROOT, "private", "books", "index.json")
LEDGER = os.path.join(ROOT, "tools", "data", "sources.tsv")

TAGS = re.compile(r"<[^>]+>")
def clean(s):
    s = TAGS.sub(" ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

# ── 1. Russian ───────────────────────────────────────────────────────────
def ru_fb2(slug, title, author):
    """Returns FB2 text, or None. Prefers the real FB2 from az.lib.ru."""
    z = os.path.join(SRC, "ru", slug + ".zip")
    if os.path.exists(z):
        try:
            Z = zipfile.ZipFile(z)
            for n in Z.namelist():
                if n.lower().endswith(".fb2"):
                    return Z.read(n).decode("utf-8", "replace")
        except Exception:
            pass
    f = os.path.join(SRC, "ru", slug + ".fb2")
    if os.path.exists(f):
        return io.open(f, encoding="utf-8", errors="replace").read()
    t = os.path.join(SRC, "ru", slug + ".txt")
    if os.path.exists(t):
        return txt_to_fb2(io.open(t, encoding="utf-8", errors="replace").read(), title, author)
    return None

def txt_to_fb2(text, title, author):
    """Wrap plain text as FB2. Chapter breaks on a lone roman/arabic numeral."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chapters, cur, head = [], [], None
    for p in paras:
        if re.fullmatch(r"(?:глава\s+)?[IVXLC]{1,7}\.?|(?:глава\s+)?\d{1,3}\.?", p.strip(), re.I):
            if cur:
                chapters.append((head, cur)); cur = []
            head = p.strip()
            continue
        cur.append(p)
    if cur:
        chapters.append((head, cur))
    if not chapters:
        chapters = [(None, paras)]
    def esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.1">',
           '<description><title-info><book-title>%s</book-title>'
           '<author><nickname>%s</nickname></author></title-info></description>' %
           (esc(title), esc(author)),
           '<body>', '<title><p>%s</p></title>' % esc(title)]
    for head, ps in chapters:
        out.append("<section>")
        if head:
            out.append("<title><p>%s</p></title>" % esc(head))
        out += ["<p>%s</p>" % esc(p) for p in ps]
        out.append("</section>")
    out += ["</body>", "</FictionBook>"]
    return "\n".join(out)

def build_fb2(chapters, title, author):
    """Write an FB2 containing EXACTLY the chapters we aligned against.

    This is not cosmetic. ru_chapters() drops the az.lib.ru title-page section
    and any «Примечания» apparatus, so its chapter 1 is the first real chapter
    — but the reader parses the ORIGINAL file, where chapter 1 is the title
    page. Every English file then lands one chapter early, which is why the
    opening screen showed front matter beside chapter one's translation.
    Rebuilding the file from the same list the alignment used makes the two
    numberings the same numbering, by construction.
    """
    def esc(t):
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.1">',
           '<description><title-info>',
           '<book-title>%s</book-title>' % esc(title),
           '<author><nickname>%s</nickname></author>' % esc(author),
           '</title-info></description>',
           '<body>',
           '<title><p>%s</p></title>' % esc(title)]
    for head, ps in chapters:
        out.append("<section>")
        if head:
            out.append("<title><p>%s</p></title>" % esc(head))
        out += ["<p>%s</p>" % esc(x) for x in ps]
        out.append("</section>")
    out += ["</body>", "</FictionBook>"]
    return "\n".join(out)

def ru_chapters(fb2):
    """Leaf sections → [(heading, [paragraphs])], mirroring the reader."""
    x = re.sub(r"<binary[\s\S]*?</binary>", "", fb2)
    m = re.search(r"<body(?:\s[^>]*)?>([\s\S]*?)</body>", x)
    if not m:
        return []
    def leaves(s, out):
        parts, depth, start = [], 0, None
        for mm in re.finditer(r"<section(?:\s[^>]*)?>|</section>", s):
            if mm.group(0).startswith("<section"):
                depth += 1
                if depth == 1:
                    start = mm.end()
            else:
                depth -= 1
                if depth == 0:
                    parts.append(s[start:mm.start()])
        if not parts:
            out.append(s)
        else:
            for p in parts:
                leaves(p, out)
    secs = []
    leaves(m.group(1), secs)
    chs = []
    for sec in secs:
        title = re.search(r"<title>([\s\S]*?)</title>", sec)
        head = clean(title.group(1)) if title else ""
        body = re.sub(r"<title>[\s\S]*?</title>", "", sec)
        body = re.sub(r"<epigraph>[\s\S]*?</epigraph>", "", body)
        ps = [clean(p) for p in re.findall(r"<p(?:\s[^>]*)?>([\s\S]*?)</p>", body)]
        ps = [p for p in ps if p]
        if not ps:
            continue
        h = head.lower()
        if re.match(r"^(примечани|комментари|содержание|оглавление|об авторе|"
                    r"сноски|указатель)", h):
            continue
        # az.lib.ru opens with a title-page section: author, title, a line or
        # two of edition data. It is not a chapter and pairing against it
        # shifts every later chapter by one.
        if not chs and len(ps) <= 3 and sum(len(x) for x in ps) < 400:
            continue
        chs.append((head, ps))
    return chs

# ── 2. English ───────────────────────────────────────────────────────────
CHAPTER_HEAD = re.compile(
    r"^(?:chapter|part|book|act)?\s*[IVXLCDM]{1,7}\.?$|^\d{1,3}\.?$|"
    r"^(?:chapter|part|book|act)\s+(?:\d+|[IVXLCDM]+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
    re.I)
FRONT = re.compile(r"project gutenberg|^contents$|^by$|translated|^introduction$|"
                   r"^preface$|copyright|^transcriber", re.I)

# Gutenberg's own ebook header, which is not part of the work at all.
PG_HEADER = re.compile(
    r"^(title|author|translator|illustrator|editor|release date|language|credits|"
    r"other information|posting date|last updated|produced by|contents)[^:]{0,30}:", re.I)
PG_NOTE = re.compile(
    r"^(this e-?book belongs|every effort has been made|the front matter|"
    r"transcriber|updated editions|start of th|end of th|n\.b\.|note[.:—-])", re.I)
# A bare year, a lone translator's name, an edition line: chrome, not text.
PG_STRAY = re.compile(r"^\(?\d{4}\)?\.?$|^[A-Z][a-z]+ [A-Z][a-z]+$")
# A dramatis-personae entry: NAME IN CAPS, then a description.
CAST = re.compile(r"^[A-ZÁÉÍÓÚÀÈÌÒÙÄÖÜÑ][A-ZÁÉÍÓÚÀÈÌÒÙÄÖÜÑ' .\u2019-]{2,40}[.,]\s+[A-Za-z]")
CAST_HEAD = re.compile(r"^(characters|dramatis personae|persons of the drama|"
                       r"personages|the persons)\b", re.I)

# ── proper-name anchors ──────────────────────────────────────────────────
# Names survive translation: Анисья→Anisya, Пётр→Peter, and numerals stay put.
# Comparing those is language-independent and catches the failure a length
# model cannot see — an English cast list "aligned" against Russian dialogue.
TRANSLIT = {
 "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i",
 "й":"i","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t",
 "у":"u","ф":"f","х":"h","ц":"ts","ч":"ch","ш":"sh","щ":"sh","ъ":"","ы":"i","ь":"",
 "э":"e","ю":"iu","я":"ia"}

def translit(w):
    return "".join(TRANSLIT.get(c, c) for c in w.lower())

def ru_keys(text):
    out = set()
    # Capitalised AND all-caps: in a play the speaker names are ПЁТР, АНИСЬЯ,
    # which a "capital followed by lowercase" pattern misses entirely — and
    # those are the strongest anchors the text has.
    for w in re.findall(r"[А-ЯЁ][а-яё]{3,}|[А-ЯЁ]{4,}", text):
        out.add(translit(w)[:3])
    for n in re.findall(r"\d+", text):
        out.add(n)
    return out

def en_keys(text):
    out = set()
    for w in re.findall(r"[A-ZÁÉÍÓÚÀÈÌÒÙÄÖÜÑ][a-záéíóúàèìòùäöüñ]{3,}|"
                        r"[A-ZÁÉÍÓÚÀÈÌÒÙÄÖÜÑ]{4,}", text):
        out.add(w.lower().replace("y", "i")[:3])
    for n in re.findall(r"\d+", text):
        out.add(n)
    return out

def anchor_score(ru_text, en_text):
    a, b = ru_keys(ru_text), en_keys(en_text)
    if not a or not b:
        return 0.0
    shared = len(a & b)
    if shared < 2:                # one shared prefix is coincidence
        return 0.0
    return shared / min(len(a), len(b))

def find_start(ru_ps, en_ps, max_ru=25, max_en=60):
    """The first paragraph pair that is genuinely the same passage.

    Front matter is asymmetric in both directions: Gutenberg stacks an ebook
    header and a cast list above the English, while the Russian edition opens
    on a subtitle and two epigraphs the translator dropped. Trimming one side
    only moves the error. So search both openings for the first pair that
    shares real anchors, and start there — earlier Russian paragraphs simply
    get no English beside them, which is honest and reads correctly.
    """
    best, bi, bj = 0.34, 0, 0
    for i, rp in enumerate(ru_ps[:max_ru]):
        if len(rp) < 50 or len(ru_keys(rp)) < 2:
            continue
        for j, ep in enumerate(en_ps[:max_en]):
            # Prefer an earlier meeting point when scores are close: front
            # matter is short, so the true start is near the top, and a later
            # coincidental match would throw the whole book out of step.
            sc = anchor_score(rp, ep) - 0.0015 * (i + j)
            if sc > best:
                best, bi, bj = sc, i, j
    return bi, bj

def spine_order(Z):
    """Reading order from the EPUB's own spine.

    Sorting filenames alphabetically puts "-10" before "-2", which silently
    reads the book out of order — chapters interleave and every alignment
    downstream is nonsense. The spine is the authoritative order.
    """
    try:
        opf = next(n for n in Z.namelist() if n.endswith(".opf"))
        x = Z.read(opf).decode("utf-8", "replace")
        base = os.path.dirname(opf)
        ids = dict(re.findall(r'<item\b[^>]*id="([^"]+)"[^>]*href="([^"]+)"', x))
        ids.update({i: h for h, i in re.findall(
            r'<item\b[^>]*href="([^"]+)"[^>]*id="([^"]+)"', x)})
        order = []
        for idref in re.findall(r'<itemref[^>]*idref="([^"]+)"', x):
            href = ids.get(idref)
            if not href:
                continue
            full = os.path.normpath(os.path.join(base, html.unescape(href)))
            full = full.replace(os.sep, "/")
            if full in Z.namelist() and full.endswith((".htm", ".html", ".xhtml")):
                order.append(full)
        if order:
            return order
    except Exception:
        pass
    def natkey(n):
        return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", n)]
    return sorted((n for n in Z.namelist()
                   if n.endswith((".htm", ".html", ".xhtml"))), key=natkey)

def epub_blocks(path):
    Z = zipfile.ZipFile(path)
    parts = spine_order(Z)
    out = []
    for n in parts:
        t = Z.read(n).decode("utf-8", "replace")
        t = re.sub(r"<(script|style)[\s\S]*?</\1>", "", t)
        for m in re.finditer(r"<(h[1-6])[^>]*>([\s\S]*?)</\1>|<p[^>]*>([\s\S]*?)</p>", t):
            if m.group(1):
                h = clean(m.group(2))
                if h:
                    out.append(("H", h))
            else:
                pp = clean(m.group(3))
                if pp:
                    out.append(("P", pp))
    return out

# Typographic punctuation must be folded to ASCII BEFORE NFKD, which drops it
# rather than decomposing it. Korolenko's volume heads its story "MAKAR\u2019S
# DREAM" with a curly apostrophe; our source table writes a straight one. Left
# alone those normalise to "makars dream" and "makar s dream", which never meet
# \u2014 and the whole volume comes back instead of the story.
SMART = {0x2018: "'", 0x2019: "'", 0x201a: "'", 0x201b: "'",
         0x201c: '"', 0x201d: '"', 0x2032: "'", 0x2035: "'",
         0x2013: "-", 0x2014: "-", 0x2012: "-", 0x2212: "-", 0x00ad: "-"}

# Volumes that title a work differently from our source table. Fuzzy matching
# cannot bridge these \u2014 no amount of it turns "light" into "gentle".
EN_TITLE_ALIASES = {
    "light breathing": ["gentle breathing"],     # \u0411\u0443\u043d\u0438\u043d, Koteliansky/Woolf 1922
}

def norm_title(s):
    s = str(s or "").translate(SMART)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def toc_entries(Z, spine):
    """[(label, spine_index, char_offset)] from the volume's own TOC.

    A TOC entry names a work AND says exactly where it starts \u2014 file plus
    anchor. That pair is a position in the whole document, which is what both
    of our failure modes need: PG 44998 keeps a four-story volume in ONE file
    separated only by id anchors, so file-level slicing returns everything,
    while PG 62555 splits works across files but heads each with a bare roman
    numeral, so scanning for headings finds nothing.
    """
    names = [n for n in Z.namelist()
             if n.lower().endswith(("toc.xhtml", "nav.xhtml", "toc.ncx"))]
    base = {n.split("/")[-1]: i for i, n in enumerate(spine)}
    cache, out = {}, []
    for tn in names:
        try:
            raw = Z.read(tn).decode("utf-8", "ignore")
        except Exception:
            continue
        for m in re.finditer(
                r'<(?:a|content)[^>]+(?:href|src)="([^"#]*)(?:#([^"]*))?"[^>]*>(.*?)</(?:a|content)>',
                raw, re.S | re.I):
            lab = clean(m.group(3))
            # Page-number links ("[57]") and bare numerals are not works.
            if not lab or re.fullmatch(r"\[?[ivxlcdm\d]+\]?", lab, re.I):
                continue
            si = base.get(m.group(1).split("/")[-1])
            if si is None:
                continue
            anchor, off = m.group(2), 0
            if anchor:
                if si not in cache:
                    cache[si] = Z.read(spine[si]).decode("utf-8", "ignore")
                a = re.search(r'id=["\']%s["\']' % re.escape(anchor), cache[si])
                off = a.start() if a else 0
            out.append((lab, si, off))
        if out:
            break
    return out


def paras_between(Z, spine, start, end):
    """Paragraphs from one global position up to the next."""
    si, so = start
    ei, eo = end if end else (len(spine) - 1, None)
    chunks = []
    for i in range(si, min(ei, len(spine) - 1) + 1):
        doc = Z.read(spine[i]).decode("utf-8", "replace")
        a = so if i == si else 0
        b = eo if (i == ei and eo is not None) else len(doc)
        chunks.append(doc[a:b])
    body = re.sub(r"<(script|style)[\s\S]*?</\1>", "", "\n".join(chunks))
    out = []
    for m in re.finditer(r"<p[^>]*>([\s\S]*?)</p>", body):
        t = clean(m.group(1))
        if t:
            out.append(t)
    return out


def toc_slice(path, want_title):
    """One work's paragraphs, located through the TOC. None when not found."""
    try:
        Z = zipfile.ZipFile(path)
    except Exception:
        return None
    spine = spine_order(Z)
    toc = toc_entries(Z, spine)
    if not toc or not want_title:
        return None
    want = norm_title(want_title)
    wants = [want] + EN_TITLE_ALIASES.get(want, [])
    hits = [i for i, (lab, _s, _o) in enumerate(toc)
            if any(norm_title(lab) == w for w in wants)]
    if not hits:
        hits = [i for i, (lab, _s, _o) in enumerate(toc)
                if any(len(norm_title(lab)) > 6
                       and (norm_title(lab) in w or w in norm_title(lab))
                       for w in wants)]
    best = None
    for h in hits:
        _lab, si, so = toc[h]
        nxt = None
        for _l2, s2, o2 in toc[h + 1:]:
            if (s2, o2) > (si, so):
                nxt = (s2, o2)
                break
        ps = paras_between(Z, spine, (si, so), nxt)
        # A volume's title page carries the same label as the work itself;
        # only one of the two has the text under it.
        if ps and (best is None or len(ps) > len(best)):
            best = ps
    return best

def en_extract(path, want_title):
    """Blocks belonging to one work inside a volume, as [(heading, [paras])]."""
    # The TOC is the one place a volume reliably states what it contains and
    # where each piece begins, so it is tried before scanning for headings.
    ts = toc_slice(path, want_title)
    # A TOC entry bearing the work's title is sometimes its title PAGE, with
    # the text itself filed under later entries named something else — "Part
    # I", "Fragment I". Andreyev's volume does exactly that, and the slice
    # comes back as five lines and 43 words. Anything that small is front
    # matter, not a work, so fall through to the heading scan instead of
    # replacing a good pairing with a title page.
    if ts and len(ts) >= 8 and sum(len(t.split()) for t in ts) >= 300:
        return [(want_title, ts)]
    blocks = epub_blocks(path)
    cand = [i for i, (k, t) in enumerate(blocks)
            if k == "H" and not CHAPTER_HEAD.match(t) and not FRONT.search(t)]
    # A title page stacks headings — "OBLOMOV", "By Ivan Goncharov", "London",
    # "1915" — and slicing between two of those yields nothing. A real work
    # section contains prose, so keep only headings followed by some.
    work_idx = []
    for k, i in enumerate(cand):
        nxt = cand[k + 1] if k + 1 < len(cand) else len(blocks)
        if sum(1 for kk, _ in blocks[i:nxt] if kk == "P") >= 10:
            work_idx.append(i)
    if not work_idx:
        work_idx = cand
    want = norm_title(want_title)
    start = None
    for i in work_idx:
        h = norm_title(blocks[i][1])
        if h == want or (len(h) > 4 and (h in want or want in h)):
            start = i
            break
    if start is None:
        firstP = next((i for i, (k, _) in enumerate(blocks) if k == "P"), 0)
        start, end = firstP, len(blocks)
    else:
        later = [i for i in work_idx if i > start]
        end = later[0] if later else len(blocks)
    chs, head, cur, in_cast = [], "", [], False
    for k, t in blocks[start:end]:
        if k == "H":
            if CAST_HEAD.match(t):
                in_cast = True
                continue
            if CHAPTER_HEAD.match(t):
                in_cast = False
                if cur:
                    chs.append((head, cur)); cur = []
                head = t
            continue
        if PG_HEADER.match(t) or PG_NOTE.match(t):
            continue
        if not cur and PG_STRAY.match(t):
            continue
        # The cast list is KEPT. Both editions carry one, and "PETER
        # IGNÁTITCH. A well-to-do peasant, 42 years old" pairs precisely with
        # «Петр -- мужик богатый, 42-х лет». Dropping it from one side only is
        # what threw the whole play out of step.
        in_cast = False
        if FRONT.search(t) and len(t) < 120:
            continue
        cur.append(t)
    if cur:
        chs.append((head, cur))
    return [c for c in chs if c[1]]

# ── 3. Alignment ─────────────────────────────────────────────────────────
def align(ru_ps, en_ps):
    """Monotone DP over paragraph lengths: 1-1, 2-1 and 1-2 moves.

    Translators merge and split paragraphs, so a positional zip drifts and
    never recovers. Cost is the squared difference of proportional lengths, so
    a merge is chosen only when it genuinely balances the two sides.
    """
    if not ru_ps or not en_ps:
        return {}
    R = [max(len(p), 1) for p in ru_ps]
    E = [max(len(p), 1) for p in en_ps]
    scale = sum(E) / max(sum(R), 1)
    n, m = len(R), len(E)
    INF = float("inf")
    d = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    d[0][0] = 0.0
    def cost(r, e):
        exp = r * scale
        return ((e - exp) / max(exp, 1.0)) ** 2
    for i in range(n + 1):
        for j in range(m + 1):
            if d[i][j] == INF:
                continue
            base = d[i][j]
            if i < n and j < m:
                c = base + cost(R[i], E[j])
                if c < d[i+1][j+1]: d[i+1][j+1], bk[i+1][j+1] = c, (i, j, 1, 1)
            if i < n and j + 1 < m:
                c = base + cost(R[i], E[j] + E[j+1]) + 0.10
                if c < d[i+1][j+2]: d[i+1][j+2], bk[i+1][j+2] = c, (i, j, 1, 2)
            if i + 1 < n and j < m:
                c = base + cost(R[i] + R[i+1], E[j]) + 0.10
                if c < d[i+2][j+1]: d[i+2][j+1], bk[i+2][j+1] = c, (i, j, 2, 1)
            if i < n:                                   # RU with no English
                c = base + 0.85
                if c < d[i+1][j]: d[i+1][j], bk[i+1][j] = c, (i, j, 1, 0)
            if j < m:                                   # English with no RU
                c = base + 0.85
                if c < d[i][j+1]: d[i][j+1], bk[i][j+1] = c, (i, j, 0, 1)
    i, j, out = n, m, {}
    while (i, j) != (0, 0):
        step = bk[i][j]
        if step is None:
            break
        pi, pj, dr, de = step
        if dr and de:
            txt = " ".join(en_ps[pj:pj+de])
            for k in range(dr):
                out[pi + k] = txt if k == 0 else ""
            if dr == 2:
                out[pi] = txt
                out.pop(pi + 1, None)
        i, j = pi, pj
    return {k: v for k, v in out.items() if v}

def align_chapters(ru_chs, en_chs):
    """Map Russian chapters to English chapters by evidence, not by position.

    Equal chapter counts are NOT proof of correspondence: an FB2 often carries
    a front-matter section, so RU chapter 1 is a title page while EN chapter 1
    is already Chapter I — and everything after is off by one. That kind of
    drift is invisible to a length model and to a start-of-book check, because
    each chapter still pairs plausibly with the wrong neighbour.

    So score every RU chapter against every EN chapter on shared proper names
    and numbers, then take the best monotone mapping. Chapters with no partner
    are allowed: a preface or an appendix genuinely has none.
    """
    R, E = len(ru_chs), len(en_chs)
    if R == 0 or E == 0:
        return []
    rk = [set().union(*[ru_keys(p) for p in ps]) if ps else set() for _, ps in ru_chs]
    ek = [set().union(*[en_keys(p) for p in ps]) if ps else set() for _, ps in en_chs]
    rlen = [sum(len(p) for p in ps) for _, ps in ru_chs]
    elen = [sum(len(p) for p in ps) for _, ps in en_chs]
    tot_r, tot_e = sum(rlen) or 1, sum(elen) or 1

    def sc(i, j):
        a, b = rk[i], ek[j]
        if not a or not b:
            return 0.0
        overlap = len(a & b) / min(len(a), len(b))
        # a chapter should also be about the right SIZE relative to the book
        fr, fe = rlen[i] / tot_r, elen[j] / tot_e
        size = 1.0 - min(abs(fr - fe) / max(fr, fe, 1e-6), 1.0)
        return 0.75 * overlap + 0.25 * size

    NEG = -1e9
    d = [[NEG] * (E + 1) for _ in range(R + 1)]
    bk = [[None] * (E + 1) for _ in range(R + 1)]
    d[0][0] = 0.0
    SKIP = -0.15                       # mild cost for leaving a chapter unpaired
    for i in range(R + 1):
        for j in range(E + 1):
            if d[i][j] == NEG:
                continue
            if i < R and j < E:
                v = d[i][j] + sc(i, j)
                if v > d[i+1][j+1]: d[i+1][j+1], bk[i+1][j+1] = v, (i, j, 1, 1)
            if i < R:
                v = d[i][j] + SKIP
                if v > d[i+1][j]: d[i+1][j], bk[i+1][j] = v, (i, j, 1, 0)
            if j < E:
                v = d[i][j] + SKIP
                if v > d[i][j+1]: d[i][j+1], bk[i][j+1] = v, (i, j, 0, 1)
    i, j, out = R, E, {}
    while (i, j) != (0, 0):
        st = bk[i][j]
        if st is None:
            break
        pi, pj, dr, de = st
        if dr and de:
            out[pi] = pj
        i, j = pi, pj
    return [out.get(i) for i in range(R)]      # RU chapter → EN chapter or None

def chapter_pair(ru_chs, en_chs):
    """Match RU chapters to EN chapters; fall back to proportional split."""
    if len(ru_chs) == len(en_chs):
        return list(zip([c[1] for c in ru_chs], [c[1] for c in en_chs]))
    en_all = [p for _, ps in en_chs for p in ps]
    total_ru = sum(sum(len(p) for p in ps) for _, ps in ru_chs) or 1
    out, pos = [], 0
    for _, ps in ru_chs:
        share = sum(len(p) for p in ps) / total_ru
        take = max(1, round(share * len(en_all)))
        out.append((ps, en_all[pos:pos + take]))
        pos += take
    if pos < len(en_all) and out:
        out[-1] = (out[-1][0], out[-1][1] + en_all[pos:])
    return out

# ── 4. Notes + catalogue ─────────────────────────────────────────────────
def note(translator, year, en_src, pg, pct):
    who = translator if translator and translator.lower() != "anonymous" else None
    src = ("Project Gutenberg" if pg else (en_src or "a public-domain edition"))
    lead = ("English by %s (%s), public domain." % (who, year) if who
            else "English from a public-domain edition of %s." % year)
    body = (" Swipe right on the text to read it beside the Russian, or tap the "
            "EN button on the right.")
    if pct < 75:
        body += (" The pairing is chapter by chapter rather than sentence by "
                 "sentence: inside a chapter the two columns run alongside each "
                 "other, and some Russian paragraphs have no English beside them.")
    else:
        body += " Paired paragraph by paragraph."
    return lead + body

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only"); ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-embed", action="store_true",
                    help="skip semantic alignment; use the length heuristic")
    ap.add_argument("--model", default=None, help="sentence-transformers model")
    ap.add_argument("--force", action="store_true",
                    help="rebuild works already in the catalogue")
    ap.add_argument("--min-sim", type=float, default=0.62,
                    help="reject a book whose mean paired similarity is below "
                         "this (0.62 is the line between a real translation "
                         "and a plausible-looking mismatch)")
    ap.add_argument("--min-pct", type=int, default=45,
                    help="skip works whose English covers less than this %% "
                         "of the Russian (default 45)")
    ap.add_argument("--public", action="store_true",
                    help='mark the new entries "public": true for Samovar')
    a = ap.parse_args()

    EA = None
    if not a.no_embed:
        try:
            sys.path.insert(0, os.path.join(ROOT, "tools"))
            import embed_align as EA
            if a.model:
                EA.DEFAULT_MODEL = a.model
            EA.load(EA.DEFAULT_MODEL)
            print("semantic alignment: %s\n" % EA.DEFAULT_MODEL)
        except SystemExit:
            raise
        except Exception as e:
            print("embeddings unavailable (%s) — falling back to the length "
                  "heuristic\n" % e)
            EA = None

    rows = list(csv.DictReader(io.open(LEDGER, encoding="utf-8"), delimiter="\t"))
    for r in rows:
        for k, v in list(r.items()):
            if v == "-":
                r[k] = ""
    manifest = json.load(io.open(MANIFEST, encoding="utf-8"))
    have = {e.get("slug") for e in manifest} | {e.get("filename") for e in manifest}

    done = 0
    for r in rows:
        slug = r["slug"]
        if a.only and slug != a.only:
            continue
        if a.limit and done >= a.limit:
            break
        if slug in have and not a.force:
            continue
        fb2 = ru_fb2(slug, r["ru_title"], r["author"])
        enp = os.path.join(SRC, "en", slug + ".epub")
        if not fb2 or not os.path.exists(enp):
            continue
        ru_chs = ru_chapters(fb2)
        try:
            en_chs = en_extract(enp, r["en_title"])
        except Exception as e:
            print("  %-28s EN extract failed: %s" % (slug, e)); continue
        if not ru_chs or not en_chs:
            print("  %-28s no chapters (ru=%d en=%d)" % (slug, len(ru_chs), len(en_chs)))
            continue
        ru_flat = [p for _, ps in ru_chs for p in ps]
        en_flat = [p for _, ps in en_chs for p in ps]

        if EA is not None:
            # ── semantic path ────────────────────────────────────────────
            # Embed each side once, then let similarity decide both which
            # chapters correspond and which paragraphs within them. Nothing
            # here assumes the two texts start together or run in step.
            print("  %-28s working ..." % slug, flush=True)
            rv = EA.encode(ru_flat, EA.DEFAULT_MODEL, cache_key=slug + "-ru",
                           label="RU")
            ev = EA.encode(en_flat, EA.DEFAULT_MODEL, cache_key=slug + "-en",
                           label="EN")
            # How the two sides are matched depends on whether they even
            # agree about what a chapter is. When the counts are close, map
            # chapter to chapter. When they are not — one Russian section
            # against forty English ones, or a hundred and ten against six —
            # a one-to-one mapping discards everything it cannot pair, which
            # is how Рудин ended up with 8% of its English and Дым with none.
            # In that case align the whole book as a single stream and cut
            # the result back into chapters afterwards.
            ratio = len(ru_chs) / max(len(en_chs), 1)
            maps, ru_total, paired, sims = [], 0, 0, []
            if 0.8 <= ratio <= 1.25 and min(len(ru_chs), len(en_chs)) > 1:
                cmap = EA.chapter_map(ru_chs, en_chs, EA.DEFAULT_MODEL,
                                      cache_key=slug)
                ru_off, en_off, o = [], [], 0
                for _, ps in ru_chs:
                    ru_off.append(o); o += len(ps)
                o = 0
                for _, ps in en_chs:
                    en_off.append(o); o += len(ps)
                for ci, (_, ru_ps) in enumerate(ru_chs):
                    j = cmap[ci] if ci < len(cmap) else None
                    if j is None:
                        maps.append({}); ru_total += len(ru_ps); continue
                    en_ps = en_chs[j][1]
                    rvc = rv[ru_off[ci]:ru_off[ci] + len(ru_ps)]
                    evc = ev[en_off[j]:en_off[j] + len(en_ps)]
                    mp = EA.align_paragraphs(ru_ps, en_ps, rvc, evc)
                    maps.append(mp); ru_total += len(ru_ps); paired += len(mp)
                    for k in list(mp)[:40]:
                        if k < len(rvc) and len(evc):
                            sims.append(max(float(rvc[k] @ evc[t])
                                            for t in range(len(evc))))
            else:
                band = max(80, int(0.08 * max(len(ru_flat), len(en_flat))))
                gmap = EA.align_paragraphs(ru_flat, en_flat, rv, ev, band=band)
                g = 0
                for _, ps in ru_chs:
                    mp = {}
                    for k in range(len(ps)):
                        v = gmap.get(g + k)
                        if v:
                            mp[k] = v
                    maps.append(mp); ru_total += len(ps); paired += len(mp)
                    g += len(ps)
                # Sample the quality of what was actually paired. The window
                # is clamped into range: a Russian index can sit well past the
                # end of a shorter English text.
                for k in list(gmap)[:120]:
                    if k >= len(rv) or not len(ev):
                        continue
                    c = min(k, len(ev) - 1)
                    lo = max(0, c - 40)
                    hi = min(len(ev), lo + 80)
                    if hi > lo:
                        sims.append(max(float(rv[k] @ ev[t]) for t in range(lo, hi)))
            start_conf = sum(sims) / len(sims) if sims else 0.0
            start_shift = (0, 0)
            no_anchors = False
        else:
            i0, j0 = find_start(ru_flat, en_flat)
            start_conf = (anchor_score(ru_flat[i0], en_flat[j0])
                          if i0 < len(ru_flat) and j0 < len(en_flat) else 0.0)
            no_anchors = not any(len(ru_keys(p)) >= 2 for p in ru_flat[:25])
            start_shift = (i0, j0)
            en_use = en_flat[j0:]
            maps, ru_total, paired = [], 0, 0
            cmap = align_chapters(ru_chs, en_chs) if min(len(ru_chs), len(en_chs)) > 1 else None
            matched = sum(1 for x in (cmap or []) if x is not None)
            if cmap and matched >= 0.6 * min(len(ru_chs), len(en_chs)):
                for ci, (_, ru_ps) in enumerate(ru_chs):
                    j = cmap[ci]
                    if j is None:
                        maps.append({}); ru_total += len(ru_ps); continue
                    en_ps = en_chs[j][1]
                    k0, l0 = (i0, j0) if (ci == 0 and j == 0) else (0, 0)
                    mp = align(ru_ps[k0:], en_ps[l0:])
                    mp = {k + k0: v for k, v in mp.items()}
                    maps.append(mp); ru_total += len(ru_ps); paired += len(mp)
            else:
                tot = sum(len(ru_flat[k]) for k in range(i0, len(ru_flat))) or 1
                pos, g = 0, 0
                for _, ps in ru_chs:
                    k0 = max(0, min(i0 - g, len(ps)))
                    local = ps[k0:]
                    share = sum(len(x) for x in local) / tot
                    take = int(round(share * len(en_use)))
                    seg = en_use[pos:pos + take]; pos += take
                    mp = align(local, seg) if local and seg else {}
                    mp = {k + k0: v for k, v in mp.items()}
                    maps.append(mp); ru_total += len(ps); paired += len(mp)
                    g += len(ps)

        blank = 1 - (paired / max(ru_total, 1))
        pct = 100 * (1 - blank)
        verdict = "ok" if pct >= 60 else ("thin" if pct >= 35 else "ABRIDGED?")
        # No anchors at all in the opening is "cannot tell", not "wrong".
        if EA is not None:
            flag = "" if start_conf >= 0.55 else "  ← LOW SIMILARITY"
        else:
            flag = ("" if start_conf >= 0.34 else
                    ("  (no names to check)" if no_anchors else "  ← CHECK OPENING"))
        print("  %-28s ru_ch=%-3d en_ch=%-3d paras=%-5d paired=%3.0f%%  "
              "sim=%.2f  %s%s"
              % (slug, len(ru_chs), len(en_chs), ru_total, pct,
                 start_conf, verdict, flag))
        # Similarity is the honest gate. Pairing percentage only says the DP
        # found SOMETHING for each paragraph, and on a mismatched book it
        # cheerfully pairs everything: Дубровский paired 100% against the
        # English of Капитанская дочка. Mean similarity separates them —
        # Олеся and Рудин sit at 0.80 and 0.76, the wrong-text books at 0.42
        # to 0.51.
        reject = None
        if EA is not None and start_conf < a.min_sim:
            reject = "similarity %.2f below --min-sim %.2f" % (start_conf, a.min_sim)
        elif pct < a.min_pct:
            reject = "paired %d%% below --min-pct %d" % (pct, a.min_pct)
        if reject:
            print("       skipped — %s" % reject)
            # Remove anything an earlier, more permissive run left behind, so
            # the library never keeps a book the current threshold rejects.
            if not a.dry_run:
                import shutil
                f = os.path.join(BOOKS, "novel", slug + ".fb2")
                d = os.path.join(BOOKS, slug + "-en")
                if os.path.exists(f):
                    os.remove(f)
                if os.path.isdir(d):
                    shutil.rmtree(d)
                before = len(manifest)
                manifest[:] = [e for e in manifest if e.get("slug") != slug]
                if len(manifest) != before:
                    json.dump(manifest, io.open(MANIFEST, "w", encoding="utf-8"),
                              ensure_ascii=False, indent=2)
                    print("       removed its earlier files and catalogue entry")
            continue
        if a.dry_run:
            done += 1; continue
        os.makedirs(os.path.join(BOOKS, "novel"), exist_ok=True)
        # Write the rebuilt file, not the original, so the reader's chapter
        # numbering matches the alignment's.
        io.open(os.path.join(BOOKS, "novel", slug + ".fb2"), "w",
                encoding="utf-8", newline="\n").write(
                    build_fb2(ru_chs, r["ru_title"], r["author"]))
        d = os.path.join(BOOKS, slug + "-en")
        os.makedirs(d, exist_ok=True)
        for i, mp in enumerate(maps):
            nn = str(i + 1).zfill(2)
            json.dump({str(k): v for k, v in mp.items()},
                      io.open(os.path.join(d, nn + ".json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        entry = {"filename": "novel/%s.fb2" % slug, "title": r["ru_title"],
                 "author": r["author"], "category": r.get("category") or "Novels",
                 "slug": slug, "parallelEn": slug + "-en",
                 "translationNote": note(r.get("translator", ""), r.get("year", ""),
                                         r["en_src"], r["pg"], pct)}
        if r.get("verse") == "1":
            entry["verse"] = True          # so drill generation can skip it
        if a.public:
            entry["public"] = True
        manifest = [e for e in manifest if e.get("slug") != slug]
        manifest.append(entry)
        done += 1
    if not a.dry_run and done:
        json.dump(manifest, io.open(MANIFEST, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    print("\n  %d work(s) processed" % done)

if __name__ == "__main__":
    main()
