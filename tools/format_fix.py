#!/usr/bin/env python3
"""Tidy FB2s whose text reads strangely (see tools/format_audit.py).

Operations, each run on every leaf <section>:
  wiki      strip leftover Wikisource template text: {{эпиграф2|, }}, |, <poem>
  front     drop a publisher's title page / illustration list / contents at the
            start of the book (per book, from tools/format_front.json)
  dupe      drop a first paragraph that only repeats the chapter's own title
  parts     drop a section that is nothing but a part heading («Часть вторая»)
  split     cut a chapter at a «ГЛАВА N» line left inside it
  verse     set a run of short lines as verse: <poem data-verse> with stanzas
            rebuilt where sentence-final punctuation shows them. In a Poetry
            book the test is loose (ladders, lower-case starts); in prose it
            is strict, so dialogue and hard-wrapped pages stay prose
  dates     a poem's date under it («1906») becomes a byline; a lone «2» or
            «IV» over a poem becomes a centred subtitle
  heads     the short title line just above a poem («Полусонет.», «* * *»)
            becomes a centred subtitle
  title     the book's own title at the head of the text, set as a title

Plays, Theatrical Performances, Religious Texts and Soviet Textbooks are left
to their own layouts by verse/dates/heads. A poem whose first lines repeat its
section title is handled by tools/format_detitle.py, run after this.

`verse`, `dates`, `heads` and `title` keep every paragraph's index (a <v> or
<subtitle> counts as a paragraph, as the <p> did); the others change indices, so a book with parallel English must have
its English rebuilt afterwards. --index-safe runs only wiki + verse + title, for books
whose English cannot be rebuilt.

    python3 tools/format_fix.py --only carroll-looking-glass --dry
    python3 tools/format_fix.py --category Translations
    python3 tools/format_fix.py --ops wiki,verse,dates,heads      # whole library

The original FB2 is kept once in tools/format-orig/.
"""
import io, json, os, re, shutil, sys

ORIG = "tools/format-orig"
FRONT = "tools/format_front.json"
BLOCK = re.compile(r"<p>.*?</p>|<empty-line/>|<poem[^>]*>.*?</poem>|<cite>.*?</cite>|<subtitle>.*?</subtitle>|"
                   r"<epigraph>.*?</epigraph>|<image[^>]*/>|<table>.*?</table>|<section>.*?</section>", re.S)
HEAD = re.compile(r"^(?:ГЛАВА|Глава)\s+(?:[IVXLCІ]+|\d+|[А-ЯЁа-яё-]+)\.?(?:\s*[.:—–-]\s*.{0,80}|\s+[А-ЯЁ].{0,80})?$")
PART = re.compile(r"^(часть|книга|том)\s+\S+\.?$|^[IVXLC]{1,6}\.?$", re.I)
POETRY = [False]
STARS = re.compile(r"^\s*\*(?:\s*\*)*\s*$")
MONTHS = r"(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*"
DATE = re.compile(r"^[\[(<]?(?:[А-ЯЁ][а-яё.-]+,?\s+)?(?:\d{1,2}[\s.]+(?:\d{1,2}|" + MONTHS + r")[\s.]+)?(?:\d{4}|" + MONTHS + r"\s+\d{4})(?:\s*[-–—]\s*\d{2,4})?(?:\s*(?:г\.|года?))?(?:,?\s+[А-ЯЁ][а-яё.-]+)?\.?[\])>]?$")
_DATE1, _DATE2 = DATE, re.compile(r"^\d{1,2}\.[IVX]{1,4}\.(?:\d{2}|\d{4})\.?$")
class _AnyDate:
    def match(self, x):
        return _DATE1.match(x) or _DATE2.match(x)
DATE = _AnyDate()
SENT_END = re.compile(r"[.!?…]+[»”\"')]*$")


