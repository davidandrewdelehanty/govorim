#!/usr/bin/env python3
"""Give the Translations FB2s real chapters.

Wikisource often holds a whole novel on one page (or one page per part) with
the chapter headings as ordinary lines — "ГЛАВА I", or "ГЛАВА" then "I." — so
the FB2 comes out as one or two enormous sections and the reader shows a
200-page "chapter". This cuts each such section at its headings. A part keeps
its own title and the chapters nest under it; a section that only repeats the
book's title is unwrapped so its chapters stand at the top level.

It also drops what is not the book:
  * a little "Переводы / Ссылки" list that a versions page put in front
  * the pre-reform copy where a page carries the same edition twice
    (dореформенная + современная)

    python3 tools/translations_fix_fb2.py            # every Translations FB2
    python3 tools/translations_fix_fb2.py --only cooper-deerslayer
    python3 tools/translations_fix_fb2.py --dry      # report only

The original is kept in tools/translations/fb2-orig/ (first time only).
"""
import csv, io, os, re, shutil, sys

DIR = "tools/translations"
ORIG = os.path.join(DIR, "fb2-orig")
NOVEL = "public/books/novel"

HEAD = re.compile(r"^(?:ГЛАВА|Глава)\s+(?:[IVXLCІ]+|\d+|[А-ЯЁа-яё-]+)\.?(?:\s*[.:—–-]\s*.{0,80}|\s+[А-ЯЁ].{0,80})?$")
LONE = re.compile(r"^(?:ГЛАВА|Глава)\.?$")
ROMAN = re.compile(r"^[IVXLCІ]{1,7}\.?$")
P_RE = re.compile(r"<p>.*?</p>|<empty-line/>|<poem>.*?</poem>|<cite>.*?</cite>|<subtitle>.*?</subtitle>|<epigraph>.*?</epigraph>|<image[^>]*/>|<table>.*?</table>", re.S)


def plain(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x)).strip()


def sections(body):
    """(start, end, inner_start, inner_end, depth) of every <section> in body."""
    out, stack = [], []
    for m in re.finditer(r"<section>|</section>", body):
        if m.group() == "<section>":
            stack.append(m)
        else:
            o = stack.pop()
            out.append((o.start(), m.end(), o.end(), m.start(), len(stack)))
    return out


def split_leaf(inner, book_title):
    """Return the new XML for a leaf section's inner text, or None."""
    t = re.match(r"\s*(<title>.*?</title>)", inner, re.S)
    title = t.group(1) if t else ""
    rest = inner[t.end():] if t else inner
    blocks = P_RE.findall(rest)
    if not blocks:
        return None
    heads = []
    i = 0
    texts = [plain(b) if b.startswith("<p>") else "" for b in blocks]
    romans = sum(1 for x in texts if ROMAN.match(x))
    while i < len(blocks):
        x = texts[i]
        if len(x) <= 90 and HEAD.match(x):
            heads.append((i, i + 1, x))
        elif LONE.match(x) and i + 1 < len(blocks) and (ROMAN.match(texts[i + 1]) or re.match(r"^\d+\.?$", texts[i + 1])):
            heads.append((i, i + 2, "Глава " + texts[i + 1].rstrip(".")))
            i += 1
        elif romans >= 5 and ROMAN.match(x):
            heads.append((i, i + 1, x.rstrip(".")))
        i += 1
    if len(heads) < 3:
        return None
    parts = []
    lead = blocks[:heads[0][0]]
    lead_txt = [plain(b) for b in lead if plain(b)]
    keep_lead = lead and not (len(lead_txt) <= 6 and all(len(x) < 80 for x in lead_txt))
    if keep_lead:
        parts.append("<section>\n" + "\n".join(lead) + "\n</section>")
    for k, (a, b, h) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(blocks)
        body = blocks[b:end]
        if not body:
            continue
        h = re.sub(r"\s+", " ", h).strip()
        h = h[0] + h[1:].lower() if h.isupper() else h
        h = re.sub(r"\b(Глава) ([ivxlc]+)\b", lambda m: m.group(1) + " " + m.group(2).upper(), h)
        parts.append("<section>\n<title><p>%s</p></title>\n%s\n</section>" % (h, "\n".join(body)))
    ttl = plain(title)
    unwrap = not ttl or ttl.lower().strip(" .") == (book_title or "").lower().strip(" .") or re.search(r"издание|редакци", ttl, re.I)
    return "\n".join(parts) if unwrap else (title + "\n" + "\n".join(parts))


def fix(path, dry=False):
    raw = io.open(path, encoding="utf-8").read()
    bt = re.search(r"<book-title>(.*?)</book-title>", raw, re.S)
    book_title = plain(bt.group(1)) if bt else ""
    m = re.search(r"<body>(.*?)</body>", raw, re.S)
    body = m.group(1)
    secs = sections(body)
    notes = []
    leaves = [s for s in secs if "<section>" not in body[s[2]:s[3]]]
    drop = set()
    titles = [plain((re.match(r"\s*<title>(.*?)</title>", body[s[2]:s[3]], re.S) or [None, ""])[1]) for s in leaves]
    for s, ttl in zip(leaves, titles):
        inner = body[s[2]:s[3]]
        txt = plain(inner)
        nparas = len(re.findall(r"<p>", inner))
        if nparas <= 12 and re.search(r"^\s*(Переводы|Редакции)\b", txt[len(ttl):].strip()):
            drop.add(s); notes.append("drop versions list «%s»" % ttl[:30])
        if re.search(r"дореформ", ttl, re.I) and any(re.search(r"современ", t2, re.I) for t2 in titles):
            drop.add(s); notes.append("drop pre-reform duplicate «%s»" % ttl[:40])
    # rebuild body back to front so offsets stay valid
    new = body
    for s in sorted(leaves, key=lambda x: -x[0]):
        if s in drop:
            new = new[:s[0]] + new[s[1]:]
            continue
        inner = new[s[2]:s[3]]
        rep = split_leaf(inner, book_title)
        if rep is None:
            continue
        n = rep.count("<section>")
        notes.append("split «%s» into %d" % ((titles[leaves.index(s)] or "-")[:30], n))
        if rep.startswith("<section>") and not rep.lstrip().startswith("<title>"):
            new = new[:s[0]] + rep + new[s[1]:]        # unwrapped
        else:
            new = new[:s[2]] + rep + new[s[3]:]
    if new == body:
        return []
    if not dry:
        os.makedirs(ORIG, exist_ok=True)
        keep = os.path.join(ORIG, os.path.basename(path))
        if not os.path.exists(keep):
            shutil.copy(path, keep)
        io.open(path, "w", encoding="utf-8", newline="\n").write(raw[:m.start(1)] + new + raw[m.end(1):])
    return notes


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1:] if "--only" in a else None
    with io.open(os.path.join(DIR, "list.tsv"), encoding="utf-8") as f:
        slugs = [r[0] for r in csv.reader(f, delimiter="\t") if r and not r[0].startswith("#")]
    for s in slugs:
        if only and s not in only:
            continue
        p = os.path.join(NOVEL, s + ".fb2")
        if not os.path.exists(p):
            continue
        notes = fix(p, "--dry" in a)
        if notes:
            print("%-28s %s" % (s, "; ".join(notes)))


if __name__ == "__main__":
    main()
