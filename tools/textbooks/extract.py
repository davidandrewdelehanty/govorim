"""Scanned textbook -> paragraphs, headings and illustration crops.

usage: extract.py <slug>   (config in books.py)
writes /tmp/claude-0/tb/out/<slug>/book.json  and  img/fNNN.jpg
"""
import sys, os, re, json, statistics, collections
import pymupdf, cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from books import BOOKS

ROOT = "/tmp/claude-0/tb"
DPI = 200
CYR = re.compile(r"[А-Яа-яЁёѢѣІіѲѳѴѵ]")
PARTICLES = {"нибудь", "либо", "то", "ка", "таки", "де", "с"}

# ---------------------------------------------------------------- dictionary
WF = {}
def load_wf():
    p = "/mnt/user-data/uploads/govorim-app/_to_delete/wordfreq.tsv"
    with open(p, encoding="utf-8") as f:
        for ln in f:
            w, n = ln.rstrip("\n").split("\t")
            n = int(n)
            if n < 2: break
            WF[w] = n
ALPHA = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
def edits1(w):
    sp = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    out = set()
    for a, b in sp:
        if b: out.add(a + b[1:])
        if len(b) > 1: out.add(a + b[1] + b[0] + b[2:])
        for c in ALPHA:
            if b: out.add(a + c + b[1:])
            out.add(a + c + b)
    return out
def fix_case(src, dst):
    if src.isupper() and len(src) > 1: return dst.upper()
    if src[:1].isupper(): return dst[:1].upper() + dst[1:]
    return dst
def correct(word, conf):
    m = re.match(r"^([^А-Яа-яЁё]*)([А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*)([^А-Яа-яЁё]*)$", word)
    if not m: return word
    pre, core, post = m.groups()
    lw = core.lower().replace("’", "ъ")
    if lw in WF: return pre + fix_case(core, lw) + post if "’" in core else word
    if len(lw) < 3: return word
    best, bf = None, 0
    for c in edits1(lw):
        f = WF.get(c, 0)
        if f > bf: best, bf = c, f
    need = 5 if conf < 70 else (60 if conf < 90 else 400)
    if best and bf >= need:
        return pre + fix_case(core, best) + post
    return word

import math
def segment(s):
    """Split a run of letters into dictionary words (for letter-spaced emphasis)."""
    n = len(s); best = [(-1e18, -1)] * (n + 1); best[0] = (0.0, -1)
    low = s.lower()
    for i in range(1, n + 1):
        for j in range(max(0, i - 24), i):
            w = low[j:i]
            f = WF.get(w, 0)
            if f: sc = math.log(f) - 19.0
            else: sc = -30.0 - 3.0 * len(w)
            v = best[j][0] + sc
            if v > best[i][0]: best[i] = (v, j)
    out = []; i = n
    while i > 0:
        j = best[i][1]; out.append(s[j:i]); i = j
    return " ".join(reversed(out))
SPACED = re.compile(r"(?<![А-Яа-яЁё])((?:[А-Яа-яЁё][,.;:!?»]? ){2,}[А-Яа-яЁё])(?![А-Яа-яЁё])")
def desperse(t):
    if not WF: return t
    def fix(m):
        raw = m.group(1)
        toks = raw.split(" ")
        core = "".join(re.sub(r"[,.;:!?»]", "", x) for x in toks)
        if len(core) < 3: return raw
        if len(core) == 3 and WF.get(core.lower(), 0) < 1000: return raw
        seg = segment(core)
        # re-attach punctuation that followed a letter
        punct = {}
        pos = 0
        for x in toks:
            pos += len(re.sub(r"[,.;:!?»]", "", x))
            p2 = re.sub(r"[А-Яа-яЁё]", "", x)
            if p2: punct[pos] = p2
        out, pos = [], 0
        for ch in seg:
            out.append(ch)
            if ch != " ":
                pos += 1
                if pos in punct: out.append(punct[pos])
        return "".join(out)
    return SPACED.sub(fix, t)

def ocr_clean(t):
    t = re.sub(r"(?<!\S)[пн](?!\S)", "и", t)
    t = t.replace("©", "с").replace("@", "а").replace("®", "к")
    t = re.sub(r"[<‹]+", "«", t); t = re.sub(r"[>›]+", "»", t)
    t = re.sub(r"^[+°‘'`‚\"*~=_|\\/ ]+(?=[«А-ЯЁа-яё(\d—])", "", t)
    t = re.sub(r"\s+[|\\]\s+", " ", t)
    return t

