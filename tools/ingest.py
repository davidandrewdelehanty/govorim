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
                p = clean(m.group(3))
                if p:
                    out.append(("P", p))
    return out

def norm_title(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()

def en_extract(path, want_title):
    """Blocks belonging to one work inside a volume, as [(heading, [paras])].

    A volume's work headings are the headings that are NOT bare numerals; the
    work runs from its own heading to the next one of those.
    """
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
        # single-work volume: begin after the front matter
        firstP = next((i for i, (k, _) in enumerate(blocks) if k == "P"), 0)
        start, end = firstP, len(blocks)
    else:
        later = [i for i in work_idx if i > start]
        end = later[0] if later else len(blocks)
    chs, head, cur = [], "", []
    for k, t in blocks[start:end]:
        if k == "H":
            if CHAPTER_HEAD.match(t):
                if cur:
                    chs.append((head, cur)); cur = []
                head = t
            continue
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
    ap.add_argument("--min-pct", type=int, default=45,
                    help="skip works whose English covers less than this %% "
                         "of the Russian (default 45)")
    ap.add_argument("--public", action="store_true",
                    help='mark the new entries "public": true for Samovar')
    a = ap.parse_args()

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
        if slug in have:
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
        # A Russian text that arrived as a stub pairs at a flattering 100%
        # against an equally short English slice, and ships as a four-paragraph
        # «Майская ночь». Judge the RU side on its own terms first.
        ru_words = sum(len(p.split()) for _, ps in ru_chs for p in ps)
        if r.get("verse") != "1" and ru_words < 400:
            print("  %-28s RU text looks truncated (%d words) — skipped"
                  % (slug, ru_words))
            continue
        pairs = chapter_pair(ru_chs, en_chs)
        maps, ru_total, paired = [], 0, 0
        for ru_ps, en_ps in pairs:
            mp = align(ru_ps, en_ps)
            maps.append(mp); ru_total += len(ru_ps); paired += len(mp)
        blank = 1 - (paired / max(ru_total, 1))
        pct = 100 * (1 - blank)
        verdict = "ok" if pct >= 60 else ("thin" if pct >= 35 else "ABRIDGED?")
        print("  %-28s ru_ch=%-3d en_ch=%-3d paras=%-5d paired=%3.0f%%  %s"
              % (slug, len(ru_chs), len(en_chs), ru_total, pct, verdict))
        if pct < a.min_pct:
            print("       skipped — below --min-pct %d; a translation this far "
                  "short of the Russian is usually an abridgement" % a.min_pct)
            continue
        if a.dry_run:
            done += 1; continue
        os.makedirs(os.path.join(BOOKS, "novel"), exist_ok=True)
        io.open(os.path.join(BOOKS, "novel", slug + ".fb2"), "w",
                encoding="utf-8", newline="\n").write(fb2)
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
        manifest.append(entry)
        done += 1
    if not a.dry_run and done:
        json.dump(manifest, io.open(MANIFEST, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    print("\n  %d work(s) processed" % done)

if __name__ == "__main__":
    main()
