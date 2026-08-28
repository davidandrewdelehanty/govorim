#!/usr/bin/env python3
"""Semantic alignment for the parallel texts, using multilingual embeddings.

Everything before this scored a candidate pairing by how LONG the paragraphs
were, with proper names as a tiebreak. That is a proxy for meaning, and it
fails exactly where it matters: Gogol's chapters all mention Тарас, and every
paragraph of the right size looks equally plausible, so an alignment can drift
a chapter and still score well.

A multilingual sentence embedding model puts a Russian sentence and its English
translation at nearly the same point in vector space, so similarity becomes a
dot product and the question stops being "is this the right shape?" and becomes
"is this the same passage?".

    python3 tools/embed_align.py --selftest      # verify the model works

Models (first run downloads once, then it is cached and offline):
    paraphrase-multilingual-MiniLM-L12-v2   ~470 MB, fast        (default)
    LaBSE                                   ~1.8 GB, most accurate
"""
import argparse, hashlib, os, sys

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "govorim-embed")

_model = None
_model_name = None

def load(model_name=DEFAULT_MODEL):
    """Load once and keep it; loading is far slower than encoding."""
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise SystemExit(
            "sentence-transformers is not installed.\n"
            "    pip install sentence-transformers")
    _model = SentenceTransformer(model_name)
    # A paragraph is identified by its opening; the rest is cost without
    # benefit. Capping the sequence at 128 tokens is roughly 3x faster than
    # the 512 default and makes no measurable difference to which paragraph
    # matches which.
    try:
        _model.max_seq_length = 128
    except Exception:
        pass
    _model_name = model_name
    return _model

def encode(texts, model_name=DEFAULT_MODEL, batch=128, cache_key=None,
           label=None):
    """Embed a list of paragraphs, L2-normalised. Cached on disk by content."""
    import numpy as np
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    path = None
    if cache_key:
        h = hashlib.sha1(("\x00".join(texts) + model_name).encode("utf-8")).hexdigest()[:16]
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, "%s-%s.npy" % (cache_key, h))
        if os.path.exists(path):
            try:
                return np.load(path)
            except Exception:
                pass
    m = load(model_name)
    if label:
        print("      embedding %-6s %5d paragraphs ..." % (label, len(texts)),
              flush=True)
    # 400 characters, not 1000: at 128 tokens the model never sees past
    # roughly that anyway, so the extra text is pure cost.
    v = m.encode([t[:400] for t in texts], batch_size=batch,
                 convert_to_numpy=True, normalize_embeddings=True,
                 show_progress_bar=False)
    v = v.astype("float32")
    if path:
        try:
            np.save(path, v)
        except Exception:
            pass
    return v

# ── paragraph alignment ──────────────────────────────────────────────────
def align_paragraphs(ru_ps, en_ps, ru_vec, en_vec, band=None,
                     merge_cost=0.06, skip_cost=0.42):
    """Monotone DP maximising semantic similarity.

    Moves: 1-1, one Russian to two English, two Russian to one English, and
    skipping either side. Translators merge and split, and some paragraphs
    have no counterpart at all, so all five are needed.

    The search is BANDED — only pairings near the diagonal are considered.
    Alignment is monotone, so a paragraph 3,000 positions out of place is not
    a real candidate, and the band keeps a 6,000-paragraph novel from needing
    a 6,000 x 3,000 table.
    """
    import numpy as np
    n, m = len(ru_ps), len(en_ps)
    if n == 0 or m == 0:
        return {}
    if band is None:
        band = max(60, int(0.12 * max(n, m)))
    ratio = m / float(n)

    def lo_hi(i):
        c = int(i * ratio)
        return max(0, c - band), min(m, c + band + 1)

    NEG = -1e18
    W = 2 * band + 3
    def idx(i, j):
        lo, _ = lo_hi(i)
        k = j - lo + 1
        return k if 0 <= k < W else None

    d = [[NEG] * W for _ in range(n + 1)]
    bk = [[None] * W for _ in range(n + 1)]
    k0 = idx(0, 0)
    if k0 is None:
        k0 = 1
    d[0][k0] = 0.0
    for i in range(n + 1):
        lo, hi = lo_hi(i) if i < n else (max(0, m - band - 1), m + 1)
        for k in range(W):
            if d[i][k] == NEG:
                continue
            j = lo + k - 1
            if j < 0 or j > m:
                continue
            base = d[i][k]
            if i < n and j < m:
                s = float(ru_vec[i] @ en_vec[j])
                kk = idx(i + 1, j + 1)
                if kk is not None and base + s > d[i + 1][kk]:
                    d[i + 1][kk] = base + s
                    bk[i + 1][kk] = (i, j, 1, 1)
            if i < n and j + 1 < m:
                s = float(ru_vec[i] @ (en_vec[j] + en_vec[j + 1]) / 2.0)
                kk = idx(i + 1, j + 2)
                if kk is not None and base + s - merge_cost > d[i + 1][kk]:
                    d[i + 1][kk] = base + s - merge_cost
                    bk[i + 1][kk] = (i, j, 1, 2)
            if i + 1 < n and j < m:
                s = float(((ru_vec[i] + ru_vec[i + 1]) / 2.0) @ en_vec[j])
                kk = idx(i + 2, j + 1)
                if kk is not None and base + s - merge_cost > d[i + 2][kk]:
                    d[i + 2][kk] = base + s - merge_cost
                    bk[i + 2][kk] = (i, j, 2, 1)
            if i < n:
                kk = idx(i + 1, j)
                if kk is not None and base - skip_cost > d[i + 1][kk]:
                    d[i + 1][kk] = base - skip_cost
                    bk[i + 1][kk] = (i, j, 1, 0)
            if j < m:
                kk = idx(i, j + 1)
                if kk is not None and base - skip_cost > d[i][kk]:
                    d[i][kk] = base - skip_cost
                    bk[i][kk] = (i, j, 0, 1)

    kend = idx(n, m)
    if kend is None or d[n][kend] == NEG:
        best, kend = NEG, None
        for k in range(W):
            if d[n][k] > best:
                best, kend = d[n][k], k
        if kend is None:
            return {}
    out, i, k = {}, n, kend
    while True:
        st = bk[i][k]
        if st is None:
            break
        pi, pj, dr, de = st
        if dr and de:
            txt = " ".join(en_ps[pj:pj + de])
            out[pi] = txt
        kk = idx(pi, pj)
        if kk is None:
            break
        i, k = pi, kk
        if i == 0 and pj == 0:
            break
    return out