# ---------------------------------------------------------------- page model
class Line:
    def __init__(s, words, blk, par):
        s.words = words  # [text, conf, x0,y0,x1,y1]
        s.blk, s.par = blk, par
        s.x0 = min(w[2] for w in words); s.y0 = min(w[3] for w in words)
        s.x1 = max(w[4] for w in words); s.y1 = max(w[5] for w in words)
        hs = sorted(w[5] - w[3] for w in words)
        s.h = hs[len(hs) // 2]
        s.size = None; s.bold = False
    @property
    def text(s): return " ".join(w[0] for w in s.words)
    @property
    def conf(s): return sum(w[1] for w in s.words) / len(s.words)

def ocr_lines(tsv, scale):
    rows = collections.OrderedDict()
    with open(tsv, encoding="utf-8") as f:
        next(f)
        for ln in f:
            c = ln.rstrip("\n").split("\t")
            if len(c) < 12 or c[0] != "5": continue
            t = c[11].strip()
            if not t: continue
            x, y, w, h = (int(v) * scale for v in c[6:10])
            key = (int(c[2]), int(c[3]), int(c[4]))
            rows.setdefault(key, []).append([t, float(c[10]), x, y, x + w, y + h])
    return [Line(ws, k[0], k[0] * 1000 + k[1]) for k, ws in rows.items()]

def layer_lines(page, fixenc=None):
    k = DPI / 72.0
    out = []
    d = page.get_text("dict")
    for bi, b in enumerate(d["blocks"]):
        if b.get("type") != 0: continue
        for l in b["lines"]:
            spans = [s for s in l["spans"] if s["text"].strip()]
            if not spans: continue
            txt = "".join(s["text"] for s in l["spans"])
            if fixenc: txt = fixenc(txt)
            x0, y0, x1, y1 = (v * k for v in l["bbox"])
            ws = []
            # split into words with proportional x positions
            toks = [m for m in re.finditer(r"\S+", txt)]
            n = max(len(txt), 1)
            for m in toks:
                ws.append([m.group(0), 95.0, x0 + (x1 - x0) * m.start() / n, y0, x0 + (x1 - x0) * m.end() / n, y1])
            if not ws: continue
            L = Line(ws, bi, bi)
            L.size = max(s["size"] for s in spans)
            L.bold = all((s["flags"] & 16) or "Bold" in s["font"] for s in spans)
            out.append(L)
    return out

# ---------------------------------------------------------------- figures
def find_figures(img, lines, cfg):
    H, W = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    ink = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 51, 18)
    # scan borders and binding shadow: blank a margin
    m = int(min(H, W) * cfg.get("margin", 0.035))
    ink[:m, :] = 0; ink[-m:, :] = 0; ink[:, :m] = 0; ink[:, -m:] = 0
    for L in lines:
        for w in L.words:
            if w[1] >= 40 or cfg.get("layer"):
                pad = int(max(3, (w[5] - w[3]) * 0.25))
                ink[max(0, int(w[3]) - pad):int(w[5]) + pad, max(0, int(w[2]) - pad):int(w[4]) + pad] = 0
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    k = max(9, int(W * 0.018))
    blob = cv2.dilate(ink, np.ones((k, k), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(blob)
    figs = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if w < W * cfg.get("fig_min_w", 0.12) or h < H * cfg.get("fig_min_h", 0.06): continue
        if w * h < W * H * cfg.get("fig_min_area", 0.025): continue
        dens = ink[y:y + h, x:x + w].mean() / 255
        if dens < 0.015: continue            # mostly blank — speckle
        # lines / rules: very thin
        if min(w, h) < 0.03 * min(W, H): continue
        figs.append([x, y, x + w, y + h])
    # grow each box to the whole of the drawing it caught: masking the words
    # also masked the labels and table cells at a figure's edge.
    full = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 51, 18)
    full[:m, :] = 0; full[-m:, :] = 0; full[:, :m] = 0; full[:, -m:] = 0
    full = cv2.dilate(full, np.ones((5, 5), np.uint8))
    n2, _, st2, _ = cv2.connectedComponentsWithStats(full)
    grown = []
    for f in figs:
        x0, y0, x1, y1 = f
        for i in range(1, n2):
            x, y, w, h, a = st2[i]
            ix = max(0, min(x1, x + w) - max(x0, x)); iy = max(0, min(y1, y + h) - max(y0, y))
            if ix * iy > 0.6 * w * h and w * h < W * H * 0.9:
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x + w), max(y1, y + h)
        grown.append([int(x0), int(y0), int(x1), int(y1)])
    figs = grown
    # merge overlapping / near boxes
    merged = True
    while merged:
        merged = False
        for i in range(len(figs)):
            for j in range(i + 1, len(figs)):
                a, b = figs[i], figs[j]
                gap = 0.02 * W
                if a[0] - gap < b[2] and b[0] - gap < a[2] and a[1] - gap < b[3] and b[1] - gap < a[3]:
                    figs[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    figs.pop(j); merged = True; break
            if merged: break
    return figs

def save_crop(img, box, path, maxw=900):
    x0, y0, x1, y1 = box
    H, W = img.shape[:2]
    p = 6
    x0, y0, x1, y1 = max(0, x0 - p), max(0, y0 - p), min(W, x1 + p), min(H, y1 + p)
    c = img[y0:y1, x0:x1]
    hsv = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)
    colorful = (hsv[:, :, 1] > 60).mean() > 0.04
    if not colorful:
        c = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
        # lift the paper to white, keep the ink
        lo, hi = np.percentile(c, 2), np.percentile(c, 92)
        c = np.clip((c.astype(np.float32) - lo) * 255.0 / max(1, hi - lo), 0, 255).astype(np.uint8)
    if c.shape[1] > maxw:
        c = cv2.resize(c, (maxw, int(c.shape[0] * maxw / c.shape[1])), interpolation=cv2.INTER_AREA)
    cv2.imwrite(path, c, [cv2.IMWRITE_WEBP_QUALITY, 72])
    return c.shape[1], c.shape[0]