def plain(x):
    x = re.sub(r"[\u200e\u200f\u200b\ufeff]", "", re.sub(r"<[^>]+>", "", x))
    return re.sub(r"\s+", " ", x).strip()


def unesc(t):
    return t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def is_p(b):
    return b.startswith("<p>")


# ------------------------------------------------------------------ verse --
def verse_like(lines):
    n = len(lines)
    if n < 4:
        return False
    if any(len(x) < 3 or len(x) > 80 for x in lines):
        return False
    if sum(1 for x in lines if x.lstrip()[:1] in "—–-") > n * 0.4:
        return False
    if sum(1 for x in lines if len(re.sub(r"[^А-ЯЁA-Z]", "", x)) > 0.6 * len(re.sub(r"[^А-ЯЁа-яёA-Za-z]", "", x) or "x")) > n * 0.25:
        return False                                  # headers in capitals: a letter, a telegram
    if sum(1 for x in lines if re.search(r"\d", x)) > n * 0.3:
        return False                                  # a list or a table
    if sum(1 for x in lines if BYLINE.match(x)) >= 2:
        return False                                  # a title page, not a poem
    caps = sum(1 for x in lines if re.match(r"^[«\"„(…—–\s-]*[А-ЯЁA-Z]", x))
    if caps < n * 0.7:
        return False
    ends = sum(1 for x in lines if SENT_END.search(x))
    if ends > n * 0.6:
        return False                                  # short sentences, not lines of verse
    if sum(len(x) for x in lines) / n > 58:
        return False
    # dialogue with attribution («— Придется, — сказала Королева») is prose
    if sum(1 for x in lines if re.search(r"[,!?…] — [а-яё]", x) or re.match(r"^[«\"„\s]*[—–]", x)) > n * 0.25:
        return False
    if sum(1 for x in lines if len(x) > 60 and SENT_END.search(x)) > max(1, n * 0.2):
        return False
    return True


class _Feats:
    """verse_like() over every window of a run in O(1) each: per-line tests
    summed once, so a 2,000-line poem doesn't cost n³ checks."""
    TESTS = (
        lambda x: len(x) < 3 or len(x) > 80 or bool(re.search(r"[а-яёa-z]-$", x)),   # «Ка- / нады»: a page's broken line
        lambda x: x.lstrip()[:1] in "—–-",
        lambda x: len(re.sub(r"[^А-ЯЁA-Z]", "", x)) > 0.6 * len(re.sub(r"[^А-ЯЁа-яёA-Za-z]", "", x) or "x"),
        lambda x: bool(re.search(r"\d", x) or re.match(r"^[IVXLC]+\.\s", x)),
        lambda x: bool(BYLINE.match(x)),
        lambda x: bool(re.match(r"^[«\"„(…—–\s-]*[А-ЯЁA-Z]", x)),
        lambda x: bool(SENT_END.search(x)),
        len,
        lambda x: bool(re.search(r"[,!?…] — [а-яё]", x) or re.match(r"^[«\"„\s]*(?:[—–]|-\s)", x)
                       or re.search(r"\b(говорит|сказал[аи]?|ответил[аи]?|спросил[аи]?|крикнул[аи]?|прибавил)\b", x)),
        lambda x: len(x) > 60 and bool(SENT_END.search(x)),
        lambda x: len(x) > 62,
    )

    def __init__(self, lines):
        self.sums = []
        for f in self.TESTS:
            acc, row = 0, [0]
            for x in lines:
                acc += int(f(x)); row.append(acc)
            self.sums.append(row)

    def ok(self, a, b):
        n = b - a
        if n < 4:
            return False
        c = [r[b] - r[a] for r in self.sums]
        bad, dash, hdr, dig, byl, caps, ends, ln, dia, longs, wide = c
        if wide > n * 0.2 and not POETRY[0]:
            return False                                  # prose printed with the page's line breaks
        if bad or dash > n * 0.4 or hdr > n * 0.25 or dig > n * 0.3 or byl >= 2 or dia > n * 0.25:
            return False
        if POETRY[0]:                      # a poetry book: Mayakovsky's ladders start low, lines end anywhere
            return ends <= n * 0.8 and ln / n <= 58 and longs <= max(1, n * 0.3)
        if caps < n * 0.7:
            # verse that capitalises only odd lines («Наполняйте же стаканы /
            # и кладите поскорей»): short lines, few sentence ends
            return False
        if dia > n * 0.15 or longs > (0 if n < 10 else n * 0.1):
            return False                                  # prose: speech, full long sentences
        return not (ends > n * 0.6 or ln / n > 58)


