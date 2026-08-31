#!/usr/bin/env python3
"""Build a parallelEn folder from a clean English source, paragraph by paragraph.

Дубровский's English came from a raw OCR of Keane's 1894 Prose Tales, and the
scan's furniture came with it: running headers like "156 poushkin's prose
tales" and footnote markers sat in the body as if they were paragraphs, 18% of
the entries, with the real prose shifted out of step around them.

The replacement is the same translation from the 1916 Bell printing, as
transcribed by Distributed Proofreaders — clean prose, footnotes kept
separate. But a clean source is not an aligned one: this printing breaks each
speech onto its own line where the Russian runs them together, so the English
has 612 paragraphs against the Russian's 465 and a straight zip would put
every line after the first quotation against the wrong Russian.

So the pairing is found rather than assumed, by the same monotonic DP that
re-pairs verse here — length ratio against the book's own expansion, pulled
about by shared numerals, shared proper nouns, and whether both sides keep the
shape of a question or a line of dialogue. One Russian paragraph answered by
two English ones is a move it knows.
"""
import io, json, os, re, sys
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters, ru_stems, en_stems
import shape_check as SHAPE

# align_verse's DP lets one Russian line answer at most TWO English ones, which
# is right for verse and wrong here: a single Russian paragraph can hold a
# four-line exchange that this printing puts on four separate lines, and with
# no move wide enough the DP simply cannot reach the end — it returned nothing
# for chapter two, 15 Russian paragraphs against 32 English. So the same idea
# is rebuilt here with merges up to four, rather than widening the aligner that
# the verse books depend on.
MAX_MERGE = 4
MERGE_PENALTY = 0.45
SKIP_PENALTY = 0.90
SHAPE_WEIGHT = 0.30
NAME_BONUS = 0.60
import math, re
DIGITS = re.compile(r'\d+')

