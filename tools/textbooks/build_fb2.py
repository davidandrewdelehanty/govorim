"""book.json -> FB2 with <image> references, plus cover.  usage: build_fb2.py <slug>"""
import sys, os, re, json, shutil, html
sys.path.insert(0, os.path.dirname(__file__))
from books import BOOKS, META
ROOT = "/tmp/claude-0/tb"
ROMAN = {"I":1,"V":5,"X":10,"L":50,"C":100}
def roman(r):
    n = 0
    for i, c in enumerate(r):
        v = ROMAN[c]; n += -v if i + 1 < len(r) and ROMAN[r[i + 1]] > v else v
    return n
def sentence(t):
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) > 0.7 * len(letters):
        t = t.lower()
        t = re.sub(r"^(\W*)(\w)", lambda m: m.group(1) + m.group(2).upper(), t)
        t = re.sub(r"([.!?]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), t)
    return t
def sub_text(t):
    # roman-numbered subheads would read as chapter markers to the reader's
    # FB2 parser; number them in arabic instead.
    t = re.sub(r"^([IVXLC]+)\.\s", lambda m: f"{roman(m.group(1))}. ", t.strip())
    return sentence(t)
def esc(t): return html.escape(t, quote=True)

def build(slug):
    cfg, meta = BOOKS.get(slug, {}), META[slug]
    out = f"{ROOT}/out/{slug}"
    data = json.load(open(f"{out}/book.json"))
    blocks = [b for b in data["blocks"]]
    for i, j in meta.get("drop_blocks", []):
        for k in range(i, j): blocks[k] = None
    blocks = [b for b in blocks if b]
    if meta.get("drop_text"):
        blocks = [b for b in blocks if not (b[0] != "fig" and b[1].strip() in meta["drop_text"])]
    if meta.get("h1_map"):
        hm = list(meta["h1_map"]); nb = []
        for b in blocks:
            if b[0] == "h1":
                if not hm: continue
                t_ = hm.pop(0)
                if t_ is None: continue
                for x in (t_ if isinstance(t_, list) else [t_]): nb.append(["h1", x, b[2]])
                continue
            nb.append(b)
        blocks = nb
    # chapters the book does not mark: (first page, title)
    if meta.get("chapters"):
        pend = list(meta["chapters"]); nb = []
        for b in blocks:
            pg = b[2]
            while pend and pend[0][0] <= pg:
                nb.append(["h1", pend.pop(0)[1], pg])
            nb.append(b)
        blocks = nb
    fix = meta.get("fix", [])
    secs = []   # [title, [items]]
    cur = None
    i = 0
    while i < len(blocks):
        k, o, pg = blocks[i]
        if k == "h1" and re.match(r"^(ЧАСТЬ|Часть|Отдел)\s", o):
            ptitle = sentence(o).rstrip(".")
            if i + 1 < len(blocks) and blocks[i + 1][0] in ("h1", "h2") and not re.match(r"^(Глава|ЧАСТЬ|Часть|Отдел)", blocks[i + 1][1]):
                ptitle += ": " + sentence(blocks[i + 1][1]).rstrip(".")
                i += 1
            part = [ptitle, []]; secs.append(("part", part)); cur = None; i += 1; continue
        if k == "h1":
            title = meta["h1fmt"](o) if meta.get("h1fmt") else sentence(o)
            # a chapter mark and its name set as two big lines
            while i + 1 < len(blocks) and blocks[i + 1][0] == "h1" and not re.match(r"^(Глава|ЧАСТЬ|Часть|Г л а в а)", blocks[i + 1][1]) \
                    and re.match(r"^(Глава|ЧАСТЬ|Часть|Введение|[IVXLC\d]+\.?$)", o):
                nxt = sentence(blocks[i + 1][1])
                title = title.rstrip(".") + ". " + nxt.rstrip(".")
                o = nxt; i += 1
            # a short heading right under the chapter mark is the chapter's name
            if i + 1 < len(blocks) and blocks[i + 1][0] == "h2" and len(blocks[i + 1][1]) < 110 and meta.get("join_h2", True):
                title = title.rstrip(".") + ". " + sub_text(blocks[i + 1][1]).rstrip(".")
                i += 1
            cur = [title, []]
            if meta.get("intros", {}).get(title): cur[1].append(("arg", meta["intros"][title]))
            if secs and secs[-1][0] == "part": secs[-1][1][1].append(cur)
            else: secs.append(cur)
            i += 1; continue
        if cur is None:
            if secs and secs[-1][0] == "part":
                cur = ["Вступление", []]; secs[-1][1][1].append(cur)
            else:
                cur = [meta.get("front_title", "Предисловие"), []]; secs.append(cur)
        if k == "fig":
            cur[1].append(("fig", o))
            if meta.get("page_text", {}).get(pg):
                for line in meta["page_text"][pg]: cur[1].append(("p", line))
        elif k == "h2": cur[1].append(("sub", sub_text(o)))
        elif k == "arg": cur[1].append(("arg", o))
        else: cur[1].append(("p", o))
        i += 1
    def flat(ss):
        for s_ in ss:
            if s_[0] == "part":
                for c in s_[1][1]: yield c
            else: yield s_
    for a, b in fix:
        for s_ in flat(secs):
            s_[0] = s_[0].replace(a, b)
            s_[1] = [(k, (v.replace(a, b) if isinstance(v, str) else v)) for k, v in s_[1]]
    imgdir = f"{out}/assets"
    if os.path.exists(imgdir): shutil.rmtree(imgdir)
    os.makedirs(imgdir)
    used = []
    body = []
    def emit(title, items):
        if not any(k in ("p", "arg", "sub", "fig") for k, _ in items): return
        body.append("<section>")
        body.append(f"<title><p>{esc(title)}</p></title>")
        # runs of short lines are verse (or a primer's line-by-line reading):
        # set them tight, as the book does
        short = lambda kv: kv[0] == "p" and len(kv[1]) <= meta.get("verse_len", 0) and not re.search(r"[:]$", kv[1])
        runs = [False] * len(items)
        j = 0
        while j < len(items):
            if short(items[j]):
                e = j
                while e < len(items) and short(items[e]): e += 1
                if e - j >= meta.get("verse_min", 3):
                    for q in range(j, e): runs[q] = True
                j = e
            else: j += 1
        inpoem = False
        for idx, (k, v) in enumerate(items):
            if runs[idx] and not inpoem:
                body.append('<poem data-tight="1"><stanza>'); inpoem = True
            if not runs[idx] and inpoem:
                body.append("</stanza></poem>"); inpoem = False
            if inpoem: body.append(f"<v>{esc(v)}</v>"); continue
            if k == "p": body.append(f"<p>{esc(v)}</p>")
            elif k == "arg": body.append(f"<p><emphasis>{esc(v)}</emphasis></p>")
            elif k == "sub": body.append(f"<subtitle>{esc(v)}</subtitle>")
            elif k == "fig":
                shutil.copy(f"{out}/img/{v['name']}", f"{imgdir}/{v['name']}")
                used.append(v["name"])
                cap = f' title="{esc(v["cap"])}"' if v.get("cap") else ""
                body.append(f'<image l:href="textbooks/{slug}/{v["name"]}"{cap} width="{v["w"]}" height="{v["h"]}"/>')
        if inpoem: body.append("</stanza></poem>")
        body.append("</section>")
    for sec in secs:
        if sec[0] == "part":
            ptitle, chs = sec[1]
            body.append("<section>"); body.append(f"<title><p>{esc(ptitle)}</p></title>")
            for t_, it_ in chs: emit(t_, it_)
            body.append("</section>")
        else:
            emit(sec[0], sec[1])
    a = meta["author"]
    fb2 = f'''<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
<description><title-info><genre>sci_textbook</genre><author><first-name>{esc(a[0])}</first-name><last-name>{esc(a[1])}</last-name></author>
<book-title>{esc(meta["title"])}</book-title><lang>ru</lang></title-info>
<document-info><program-used>govorim tools/textbooks</program-used><src-ocr>{esc(meta.get("src", ""))}</src-ocr></document-info>
<publish-info><year>{meta.get("year", "")}</year></publish-info></description>
<body>
''' + "\n".join(body) + "\n</body>\n</FictionBook>\n"
    open(f"{out}/{slug}.fb2", "w", encoding="utf-8").write(fb2)
    # cover
    if meta.get("cover"):
        import cv2, numpy as np
        pn, box = meta["cover"]
        img = cv2.imread(f"{ROOT}/pages/{slug}/p{pn:04d}.jpg") if pn else None
        if img is None and BOOKS.get(slug, {}).get("pdf"):
            import pymupdf
            d = pymupdf.open(BOOKS[slug]["pdf"]); d[pn - 1].get_pixmap(dpi=200).save(f"{ROOT}/pages/{slug}/p{pn:04d}.jpg")
            img = cv2.imread(f"{ROOT}/pages/{slug}/p{pn:04d}.jpg")
        H, W = img.shape[:2]
        x0, y0, x1, y1 = box
        c = img[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
        tw = 480
        c = cv2.resize(c, (tw, int(c.shape[0] * tw / c.shape[1])), interpolation=cv2.INTER_AREA)
        cv2.imwrite(f"{imgdir}/cover.webp", c, [cv2.IMWRITE_WEBP_QUALITY, 78])
    words = len(re.findall(r"[А-Яа-яЁёѣіѳѵ]+", re.sub(r"<[^>]+>", " ", "\n".join(body))))
    nsec = sum(1 for b in body if b == "<section>")
    toc = [re.sub(r"<[^>]+>", "", b) for b in body if b.startswith("<title>")]
    open(f"{out}/toc.txt", "w").write("\n".join(toc))
    sz = sum(os.path.getsize(f"{imgdir}/{f}") for f in os.listdir(imgdir))
    print(f"{slug}: {nsec} sections, {words} words, {len(used)} figures, assets {sz/1e6:.1f} MB")
    json.dump({"words": words}, open(f"{out}/stats.json", "w"))

if __name__ == "__main__":
    for s in sys.argv[1:]: build(s)
