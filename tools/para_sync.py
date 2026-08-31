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

SPEAKER = re.compile(r'^\s*(?:[А-ЯЁ][а-яё]*\.?\s*){1,3}\s*(?:\([^)]*\)\s*)?\.\s+')
STAGE   = re.compile(r'\([^)]*\)')

def spoken(text):
    """What an actor actually says, out of what the page prints.

    A printed play gives every speech its character's name — "Медведенко.
    Отчего вы всегда ходите в черном?" — and stage directions in parentheses.
    None of it is spoken aloud, so a ten-word probe taken off the page spends
    its first words on text that cannot be in the recording. Чайка anchored
    28% of its paragraphs that way. Only the probe is cleaned; the paragraph
    itself is untouched, because its index is what the map is keyed by.
    """
    t = SPEAKER.sub('', text or '')
    return STAGE.sub(' ', t)


def align_chapter(paras, toks, t0, t1, play=False):
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
    # Where a paragraph OUGHT to fall is only as good as the assumption that
    # the reading proceeds evenly, and a staged performance does not: stage
    # business, music and silence fall where the play needs them, not in
    # proportion to the words. Over a 43-minute act of Чайка the drift ran
    # well past the ±75s window and every paragraph missed, so a performance
    # whose act boundaries were already confirmed to the second produced no
    # map at all.
    #
    # So look twice. The first pass samples widely with a window loose enough
    # to survive that drift, which costs little because it probes one
    # paragraph in eight. Those anchors then say what the local pace actually
    # is, and the second pass asks the tight question — where does THIS
    # paragraph fall, between the two anchors that surround it — which is the
    # question the ±75s window was always meant to answer.
    def probe(pi, para, centre, half):
        op = words_of(spoken(para) if play else para)[:10]
        if len(op) < 4:
            return None
        a = max(lo, bisect.bisect_left(times, centre - half))
        b = min(hi, bisect.bisect_left(times, centre + half))
        best = (0.0, None)
        for j in range(a, max(a + 1, b - len(op))):
            r = difflib.SequenceMatcher(None, words[j:j+len(op)], op).ratio()
            if r > best[0]:
                best = (r, times[j])
                if r > 0.95: break
        return best[1] if best[0] >= 0.6 else None

    cum_at = []
    cum = 0
    for pi in range(len(paras)):
        cum_at.append(cum); cum += wc[pi]

    coarse = {}
    step = max(1, len(paras) // 24)
    for pi in range(0, len(paras), step):
        t = probe(pi, paras[pi], t0 + rate * cum_at[pi], 300)
        if t is not None:
            coarse[pi] = t
    # Keep only the coarse anchors that move forward together; a wide window
    # buys reach at the cost of the occasional wild match.
    ck = sorted(coarse)
    fwd, last_t = [], -1
    for k in ck:
        if coarse[k] >= last_t:
            fwd.append(k); last_t = coarse[k]
    coarse = {k: coarse[k] for k in fwd}
    ca = sorted(coarse)

    def expected(pi):
        """Where this paragraph falls, given the coarse anchors around it."""
        if not ca:
            return t0 + rate * cum_at[pi]
        before = [k for k in ca if k <= pi]
        after = [k for k in ca if k > pi]
        if before and after:
            a, b = before[-1], after[0]
            wa, wb = cum_at[a], cum_at[b]
            f = (cum_at[pi] - wa) / float(max(wb - wa, 1))
            return coarse[a] + f * (coarse[b] - coarse[a])
        if before:
            a = before[-1]
            return coarse[a] + rate * (cum_at[pi] - cum_at[a])
        b = after[0]
        return coarse[b] - rate * (cum_at[b] - cum_at[pi])

    cands = {}
    for pi, para in enumerate(paras):
        if pi in coarse:
            cands[pi] = coarse[pi]
            continue
        t = probe(pi, para, expected(pi), 75)
        if t is not None:
            cands[pi] = t
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
    # Only the paragraphs actually FOUND in the transcript get a time.
    #
    # This used to fill the gaps by interpolating between anchors on word
    # count, which gave every paragraph a jump button. The times were
    # plausible and that was the problem: a button that lands thirty seconds
    # out is worse than no button, because the reader cannot tell which kind
    # they just pressed, and one bad jump teaches them not to trust any of
    # them. An arrow now means the words beside it were located in the
    # recording. Where the transcript garbled a passage, or the reader cut it,
    # there is simply no arrow — which is honest, and the paragraph above it
    # still gets you close.
    return ({str(k): int(round(v)) for k, v in sorted(keep.items())},
            len(keep), len(paras))