def align(R, E):
    n, m = len(R), len(E)
    rl = [max(len(x), 1) for x in R]
    el = [max(len(x), 1) for x in E]
    k = sum(el) / float(sum(rl)) if sum(rl) else 1.0
    rstem = [ru_stems(x) for x in R]
    estem = [en_stems(x) for x in E]
    def cost(i0, i1, j0, j1):
        a = sum(rl[i] for i in range(i0, i1))
        b = sum(el[j] for j in range(j0, j1))
        c = abs(math.log(max(b, 1) / (max(a, 1) * k)))
        ru = ' '.join(R[i0:i1]); en = ' '.join(E[j0:j1])
        rd = tuple(sorted(DIGITS.findall(ru))); ed = tuple(sorted(DIGITS.findall(en)))
        if rd and ed: c -= 0.35 if rd == ed else -0.20
        # Proper nouns are the one thing that survives translation intact, and
        # leaving them out was why chapter one drifted: with only length and
        # shape to go on, the DP had no reason to put Троекуров against
        # Troekouroff rather than against the paragraph beside it. This is the
        # same anchor align_verse uses — a Russian word transliterated into the
        # Latin stems it could be spelled as, matched against the English.
        rn = rstem[i0] if i1 == i0 + 1 else set().union(*[rstem[i] for i in range(i0, i1)])
        eN = estem[j0] if j1 == j0 + 1 else set().union(*[estem[j] for j in range(j0, j1)])
        if rn and eN:
            c -= NAME_BONUS * min(len(rn & eN), 3) / 3.0
        try: c += SHAPE_WEIGHT * (1.0 - SHAPE.agree(ru, en))
        except Exception: pass
        return c
    INF = float('inf')
    d = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    d[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            c = d[i][j]
            if c == INF: continue
            if i < n:
                for e in range(1, MAX_MERGE + 1):
                    if j + e > m: break
                    v = c + cost(i, i + 1, j, j + e) + MERGE_PENALTY * (e - 1)
                    if v < d[i + 1][j + e]:
                        d[i + 1][j + e] = v; bk[i + 1][j + e] = (i, j, 1, e)
                if j < m and i + 2 <= n:
                    v = c + cost(i, i + 2, j, j + 1) + MERGE_PENALTY
                    if v < d[i + 2][j + 1]:
                        d[i + 2][j + 1] = v; bk[i + 2][j + 1] = (i, j, 2, 1)
                v = c + SKIP_PENALTY
                if v < d[i + 1][j]:
                    d[i + 1][j] = v; bk[i + 1][j] = (i, j, 1, 0)
    if d[n][m] == INF: return None
    out, i, j = [], n, m
    while i or j:
        st = bk[i][j]
        if st is None: return None
        pi, pj, a, b = st
        out.append((pi, a, pj, b)); i, j = pi, pj
    return out[::-1]


# The transcription keeps its footnotes in the body, each as its own block:
# "[Footnote 4: Diminutive of Maria or Mary.]". They are not prose and no
# Russian paragraph answers them — and because this DP has no move for
# skipping an ENGLISH paragraph, every one of them had to be stapled onto some
# Russian paragraph, which is what dragged the alignment out of step and put
# "[Footnote 1: The Russians put double frames to their windows in winter.]"
# at the head of a chapter.
FOOTNOTE = re.compile(r'^\[Footnote\b')

def paras(lines):
    out, cur = [], []
    for l in lines:
        if not l.strip():
            if cur: out.append(' '.join(cur).strip()); cur = []
        else:
            cur.append(l.strip())
    if cur: out.append(' '.join(cur).strip())
    return [p for p in out if p and not FOOTNOTE.match(p)]

def main():
    src, a, b, fb2, outdir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    seg = io.open(src, encoding='utf-8').read().split('\n')[a-1:b-1]
    idx = [i for i, l in enumerate(seg) if re.match(r'^\s*CHAPTER\s+[IVXL]+\.?\s*$', l.strip())]
    enchs = []
    for n, s in enumerate(idx):
        e = idx[n+1] if n + 1 < len(idx) else len(seg)
        enchs.append(paras(seg[s+1:e]))
    ru = fb2_chapters(fb2)
    # Align the two as CONTINUOUS STREAMS, then cut the result by the Russian
    # chapter boundaries — never chapter against chapter.
    #
    # The two editions do not agree about where chapters begin. This FB2's
    # chapter one runs on past the English chapter one and swallows "Several
    # days passed, and the animosity between the two neighbours did not
    # subside"; its chapter eleven swallows the opening of English chapter
    # twelve; and around chapters fourteen and fifteen the English sits a
    # chapter ahead before catching up again. Aligning chapter against chapter
    # forces every one of those disagreements down into the paragraph mapping,
    # where it shows up as English text sitting against the wrong Russian —
    # which is exactly the fault being repaired. As one stream the boundaries
    # stop mattering: the alignment finds the correspondence, and the Russian's
    # own chapter divisions decide afterwards which file each pair lands in.
    R = [p for c in ru for p in c]
    E = [p for c in enchs for p in c]
    starts, at = [], 0
    for c in ru:
        starts.append(at); at += len(c)
    print('aligning %d russian paragraphs against %d english, as one stream' % (len(R), len(E)), flush=True)
    pairs = align(R, E)
    if pairs is None:
        print('no monotonic path found'); return
    flat = {}
    for ri, rspan, ei, espan in pairs:
        if rspan <= 0 or espan <= 0: continue
        flat[ri] = ' '.join(E[ei:ei+espan]).strip()
    os.makedirs(outdir, exist_ok=True)
    tot_pairs = 0
    for ci, c in enumerate(ru):
        a = starts[ci]; b = a + len(c)
        m = {}
        for k, v in flat.items():
            if a <= k < b: m[str(k - a)] = v
        tot_pairs += len(m)
        io.open(os.path.join(outdir, '%02d.json' % (ci + 1)), 'w', encoding='utf-8').write(
            json.dumps(m, ensure_ascii=False, indent=1) + '\n')
        print('ch%-3d ru %3d  paired %3d' % (ci + 1, len(c), len(m)), flush=True)
    print('\n%d russian paragraphs carry an english line' % tot_pairs)

if __name__ == '__main__':
    main()
