"""Lesson blocks taken word for word from the Wikibooks Russian textbook
(en.wikibooks.org/wiki/Russian, CC BY-SA 4.0), from the copies in
private/wikibooks-russian/ that tools/fetch_wikibooks_russian.py saved.

    wiki("Genitive_case", "Usage/Counting")  → [blocks]
A path names a heading and, after "/", a heading inside it; "" is the text
before the first heading."""
import io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "private", "wikibooks-russian")


def _inline(t):
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<small>(.*?)</small>", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+ ([^\]]+)\]", r"\1", t)
    t = re.sub(r"\{\{[^}]*\}\}", "", t)
    t = re.sub(r"'''''(.+?)'''''", r"**\1**", t)
    t = re.sub(r"'''(.+?)'''", r"**\1**", t)
    t = re.sub(r"''(.+?)''", r"*\1*", t)
    return re.sub(r"\s+", " ", t).strip()


def _plain(t):
    return _inline(t).replace("**", "").replace("*", "")


def _sections(text):
    """[(level, title, body)] in order."""
    out, cur, lvl, buf = [], "", 0, []
    for line in text.split("\n"):
        m = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
        if m:
            out.append((lvl, cur, "\n".join(buf))); lvl, cur, buf = len(m.group(1)), m.group(2), []
        else:
            buf.append(line)
    out.append((lvl, cur, "\n".join(buf)))
    return out


def _table(lines):
    rows, row = [], []
    for l in lines:
        l = l.strip()
        if l.startswith("{|") or l.startswith("|}") or l.startswith("|+"):
            continue
        if l.startswith("|-"):
            if row: rows.append(row)
            row = []
            continue
        cells = re.split(r"\s*(?:\|\||!!)\s*", l[1:]) if l[:1] in "|!" else [l]
        for c in cells:
            if "|" in c and not c.startswith("["):
                c = c.split("|", 1)[1] if re.match(r"^\s*(class|style|colspan|rowspan|align)=", c) else c
            row.append(_plain(c))
    if row: rows.append(row)
    rows = [r for r in rows if any(x for x in r)]
    if not rows:
        return None
    w = max(len(r) for r in rows)
    rows = [r + [""] * (w - len(r)) for r in rows]
    return {"t": "table", "head": rows[0], "rows": rows[1:], "rowHeads": True}


def _blocks(body):
    blocks, para, lst, ex = [], [], [], []
    lines = body.split("\n")

    def flush():
        if para:
            blocks.append({"t": "p", "text": _inline(" ".join(para))}); para.clear()
        if lst:
            blocks.append({"t": "list", "items": list(lst)}); lst.clear()
        if ex:
            blocks.append({"t": "ex", "items": [list(x) for x in ex]}); ex.clear()
    i = 0
    while i < len(lines):
        l = lines[i].rstrip()
        if l.startswith("{|"):
            flush(); j = i
            while j < len(lines) and not lines[j].startswith("|}"):
                j += 1
            tb = _table(lines[i:j + 1])
            if tb: blocks.append(tb)
            i = j + 1; continue
        if not l.strip() or l.strip() in ("<br>", "<br/>"):
            flush()
        elif l.startswith(":"):
            if para or lst: 
                b = list(ex); ex.clear(); flush(); ex.extend(b)
            t = l.lstrip(":").strip()
            m = re.match(r"^(.*?)\s+[-–—]\s+(.*)$", t)
            if m:
                a, b = m.group(1), m.group(2)
                ru, en = (b, a) if re.search(r"[А-Яа-яЁё]", b) and not re.search(r"[А-Яа-яЁё]", a) else (a, b)
                ex.append((_plain(ru), _plain(en)))
            else:
                ex.append((_plain(t), ""))
        elif l.startswith("*") or l.startswith("#"):
            if para or ex:
                b = list(lst); lst.clear(); flush(); lst.extend(b)
            lst.append(_inline(l.lstrip("*#").strip()))
        else:
            if lst or ex:
                flush()
            para.append(l.strip())
        i += 1
    flush()
    return [b for b in blocks if not (b["t"] == "p" and not b["text"])]


def wiki(page, path=""):
    text = io.open(os.path.join(DIR, "Russian_Grammar_" + page + ".wiki"), encoding="utf-8").read()
    secs = _sections(text)
    want = [p.strip().lower() for p in path.split("/")] if path else []
    out, stack = [], []
    for lvl, title, body in secs:
        while stack and stack[-1][0] >= lvl:
            stack.pop()
        if title:
            stack.append((lvl, title.lower()))
        names = [t for _, t in stack]
        if (not want and not title) or (want and names[:len(want)] == want):
            if title and want and len(names) > len(want):
                out.append({"t": "h", "text": _plain(title)})
            out += _blocks(body)
    return out
