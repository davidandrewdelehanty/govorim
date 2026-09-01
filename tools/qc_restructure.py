#!/usr/bin/env python3
"""Section-level FB2 surgery: drop/retitle/insert on top-level sections."""
import io, re, sys

def load(path):
    raw = io.open(path, 'rb').read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"\']([\w-]+)", raw[:200])
    encs = ([m.group(1).decode()] if m else []) + ["utf-8", "cp1251"]
    for enc in encs:
        try: return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError): continue
    raise RuntimeError(path)

def save(path, text, enc):
    io.open(path, 'w', encoding=enc, errors='xmlcharrefreplace').write(text)

def top_sections(text):
    """Spans of top-level <section>..</section> inside the first unnamed body."""
    mb = re.search(r'<body(?![^>]*name=)[^>]*>', text)
    start = mb.end()
    end = text.find('</body>', start)
    spans = []
    i = start
    while True:
        s = text.find('<section', i)
        if s < 0 or s > end: break
        depth = 0
        for m in re.finditer(r'<section\b|</section>', text[s:end+20]):
            depth += 1 if m.group(0).startswith('<section') else -1
            if depth == 0:
                e = s + m.end()
                spans.append((s, e))
                i = e
                break
        else: break
    return spans

def title_of(sec_text):
    m = re.search(r'<title>(.*?)</title>', sec_text, re.S)
    if not m: return ''
    return re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', m.group(1))).strip()

def rewrite(path, fn):
    """fn(list of (title, sec_text)) -> new list of sec_text (or None to drop)."""
    text, enc = load(path)
    spans = top_sections(text)
    secs = [text[a:b] for a, b in spans]
    titles = [title_of(s) for s in secs]
    new = fn(list(zip(titles, secs)))
    out = text[:spans[0][0]]
    prev_end = spans[0][0]
    ni = 0
    body = []
    for k, (a, b) in enumerate(spans):
        pass
    # rebuild: everything before first span + joined new sections + everything after last span
    tail = text[spans[-1][1]:]
    save(path, text[:spans[0][0]] + "\n".join(s for s in new if s is not None) + tail, enc)
    return len([s for s in new if s is not None])

def set_title(sec_text, title):
    if re.search(r'<title>.*?</title>', sec_text, re.S):
        return re.sub(r'<title>.*?</title>', '<title><p>%s</p></title>' % title, sec_text, count=1, flags=re.S)
    return re.sub(r'(<section[^>]*>)', r'\1<title><p>%s</p></title>' % title, sec_text, count=1)

def drop_first_para(sec_text):
    return re.sub(r'<p\b[^>]*>.*?</p>', '', sec_text, count=1, flags=re.S)