def chapter_map(ru_chs, en_chs, model_name=DEFAULT_MODEL, cache_key=None):
    """Monotone chapter-to-chapter mapping on centroid similarity."""
    import numpy as np
    R, E = len(ru_chs), len(en_chs)
    if R == 0 or E == 0:
        return []
    rv = encode([" ".join(ps[:12])[:2000] for _, ps in ru_chs],
                model_name, cache_key=(cache_key + "-rch") if cache_key else None)
    ev = encode([" ".join(ps[:12])[:2000] for _, ps in en_chs],
                model_name, cache_key=(cache_key + "-ech") if cache_key else None)
    NEG = -1e18
    d = [[NEG] * (E + 1) for _ in range(R + 1)]
    bk = [[None] * (E + 1) for _ in range(R + 1)]
    d[0][0] = 0.0
    SKIP = -0.18
    for i in range(R + 1):
        for j in range(E + 1):
            if d[i][j] == NEG:
                continue
            if i < R and j < E:
                v = d[i][j] + float(rv[i] @ ev[j])
                if v > d[i + 1][j + 1]:
                    d[i + 1][j + 1], bk[i + 1][j + 1] = v, (i, j, 1, 1)
            if i < R and d[i][j] + SKIP > d[i + 1][j]:
                d[i + 1][j], bk[i + 1][j] = d[i][j] + SKIP, (i, j, 1, 0)
            if j < E and d[i][j] + SKIP > d[i][j + 1]:
                d[i][j + 1], bk[i][j + 1] = d[i][j] + SKIP, (i, j, 0, 1)
    i, j, out = R, E, {}
    while (i, j) != (0, 0):
        st = bk[i][j]
        if st is None:
            break
        pi, pj, dr, de = st
        if dr and de:
            out[pi] = pj
        i, j = pi, pj
    return [out.get(i) for i in range(R)]

def selftest(model_name=DEFAULT_MODEL):
    import numpy as np
    ru = ["А поворотись-ка, сын! Экой ты смешной какой!",
          "Дождь стучал в окна всю ночь.",
          "Я человек больной. Я злой человек. Непривлекательный я человек."]
    en = ["Turn round, my boy! How ridiculous you look!",
          "The rain beat against the windows all night.",
          "I am a sick man. I am a spiteful man. I am an unattractive man.",
          "Broad is the river Dniester, and in it are many deep pools."]
    print("loading %s ..." % model_name)
    rv, ev = encode(ru, model_name), encode(en, model_name)
    print("\n         " + "".join("  EN%d " % k for k in range(len(en))))
    ok = True
    for i in range(len(ru)):
        row = [float(rv[i] @ ev[j]) for j in range(len(en))]
        print("   RU%d   " % i + "".join("%6.2f" % x for x in row))
        if max(range(len(row)), key=lambda j: row[j]) != i:
            ok = False
    print("\n%s — each Russian line should match its own English line, and the"
          "\n   diagonal should be the highest number in its row." %
          ("PASS" if ok else "FAIL"))
    return 0 if ok else 1

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest(a.model))
    ap.print_help()