# ---------------------------------------------------------------- main
def run(slug):
    cfg = BOOKS[slug]
    if not WF: load_wf()
    pdir = f"{ROOT}/pages/{slug}"
    out = f"{ROOT}/out/{slug}"; os.makedirs(out + "/img", exist_ok=True)
    for f in os.listdir(out + "/img"): os.remove(out + "/img/" + f)
    doc = pymupdf.open(cfg["pdf"]) if cfg.get("pdf") else None
    first, last = cfg["pages"] if "pages" in cfg else (1, len(doc))
    skip = set(cfg.get("skip", []))
    fig_pages = cfg.get("fig_pages")          # None = detect everywhere
    nofig = set(cfg.get("nofig", []))
    pages = []
    for pn in range(first, last + 1):
        if pn in skip: continue
        jpg = f"{pdir}/p{pn:04d}.jpg"
        if not os.path.exists(jpg):
            os.makedirs(pdir, exist_ok=True)
            doc[pn - 1].get_pixmap(dpi=DPI).save(jpg, jpg_quality=92)
        img = cv2.imread(jpg)
        if pn in set(cfg.get("plates", [])):
            lines = []
        elif cfg.get("layer"):
            lines = layer_lines(doc[pn - 1], cfg.get("fixenc"))
        else:
            lines = ocr_lines(f"{pdir}/p{pn:04d}.tsv", cfg.get("ocr_scale", DPI / 300.0))
        pages.append((pn, img, lines))
    # body line height
    hs = [L.h for _, _, ls in pages for L in ls if len(L.words) > 4]
    body_h = statistics.median(hs) if hs else 20
    sizes = [L.size for _, _, ls in pages for L in ls if L.size and len(L.words) > 4]
    body_size = statistics.median(sizes) if sizes else None
    # running heads: normalised short top/bottom lines that recur
    def norm(t): return re.sub(r"[\d\W_]+", "", t.lower())
    edge = collections.Counter()
    for _, img, ls in pages:
        H = img.shape[0]
        for L in ls:
            if (L.y1 < H * 0.09 or L.y0 > H * 0.92) and len(L.words) <= 7:
                edge[norm(L.text)] += 1
    blocks = []   # ("p"|"h1"|"h2"|"fig", text/obj, page)
    fign = 0
    plates = set(cfg.get("plates", []))
    for pn, img, ls in pages:
        H, W = img.shape[:2]
        if pn in plates:
            # the page itself is the thing to see: copybook lines, syllable
            # tables, letters drawn large. Crop to the printed area.
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ink = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 51, 18)
            m = int(min(H, W) * 0.04)
            ink[:m, :] = 0; ink[-m:, :] = 0; ink[:, :m] = 0; ink[:, -m:] = 0
            ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            ys, xs = np.where(ink > 0)
            if len(xs) > ink.size * 0.006:
                box = [int(np.percentile(xs, 0.2)), int(np.percentile(ys, 0.2)), int(np.percentile(xs, 99.8)), int(np.percentile(ys, 99.8))]
                pd = int(0.025 * W)
                box = [max(0, box[0] - pd), max(0, box[1] - pd), min(W, box[2] + pd), min(H, box[3] + pd)]
                if cfg.get("plate_inset") is not None:
                    q = cfg["plate_inset"]; box = [int(W * q[0]), int(H * q[1]), int(W * q[2]), int(H * q[3])]
                fign += 1
                name = f"f{fign:03d}.webp"
                w, h = save_crop(img, box, f"{out}/img/{name}", maxw=cfg.get("plate_w", 1000))
                blocks.append(["fig", {"y": 0, "name": name, "cap": "", "w": w, "h": h, "page": pn, "plate": True}, pn])
            continue
        keep = []
        if not cfg.get("two_col"):
            ls = sorted(ls, key=lambda L: (round(L.y0 / (body_h * 0.6)), L.x0))
        for L in ls:
            t = L.text.strip()
            nt = norm(t)
            atedge = (L.y1 < H * 0.09 or L.y0 > H * 0.92)
            if atedge and len(L.words) <= 7 and (not nt or edge[nt] >= 3 or re.fullmatch(r"[\W\d_ivxlcIVXLCоО]*", t)):
                continue
            if (L.y1 < H * 0.16 or L.y0 > H * 0.86) and re.fullmatch(r"[\W\d_]*\d[\W\d_]*", t): continue
            if L.y1 < H * 0.16 and re.fullmatch(r"[—\-=–.,'\s]+\S{1,4}[—\-=–.,'\s]*", t): continue
            if not CYR.search(t) and not re.search(r"\d", t): continue
            if not cfg.get("layer") and L.conf < cfg.get("min_line_conf", 45): continue
            if not cfg.get("layer") and not cfg.get("old"):
                ws3 = [re.sub(r"[^А-Яа-яЁё]", "", w[0]).lower() for w in L.words]
                ws3 = [w for w in ws3 if len(w) >= 3]
                if len(ws3) >= 2 and sum(1 for w in ws3 if w in WF) < 0.5 * len(ws3): continue
                if len(ws3) == 1 and len(L.words) <= 2 and ws3[0] not in WF and L.conf < 75: continue
            if cfg.get("drop_small") and (L.size and body_size and L.size < body_size * 0.82 or
                                          (not L.size and L.h < body_h * 0.72 and L.y0 > H * 0.6)):
                continue     # footnotes
            keep.append(L)
        figs = []
        if pn not in nofig and (fig_pages is None or pn in fig_pages):
            figs = find_figures(img, ls, cfg)
        for box in cfg.get("manual_figs", {}).get(pn, []):
            figs.append([int(v * (W if i % 2 == 0 else H)) for i, v in enumerate(box)])
        # words inside a figure are labels, not text
        def inside(L, b):
            cx, cy = (L.x0 + L.x1) / 2, (L.y0 + L.y1) / 2
            return b[0] <= cx <= b[2] and b[1] <= cy <= b[3]
        fig_items = []
        for b in sorted(figs, key=lambda b: b[1]):
            keep = [L for L in keep if not inside(L, b)]
            # caption: short line(s) right under the figure
            cap, capl = "", []
            below = sorted([L for L in keep if L.y0 >= b[1] + (b[3] - b[1]) * 0.5 and L.y0 >= b[3] - 6 and L.y0 - b[3] < body_h * 3.2], key=lambda L: L.y0)
            def capsl_(lt): return sum(c.isupper() for c in lt) > 0.7 * max(1, sum(c.isalpha() for c in lt))
            if below:
                L = below[0]
                if L.size and body_size:
                    if L.size < body_size * 0.93 and not capsl_(L.text):
                        capl = [L]
                        rest = sorted([M for M in keep if M.y0 > L.y0 and M.size and M.size < body_size * 0.93], key=lambda M: M.y0)
                        for M in rest:
                            if M.y0 - capl[-1].y1 < body_h * 0.9 and len(capl) < 8: capl.append(M)
                            else: break
                else:
                    cx = (L.x0 + L.x1) / 2
                    centered = abs(cx - (b[0] + b[2]) / 2) < W * 0.12
                    if centered and L.h <= body_h * 1.05 and not capsl_(L.text) and len(L.text) < 140 \
                            and (L.x1 - L.x0) < (b[2] - b[0]) * 1.15 and (L.x1 - L.x0) < W * 0.75:
                        capl = [L]
                        if len(below) > 1 and below[1].y0 - L.y1 < body_h * 0.9 and abs((below[1].x0 + below[1].x1) / 2 - cx) < W * 0.08:
                            capl.append(below[1])
            if not capl:
                for L in keep:
                    if re.match(r"^(Рис|Рисунок|Фиг|Карта)\b", L.text) and abs(L.y0 - b[3]) < body_h * 6:
                        capl = [L]; break
            if capl:
                cap = ""
                for L in capl:
                    t2 = L.text
                    if re.search(r"[А-Яа-яЁё][-\u00ad]$", cap) and re.match(r"^[а-яё]", t2): cap = cap[:-1] + t2
                    else: cap = (cap + " " + t2).strip()
                keep = [L for L in keep if L not in capl]
            fign += 1
            name = f"f{fign:03d}.webp"
            w, h = save_crop(img, b, f"{out}/img/{name}")
            fig_items.append({"y": int(b[1]), "name": name, "cap": cap, "w": w, "h": h, "page": pn})
        # lines -> paragraphs on this page, figures interleaved by y within column order
        paras = []
        cur = None
        prev = None
        # right margin per block
        right = collections.defaultdict(float); left = collections.defaultdict(lambda: 1e9)
        if cfg.get("two_col"):
            for L in keep:
                right[L.blk] = max(right[L.blk], L.x1); left[L.blk] = min(left[L.blk], L.x0)
        else:
            longs = [L for L in keep if len(L.words) >= 5] or keep
            if longs:
                xs0 = sorted(L.x0 for L in longs); xs1 = sorted(L.x1 for L in longs)
                pl, pr = xs0[len(xs0) // 5], xs1[len(xs1) * 4 // 5]
                for L in keep:
                    left[L.blk] = pl; right[L.blk] = pr
        prev_hyph = False
        for L in keep:
            t = L.text
            if not cfg.get("layer") and not cfg.get("old") and cfg.get("correct", True):
                ws = []
                for wi, w in enumerate(L.words):
                    frag = (wi == len(L.words) - 1 and re.search(r"[-\u00ad]$", w[0])) or (wi == 0 and prev_hyph)
                    ws.append(w[0] if (frag or w[1] >= cfg.get("trust", 80)) else correct(w[0], w[1]))
                t = " ".join(ws)
            prev_hyph = bool(re.search(r"[-\u00ad]$", L.words[-1][0]))

            bw0 = right[L.blk] - left[L.blk]
            big = (L.size and body_size and L.size >= body_size * 1.18) or \
                  (not L.size and min([w[5] - w[3] for w in L.words if len(w[0]) >= 3] or [0]) >= body_h * 1.3
                   and (bw0 <= 0 or (L.x1 - L.x0) < bw0 * 0.85)
                   and re.match(r"^[А-ЯЁA-Z«\d§]", t.strip()) and not re.search(r"[,;-]$", t.strip()))
            caps = sum(1 for c in t if c.isupper()) >= 0.7 * max(1, sum(1 for c in t if c.isalpha()))
            cx = (L.x0 + L.x1) / 2; bw = right[L.blk] - left[L.blk]
            centered = bw > 0 and abs(cx - (left[L.blk] + right[L.blk]) / 2) < W * 0.04 and (L.x1 - L.x0) < bw * 0.8
            heading = None
            hre = cfg.get("h1")
            if hre and re.match(hre, t.strip()): heading = "h1"
            elif cfg.get("h1size") and L.size and body_size and L.size >= body_size * cfg["h1size"] and CYR.search(t) or \
                 (cfg.get("h1size") and heading is None and paras and paras[-1][0] == "h1" and L.size and body_size and L.size >= body_size * cfg["h1size"]):
                heading = "h1"
            elif (big or (L.bold and len(t) < 90) or (caps and len(t) < 70 and centered)) and len(t) < 110 and CYR.search(t):
                heading = "h2"
            if heading is None and not L.size and bw0 > 0 and len(t) < 70 and not re.search(r"[,;:]$|-$", t.strip()):
                lm, rm = L.x0 - left[L.blk], right[L.blk] - L.x1
                if lm > body_h * 2 and rm > body_h * 2 and abs(lm - rm) < body_h * 1.5 and CYR.search(t) \
                        and re.match(r"^[А-ЯЁA-Z«\d]", t.strip()) and not re.search(r"[.»)]$", t.strip()):
                    heading = "h2"
            if cfg.get("h2re") and re.match(cfg["h2re"], t.strip()): heading = heading or "h2"
            if cfg.get("noheads"): heading = None
            if heading:
                def capsy(x):
                    ls_ = [c for c in x if c.isalpha()]
                    return bool(ls_) and sum(c.isupper() for c in ls_) > 0.7 * len(ls_)
                if (paras and paras[-1][0] == heading and prev is not None and L.y0 - prev.y1 < body_h * 1.2
                        and not re.search(r"[.:!?]$", paras[-1][1].strip())
                        and not re.match(r"^([IVXLC]+\.|\d+\.|[а-яa-z]\)|[а-я]\.\s|§)", t.strip())
                        and capsy(paras[-1][1]) == capsy(t)):
                    a = paras[-1][1]
                    if re.search(r"[А-Яа-яЁё][-\u00ad]$", a) and re.match(r"^[а-яё]", t):
                        paras[-1][1] = a[:-1] + t
                    else:
                        paras[-1][1] = a + " " + t
                else:
                    paras.append([heading, t, L.y0]); 
                cur = None; prev = L; continue
            newp = cur is None
            if not newp:
                indent = L.x0 - left[L.blk]
                pshort = prev.x1 < right[prev.blk] - body_h * 2.2
                gap = L.y0 - prev.y1
                if indent > body_h * 0.9 and prev.x0 - left[prev.blk] < body_h * 0.6: newp = True
                elif pshort: newp = True
                elif gap > body_h * 1.1: newp = True
                elif L.blk != prev.blk and L.y0 < prev.y0: newp = False   # column jump mid-paragraph
                if cfg.get("tesspar") and L.par != prev.par: newp = True
            if newp:
                cur = ["p", t, L.y0]; paras.append(cur)
            else:
                a = cur[1]
                if re.search(r"[А-Яа-яЁё][-­]$", a) and re.match(r"^[а-яё]", t):
                    nxt = re.match(r"^[а-яё]+", t).group(0)
                    if nxt in PARTICLES and not a.endswith("­"):
                        cur[1] = a + t
                    else:
                        cur[1] = a[:-1] + t
                else:
                    cur[1] = a + " " + t
            prev = L
        # interleave figures by vertical position (good enough for single-column pages)
        items = [(p[2], p[0], p[1]) for p in paras] + [(f["y"], "fig", f) for f in fig_items]
        if cfg.get("figs_first"):
            items.sort(key=lambda it: (0 if it[1] == "fig" else 1, it[0]))
        elif not cfg.get("two_col"):
            items.sort(key=lambda it: it[0])
        else:
            # keep text order; place each figure before the first paragraph below it
            ps = [it for it in items if it[1] != "fig"]; fs = [it for it in items if it[1] == "fig"]
            res = []
            for it in ps:
                while fs and fs[0][0] <= it[0]: res.append(fs.pop(0))
                res.append(it)
            items = res + fs
        for y, kind, obj in items:
            blocks.append([kind, obj, pn])
    # join paragraphs across pages
    res = []
    for b in blocks:
        if res and b[0] == "p" and res[-1][0] == "p" and res[-1][2] != b[2]:
            a = res[-1][1]
            if not re.search(r"[.!?:;»\"…)]$", a) and re.match(r"^[а-яё(«,]", b[1]):
                if re.search(r"[А-Яа-яЁё][-­]$", a):
                    res[-1][1] = a[:-1] + b[1]
                else:
                    res[-1][1] = a + " " + b[1]
                continue
        # a figure that interrupted a paragraph across pages: let the text continue after it
        if res and b[0] == "p" and len(res) > 1 and res[-1][0] == "fig" and res[-2][0] == "p":
            a = res[-2][1]
            if not re.search(r"[.!?:;»\"…)]$", a) and re.match(r"^[а-яё(«,]", b[1]):
                res[-2][1] = (a[:-1] if re.search(r"[А-Яа-яЁё][-­]$", a) else a + " ") + b[1]
                continue
        res.append(b)
    if not cfg.get("layer"):
        for b in res:
            if b[0] == "h2" and re.search(r"[.)…!?»]$", b[1].strip()) and not re.match(r"^(\d+|[IVXLC]+)\.\s", b[1]):
                letters = [c for c in b[1] if c.isalpha()]
                if not (letters and sum(c.isupper() for c in letters) > 0.7 * len(letters)):
                    b[0] = "p"
    # chapter synopses: "Тезис. — Выяснение тезиса. — …", set centred over
    # several lines; the first lines read as headings, the last as text
    for k2, b in enumerate(res):
        if b[0] == "h2" and (b[1].rstrip().endswith("—") or b[1].count(" — ") >= 1 and re.search(r"\. —", b[1])):
            b[0] = "arg"
    merged = []
    for b in res:
        if merged and merged[-1][0] == "arg" and b[0] in ("arg", "h2") and merged[-1][1].rstrip().endswith("—"):
            merged[-1][1] += " " + b[1]; continue
        if merged and merged[-1][0] == "arg" and b[0] in ("p", "arg") and not re.search(r"[.!?»)]$", merged[-1][1].rstrip()) and len(b[1]) < 200 and merged[-1][2] == b[2]:
            merged[-1][1] += " " + b[1]; continue
        merged.append(b)
    res = merged
    for b in res:
        if b[0] == "h2" and len(b[1]) > cfg.get("h2_max", 120): b[0] = "arg"
        if b[0] != "fig":
            b[1] = re.sub(r"\s+", " ", b[1].replace("\u00ad", "")).strip()
            if not cfg.get("layer"): b[1] = ocr_clean(b[1])
            if not cfg.get("old"): b[1] = desperse(b[1])
            if not cfg.get("old") and cfg.get("layer") and cfg.get("correct"):
                b[1] = " ".join(correct(w, cfg.get("layer_conf", 60)) for w in b[1].split(" "))
            b[1] = re.sub(r" ([,.;:!?»)])", r"\1", b[1]); b[1] = re.sub(r"([«(]) ", r"\1", b[1])
        elif b[1].get("cap") and not cfg.get("old"):
            c = b[1]["cap"]
            if cfg.get("correct", not cfg.get("layer")):
                c = " ".join(correct(w, cfg.get("layer_conf", 70)) for w in c.split(" "))
            b[1]["cap"] = desperse(c)
    # stray marks taken for headings: printer's signatures, stamps, crumbs
    def junk_head(t):
        if re.fullmatch(r"\s*([IVXLC]+|\d{1,2})\.?\s*", t): return False
        cy = CYR.findall(t)
        if len(cy) < 4 or "]" in t: return True
        letters = [c.lower() for c in t if c.isalpha()]
        return len(set(letters)) < 0.3 * len(letters) and len(letters) > 10
    res = [b for b in res if not (b[0] in ("h1", "h2") and junk_head(b[1]))]
    json.dump({"slug": slug, "blocks": res, "body_h": body_h}, open(f"{out}/book.json", "w"), ensure_ascii=False, indent=0)
    nh1 = sum(1 for b in res if b[0] == "h1"); nh2 = sum(1 for b in res if b[0] == "h2")
    print(f"{slug}: {len(res)} blocks, {nh1} h1, {nh2} h2, {fign} figures")

if __name__ == "__main__":
    for s in sys.argv[1:]: run(s)
