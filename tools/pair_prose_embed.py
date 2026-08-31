#!/usr/bin/env python3
"""Pair a clean English source to a Russian text by MEANING, not by shape.

tools/pair_prose.py does this with the signals that were already here: length
ratio, shared numerals, shared proper nouns, and whether both sides keep the
shape of a question. On Дубровский it gets most of the book right and then
drifts in a handful of places, and every attempt to fix one of those by moving
a penalty broke another chapter — which is the failure embed_align.py was
written about: "Gogol's chapters all mention Тарас, and every paragraph of the
right size looks equally plausible, so an alignment can drift a chapter and
still score well."

So this runs the same extraction and the same stream-then-cut structure, and
hands the actual decision to the multilingual embedding model, where the
question stops being "is this the right shape?" and becomes "is this the same
passage?".

    pip install sentence-transformers
    python3 tools/pair_prose_embed.py tools/pushkin-prose-tales.txt 5181 8401 \\
        public/books/novel/dubrovskiy.fb2 public/books/dubrovskiy-en

The first run downloads the model (~470 MB) and caches it; later runs are
offline.
"""
import io, json, os, re, sys
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters
import embed_align as EA
from pair_prose import paras

def main():
    src, a, b, fb2, outdir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    seg = io.open(src, encoding='utf-8').read().split('\n')[a-1:b-1]
    idx = [i for i, l in enumerate(seg) if re.match(r'^\s*CHAPTER\s+[IVXL]+\.?\s*$', l.strip())]
    enchs = []
    for n, s in enumerate(idx):
        e = idx[n+1] if n + 1 < len(idx) else len(seg)
        enchs.append(paras(seg[s+1:e]))
    ru = fb2_chapters(fb2)
    R = [p for c in ru for p in c]
    E = [p for c in enchs for p in c]
    starts, at = [], 0
    for c in ru:
        starts.append(at); at += len(c)
    print('%d russian paragraphs, %d english' % (len(R), len(E)), flush=True)

    model = EA.load()
    print('model loaded; encoding', flush=True)
    rv = model.encode(R, normalize_embeddings=True, show_progress_bar=False)
    ev = model.encode(E, normalize_embeddings=True, show_progress_bar=False)
    flat = EA.align_paragraphs(R, E, rv, ev)
    print('aligned: %d russian paragraphs matched' % len(flat), flush=True)

    os.makedirs(outdir, exist_ok=True)
    tot = 0
    for ci, c in enumerate(ru):
        lo = starts[ci]; hi = lo + len(c)
        m = {}
        for k, v in flat.items():
            k = int(k)
            if lo <= k < hi:
                m[str(k - lo)] = v if isinstance(v, str) else ' '.join(v)
        tot += len(m)
        io.open(os.path.join(outdir, '%02d.json' % (ci + 1)), 'w', encoding='utf-8').write(
            json.dumps(m, ensure_ascii=False, indent=1) + '\n')
        print('ch%-3d ru %3d  paired %3d' % (ci + 1, len(c), len(m)), flush=True)
    print('\n%d russian paragraphs carry an english line' % tot)

if __name__ == '__main__':
    main()
