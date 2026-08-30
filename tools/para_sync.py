# Align every paragraph of a chapter to its moment in the recording, using the
# video's auto-caption transcript. The product is one JSON per chapter mapping
# paragraph index -> absolute seconds in the video, which is what a "jump
# here" button needs and nothing more.
#
# Method: each paragraph's opening words are matched against the timed token
# stream, searching FORWARD from the previous paragraph's match in a bounded
# window around where the paragraph is expected to fall (previous position +
# previous paragraph's word count). Monotonicity is therefore structural, not
# checked after the fact. Paragraphs the captions garble are interpolated
# between their matched neighbours by word count.
import re, io, json, sys, difflib, bisect
sys.path.insert(0, 'tools')
from vtt_tokens import load, norm

def paragraphs_of_chunk(chunk):
    return [re.sub(r'<[^>]+>', '', p) for p in re.findall(r'<p>(.*?)</p>', chunk, re.S)]

def words_of(text):
    return [w for w in (norm(x) for x in text.split()) if w]

def align_chapter(paras, toks, t0, t1):
    # Each paragraph is looked for where it OUGHT to fall — chapter start plus
    # the narrator's rate times the words before it — inside a generous window.
    # No running lock: one garbled opening then fails alone instead of
    # derailing everything after it. Order is enforced afterwards by keeping
    # the longest increasing run of matches and interpolating the rest.
    times = [t for t, _ in toks]
    words = [norm(w) for _, w in toks]
    lo = bisect.bisect_left(times, t0)
    hi = bisect.bisect_left(times, t1) if t1 else len(times)
    wc = [max(1, len(words_of(p))) for p in paras]
    total_w = sum(wc)
    span = (t1 - t0) if t1 else (times[-1] - t0)
    rate = span / max(total_w, 1)
    cands = {}
    cum = 0
    for pi, para in enumerate(paras):
        op = words_of(para)[:10]
        exp_t = t0 + rate * cum
        cum += wc[pi]
        if len(op) < 4:
            continue
        a = bisect.bisect_left(times, exp_t - 75)
        b = bisect.bisect_left(times, exp_t + 75)
        a, b = max(lo, a), min(hi, b)
        best = (0.0, None)
        for j in range(a, max(a + 1, b - len(op))):
            r = difflib.SequenceMatcher(None, words[j:j+len(op)], op).ratio()
            if r > best[0]:
                best = (r, times[j])
                if r > 0.95: break
        if best[0] >= 0.6:
            cands[pi] = best[1]
    # Longest increasing subsequence over the matched times, so one wrong match
    # cannot fold time backwards for its neighbours.
    ks = sorted(cands)
    import functools
    seq = [(k, cands[k]) for k in ks]
    n = len(seq)
    best_len = [1] * n; prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if seq[j][1] <= seq[i][1] and best_len[j] + 1 > best_len[i]:
                best_len[i] = best_len[j] + 1; prev[i] = j
    keep = {}
    if n:
        i = max(range(n), key=lambda x: best_len[x])
        while i >= 0:
            keep[seq[i][0]] = seq[i][1]; i = prev[i]
    # Interpolate everything else between kept anchors by word count.
    out = dict(keep)
    anchors = sorted(keep)
    allk = list(range(len(paras)))
    for a, b in zip(anchors, anchors[1:]):
        gap = [k for k in allk if a < k < b]
        if not gap: continue
        tot = sum(wc[k] for k in [a] + gap)
        t, sp = out[a], out[b] - out[a]
        acc = 0
        for k in [a] + gap:
            if k != a: out[k] = t + sp * acc / tot
            acc += wc[k]
    if anchors:
        first, last = anchors[0], anchors[-1]
        r0 = rate
        for k in allk:
            if k < first:
                out[k] = max(t0, out[first] - r0 * sum(wc[k:first]))
            elif k > last:
                out[k] = out[last] + r0 * sum(wc[last:k])
    return {str(k): int(round(v)) for k, v in sorted(out.items())}, len(keep), len(paras)