def stanzas(lines):
    """Stanza breaks were lost on the way from Wikisource; find them again.
    First, a fixed stanza size (4, 6, 8, 3, 5 lines) where every stanza ends a
    sentence — the one with the fewest sentence ends INSIDE its stanzas wins
    (Carroll's aBaBcc sixains end a sentence at line 4 too, so 4 alone would
    cut them wrongly). Failing that, cut where sentences end if that gives
    near-equal stanzas. Failing that, one block."""
    n = len(lines)
    ends = [bool(SENT_END.search(x)) or x.rstrip().endswith((";", "!»", "?»")) for x in lines]
    best = None
    for k in (4, 6, 8, 3, 5):
        if n % k or n // k < 2:
            continue
        if not all(ends[i] for i in range(k - 1, n, k)):
            continue
        inner = sum(1 for i in range(n) if ends[i] and (i + 1) % k)
        score = (inner / (n // k), k)
        if best is None or score < best[0]:
            best = (score, k)
    if best:
        k = best[1]
        return [lines[i:i + k] for i in range(0, n, k)]
    cuts, cur = [], []
    for x in lines:
        cur.append(x)
        if SENT_END.search(x):
            cuts.append(cur); cur = []
    if cur:
        cuts.append(cur)
    sizes = [len(c) for c in cuts]
    if len(cuts) >= 2:
        mode = max(set(sizes), key=sizes.count)
        if 3 <= mode <= 8 and sizes.count(mode) >= 0.75 * len(sizes) and max(sizes) <= 2 * mode:
            return cuts
    return [lines]


def restanza(body):
    """Re-group the stanzas of every verse poem already in the book."""
    n = [0]
    def one(m):
        vs = re.findall(r"<v>(.*?)</v>", m.group(1), re.S)
        groups = stanzas([plain(v) for v in vs])
        k, st = 0, []
        for g in groups:
            st.append("<stanza>\n" + "\n".join("<v>%s</v>" % vs[k + i] for i in range(len(g))) + "\n</stanza>")
            k += len(g)
        new = '<poem data-verse="1">\n' + "\n".join(st) + "\n</poem>"
        if new != m.group(0):
            n[0] += 1
        return new
    out = re.sub(r'<poem data-verse="1">(.*?)</poem>', one, body, flags=re.S)
    return out, n[0]


def poem_heading(block):
    """«Полусонет.», «<strong>Песня</strong>», «ПЕСНЯ МИГНОНЫ» just above a poem: its title."""
    if not is_p(block):
        return False
    x = plain(block)
    if not x or len(x) > 40 or x[0] in "—–-(" or DATE.match(x) or re.search(r"[,:;—–-]$", x):
        return False
    words = len(x.split())
    inner = re.sub(r"^<p>|</p>$", "", block).strip()
    styled = bool(re.fullmatch(r"<(strong|emphasis)>[^<]*</\1>", inner))
    caps = x.upper() == x and re.search(r"[А-ЯЁA-Z]", x)
    if not re.match(r"^[«\"„]?[А-ЯЁA-Z]", x):
        return False
    genre = re.search(r"(сонет|песн|романс|баллад|элеги|ода\b|послани|эпиграмм|молитв|гимн|куплет|станс|мадригал|"
                      r"канцон|серенад|колыбельн|стих|акростих|эпитафи|басн|частушк|марш|канта|псал|дума|плач)", x, re.I)
    return (styled and words <= 6) or (caps and words <= 6) or (words <= 4 and not re.search(r"[.!?…»]$", x)) \
        or (bool(genre) and words <= 4)


def wrap_verse(blocks):
    out, i, n = [], 0, 0
    while i < len(blocks):
        if not is_p(blocks[i]):
            out.append(blocks[i]); i += 1; continue
        j = i
        while j < len(blocks) and is_p(blocks[j]) and len(plain(blocks[j])) <= 80:
            j += 1
        run = blocks[i:j]
        texts = [plain(b) for b in run]
        # find the longest verse-like window inside the run
        best = None
        fe = _Feats(texts)
        for a in range(len(run)):
            for b in range(len(run), a + 3, -1):
                if fe.ok(a, b):
                    best = (a, b); break
            if best:
                break
        if not best:
            out.extend(run if j > i else [blocks[i]]); i = max(j, i + 1); continue
        a, b = best
        # A poem's edges: the line that introduces it («И Мили начала:»), a
        # heading in front of an epigraph, a line of dialogue either side —
        # none of those are verse, so they stay outside the poem.
        edge = lambda x: x.endswith(":") or bool(STARS.match(x)) or bool(DATE.match(x)) or bool(re.match(r"^[«\"„\s]*[—–]", x)) or bool(HEAD.match(x)) or bool(PART.match(x.strip(" .")))\
            or bool(re.match(r"^(ГЛАВА|Глава)\b", x))
        prose = lambda x: len(x) > 40 and bool(SENT_END.search(x)) and not x.startswith(("«", "„", '"'))
        if POETRY[0]:                                  # a poetry book: only separators and dates are not verse
            edge = lambda x: bool(STARS.match(x)) or bool(DATE.match(x)) or bool(re.match(r"^[IVXLC]{1,6}\.?$", x))
            prose = lambda x: False
        while a < b and (edge(texts[a]) or prose(texts[a])):
            a += 1
        while b > a and (texts[b - 1].lstrip()[:1] in "—–" or DATE.match(texts[b - 1]) or STARS.match(texts[b - 1])):
            b -= 1
        if b - a < 4 or not fe.ok(a, b):
            out.extend(run); i = j; continue
        pre = list(run[:a])
        if pre and poem_heading(pre[-1]):
            pre[-1] = "<subtitle>%s</subtitle>" % re.sub(r"^<p>|</p>$", "", pre[-1])
        out.extend('<subtitle>%s</subtitle>' % re.sub(r"^<p>|</p>$", "", x) if is_p(x) and (STARS.match(plain(x)) or re.match(r"^[IVXLC]{1,6}\.?$", plain(x))) else x
                   for x in pre)
        inner = [re.sub(r"^<p>|</p>$", "", x) for x in run[a:b]]
        groups = stanzas([plain(x) for x in run[a:b]])
        k, st = 0, []
        for g in groups:
            st.append("<stanza>\n" + "\n".join("<v>%s</v>" % inner[k + m] for m in range(len(g))) + "\n</stanza>")
            k += len(g)
        out.append('<poem data-verse="1">\n' + "\n".join(st) + "\n</poem>")
        n += 1
        tail = run[b:]
        if tail and DATE.match(plain(tail[0])):          # «1906» under a poem: its date
            out.append('<subtitle data-byline="1">%s</subtitle>' % re.sub(r"^<p>|</p>$", "", tail[0]))
            tail = tail[1:]
        out.extend(tail)
        i = j
    return out, n


# ---------------------------------------------------------------- driver --
def leaf_sections(body):
    out, stack = [], []
    for m in re.finditer(r"<section>|</section>", body):
        if m.group() == "<section>":
            stack.append(m)
        else:
            o = stack.pop()
            inner = body[o.end():m.start()]
            if "<section>" not in inner:
                out.append((o.start(), m.end(), o.end(), m.start()))
    return out


def _norm(t):
    return re.sub(r"[^а-яa-z0-9]+", " ", t.lower().replace("ё", "е")).strip()


BYLINE = re.compile(r"^[(«\"]?\s*(роман|повесть|рассказ|перевод|перевел|перевела|переведено|с английского|с англиского|"
                    r"продолжение|автора|сочинение|полное собрание|для детей|издание)\b", re.I)


def mark_title(body, titles):
    """The book's own title printed at the head of its text becomes
    <subtitle data-booktitle>, and the credit lines under it («Роман Джона
    Голсуорси», «Перевод …», «С английского», an English title in brackets)
    become <subtitle data-byline>: the reader sets them as a title page. A
    title swept into the first poem as its opening line comes out of it."""
    import difflib
    want = [_norm(t) for t in titles if t]
    def is_title(t):
        n = _norm(t)
        return bool(n) and any(difflib.SequenceMatcher(None, n, w).ratio() >= 0.85 for w in want)
    def is_byline(t, prev_byline):
        if len(t) > 90:
            return False
        if BYLINE.match(t) or re.match(r"^\(.*\)\.?$", t):
            return True
        lat = len(re.findall(r"[A-Za-z]", t)); cyr = len(re.findall(r"[А-Яа-яЁё]", t))
        if lat > 3 and lat > cyr:
            return True                                   # the English title
        # a name carried onto its own line: «Луизы Олькот», «ЭДУАРДА БЕЛЛАМИ.»
        return prev_byline and len(t) <= 40 and bool(re.match(r"^([А-ЯЁA-Z][\w.’'-]*\s*){1,4}\.?$", t))
    m = re.search(r"<section>\s*(?:<title>.*?</title>)?", body, re.S)
    if not m:
        return body, False
    head = body[m.end():m.end() + 6000]
    PUBLISHER = re.compile(r"издани[ея]|типограф|книгопродав|издательств|петербург|^москва|^\d{4}\s*г?\.?$|^м\.,", re.I)
    pos, out, found, prev_by, changed, k = 0, [], False, False, False, 0
    while True:
        mp = re.match(r"\s*<p>(.*?)</p>", head[pos:], re.S)
        if not mp:
            break
        t = plain(mp.group(1))
        nxt = re.match(r"\s*<p>(.*?)</p>", head[pos + mp.end():], re.S)
        nt = plain(nxt.group(1)) if nxt else ""
        bold = bool(re.fullmatch(r"\s*<strong>.*</strong>\s*", mp.group(1), re.S))
        first_is_title = k == 0 and len(t) <= 300 and (bold or (len(t) <= 90 and is_byline(nt, False)))
        k += 1
        if found and PUBLISHER.search(t) and len(t) <= 90:
            pass                                          # the publisher's imprint
        elif not found and (is_title(t) or first_is_title):
            out.append('<subtitle data-booktitle="1">%s</subtitle>' % mp.group(1)); found = True; prev_by = True
        elif found and is_title(t):
            pass                                          # the title printed twice
        elif is_byline(t, prev_by):
            out.append('<subtitle data-byline="1">%s</subtitle>' % mp.group(1)); prev_by = True
        else:
            break
        changed = True
        pos += mp.end()
    if not changed:
        mv = re.match(r'\s*<poem data-verse="1">\s*<stanza>\s*<v>(.*?)</v>\s*', head, re.S)
        if mv and is_title(plain(mv.group(1))):
            rep = '\n<subtitle data-booktitle="1">%s</subtitle>\n<poem data-verse="1">\n<stanza>\n' % mv.group(1)
            return body[:m.end()] + rep + head[mv.end():] + body[m.end() + 6000:], True
        return body, False
    return body[:m.end()] + "\n" + "\n".join(out) + head[pos:] + body[m.end() + 6000:], True


def fix_book(path, slug, ops, front_cfg, dry=False, titles=()):
    raw = io.open(path, encoding="utf-8").read()
    m = re.search(r"<body>(.*?)</body>", raw, re.S)
    body = m.group(1)
    notes = []
    if "restanza" in ops:
        body, nr = restanza(body)
        if nr:
            notes.append("%d poem(s) re-stanzaed" % nr)
    if "title" in ops:
        bt = re.search(r"<book-title>(.*?)</book-title>", raw, re.S)
        body, did = mark_title(body, list(titles) + ([plain(bt.group(1))] if bt else []))
        if did:
            notes.append("book title set as title")
    if "wiki" in ops:
        nb = re.sub(r"\{\{[^{}|<>]*\|", "", body)
        nb = re.sub(r"\}\}", "", nb)
        nb = re.sub(r"&lt;/?poem&gt;", "", nb)
        nb = re.sub(r"<p>\s*\|", "<p>", nb)
        if nb != body:
            notes.append("wiki markup removed"); body = nb
    leaves = leaf_sections(body)
    front = front_cfg.get(slug)
    first_leaf = leaves[0] if leaves else None
    new = body
    for idx, (s0, s1, i0, i1) in sorted(enumerate(leaves), key=lambda x: -x[1][0]):
        inner = new[i0:i1]
        t = re.match(r"\s*(<title>.*?</title>)", inner, re.S)
        title = t.group(1) if t else ""
        rest = inner[t.end():] if t else inner
        blocks = BLOCK.findall(rest)
        ttl = plain(title)
        changed = False
        if "front" in ops and front is not None and idx == 0:
            if front == "section":
                new = new[:s0] + new[s1:]
                notes.append("dropped title-page section «%s»" % ttl[:30]); continue
            drop = set(front)
            pi, keep = 0, []
            for b in blocks:
                if is_p(b) or b.startswith("<subtitle>"):
                    if pi in drop:
                        pi += 1; continue
                    pi += 1
                keep.append(b)
            notes.append("dropped %d opening line(s)" % (len(blocks) - len(keep)))
            blocks, changed = keep, True
        if "parts" in ops and len(blocks) <= 2 and PART.match(ttl.strip(" .")) and sum(len(plain(b)) for b in blocks) < 200:
            new = new[:s0] + new[s1:]
            notes.append("dropped empty part «%s»" % ttl[:30]); continue
        if "dupe" in ops and blocks and is_p(blocks[0]) and ttl and plain(blocks[0]).strip(" .").lower() == ttl.strip(" .").lower():
            blocks = blocks[1:]; changed = True; notes.append("dropped repeated title «%s»" % ttl[:30])
        if "split" in ops and re.match(r"^(глава\s+|[ivxlc]+\.)", ttl, re.I):
            heads = [k for k, b in enumerate(blocks) if k > 0 and is_p(b) and len(plain(b)) <= 90 and HEAD.match(plain(b))]
            if heads:
                parts, prev = [], 0
                for k in heads + [len(blocks)]:
                    parts.append(blocks[prev:k]); prev = k
                secs = [(title, parts[0])] + [("<title><p>%s</p></title>" % plain(p[0]), p[1:]) for p in parts[1:]]
                if "verse" in ops:
                    secs = [(tt, wrap_verse(bb)[0]) for tt, bb in secs]
                rep = "</section>\n<section>".join("\n%s\n%s\n" % (tt, "\n".join(bb)) for tt, bb in secs)
                new = new[:i0] + rep + new[i1:]
                notes.append("split «%s» at %d heading(s)" % (ttl[:30], len(heads)))
                continue
        if "verse" in ops:
            blocks2, nv = wrap_verse(blocks)
            if nv:
                blocks, changed = blocks2, True
                notes.append("%d poem(s) in «%s»" % (nv, ttl[:30]))
        if "dates" in ops:
            # A poem's date («1906», «20.VIII.13») under it, or closing the
            # section, is a byline; a lone «2» or «IV» over a poem is its
            # part number. Both stay paragraphs (a <subtitle> counts as one),
            # so indices hold.
            nd = 0
            for k, b in enumerate(blocks):
                if not is_p(b):
                    continue
                x = plain(b)
                inner_b = re.sub(r"^<p>|</p>$", "", b)
                prev_poem = k > 0 and blocks[k - 1].startswith("<poem")
                if len(x) <= 40 and DATE.match(x) and (prev_poem or k == len(blocks) - 1):
                    blocks[k] = '<subtitle data-byline="1">%s</subtitle>' % inner_b; nd += 1
                elif re.match(r"^(?:\d{1,2}|[IVXLC]{1,6})\.?$", x) and k + 1 < len(blocks) and blocks[k + 1].startswith("<poem"):
                    blocks[k] = "<subtitle>%s</subtitle>" % inner_b; nd += 1
            if nd:
                changed = True; notes.append("%d date/number line(s) in «%s»" % (nd, ttl[:30]))
        if "heads" in ops:
            nh = 0
            for k in range(1, len(blocks)):
                if blocks[k].startswith('<poem data-verse') and poem_heading(blocks[k - 1]) and not (k >= 2 and blocks[k - 2].startswith("<subtitle")):
                    blocks[k - 1] = "<subtitle>%s</subtitle>" % re.sub(r"^<p>|</p>$", "", blocks[k - 1]); nh += 1
            if nh:
                changed = True; notes.append("%d poem title(s) in «%s»" % (nh, ttl[:30]))
        if changed:
            new = new[:i0] + "\n" + title + "\n" + "\n".join(blocks) + "\n" + new[i1:]
    if new == m.group(1) or dry:
        return notes
    os.makedirs(ORIG, exist_ok=True)
    keep = os.path.join(ORIG, os.path.basename(path))
    if not os.path.exists(keep):
        shutil.copy(path, keep)
    io.open(path, "w", encoding="utf-8", newline="\n").write(raw[:m.start(1)] + new + raw[m.end(1):])
    return notes


def main():
    a = sys.argv[1:]
    idx = json.load(io.open("private/books/index.json", encoding="utf-8"))
    if "--only" in a:
        want = set(x for x in a[a.index("--only") + 1:] if not x.startswith("--"))
        books = [b for b in idx if b.get("slug") in want]
    elif "--category" in a:
        cat = a[a.index("--category") + 1]
        books = [b for b in idx if b.get("category") == cat]
    else:
        books = [b for b in idx if str(b.get("filename", "")).endswith(".fb2")]
    ops = {"wiki", "verse", "title"} if "--index-safe" in a else {"wiki", "front", "dupe", "parts", "split", "verse", "title"}
    if "--ops" in a:
        ops = set(a[a.index("--ops") + 1].split(","))
    front_cfg = json.load(io.open(FRONT, encoding="utf-8")) if os.path.exists(FRONT) else {}
    hit = 0
    for b in books:
        p = "public/books/" + b["filename"]
        if not os.path.exists(p):
            continue
        try:
            POETRY[0] = b.get("category") == "Poetry"
            if b.get("category") in ("Religious Texts", "Soviet Textbooks", "Plays", "Theatrical Performances") and ops & {"verse", "heads", "dates"}:
                continue                                  # the Bible's own layout; textbooks' tables; plays have their own speaker layout
            notes = fix_book(p, b.get("slug"), ops, front_cfg, "--dry" in a, (b.get("title", ""),))
        except Exception as e:
            print("!! %-28s %s" % (b.get("slug"), e)); continue
        if notes:
            hit += 1
            print("%-30s %s" % (b.get("slug"), "; ".join(notes[:6]) + (" …+%d" % (len(notes) - 6) if len(notes) > 6 else "")))
    print("\n%d book(s) %s" % (hit, "would change" if "--dry" in a else "changed"))


if __name__ == "__main__":
    main()
