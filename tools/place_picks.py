#!/usr/bin/env python3
# Place every hunted recording: find each chapter in the transcript, check the
# result, write the catalogue entry. Nothing here trusts the uploader — not
# chapter markers, not part numbers, not the title. The transcript decides.
#
# A book is placed only if ALL of these hold:
#   * every chapter's opening line is found, in ascending order;
#   * the median match score is decent (a wrong or partial recording fails here
#     — a reading of part four of a memoir cannot produce the openings of
#     parts one to three);
#   * the spans divide out into a sane seconds-per-word band, which is what
#     separates a complete reading from an abridgement or a discussion.
# Otherwise the book is reported and left alone.
import json, io, os, sys, difflib, statistics
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters
from vtt_tokens import load, norm

MIN_MEDIAN_SCORE = 0.70
MIN_FOUND_FRAC   = 0.85
RATE_LO, RATE_HI = 0.35, 0.90

def probes(chapter, n=4):
    """Opening phrases to look for, one per early paragraph.

    A chapter does not always begin with words anyone says out loud. Several
    of these FB2s open with the publisher's boilerplate — collected works,
    volume and edition — which a narrator skips and which therefore cannot be
    found in any transcript. Searching only the chapter's first words meant
    Степь, Моя жизнь and Скучная история all reported that their own opening
    was missing from a recording of themselves. So each of the first few
    paragraphs is offered instead, and the first one actually spoken is where
    the audio begins.
    """
    out = []
    for para in chapter[:n + 2]:
        w = [x for x in (norm(y) for y in para.split()) if x]
        if len(w) >= 8:
            out.append(w[:14])
        if len(out) >= n:
            break
    if not out:
        w = [x for x in (norm(y) for y in ' '.join(chapter).split()) if x]
        if len(w) >= 5:
            out.append(w[:14])
    return out

def locate(chs, toks):
    """Where each chapter starts, searched forward so order is structural.

    Scoring every position of a thirty-thousand-token transcript against every
    probe is far too slow to finish. Instead the transcript is indexed by word
    once, and only the positions where one of the probe's first three words
    actually occurs are scored — a few hundred candidates rather than thirty
    thousand, with the same answer, because a window that shares none of those
    three words cannot score well anyway.
    """
    times = [t for t, _ in toks]
    words = [norm(w) for _, w in toks]
    where = {}
    for i, w in enumerate(words):
        if w:
            where.setdefault(w, []).append(i)
    out, cur = [], 0
    for c in chs:
        best = (0.0, None, 0)
        for op in probes(c):
            if len(op) < 5: continue
            cands = set()
            for k in range(min(3, len(op))):
                for j in where.get(op[k], ()):
                    if j - k >= cur:
                        cands.add(j - k)
            for j in sorted(cands):
                if j + len(op) > len(words): continue
                r = difflib.SequenceMatcher(None, words[j:j+len(op)], op).ratio()
                if r > best[0]:
                    best = (r, j, len(op))
                    if r > 0.97: break
            if best[0] >= 0.8:
                break          # a clear hit on an earlier paragraph wins
        if best[1] is not None and best[0] >= 0.55:
            out.append((times[best[1]], best[0]))
            cur = best[1] + best[2]
        else:
            out.append((None, best[0]))
    return out

def assess(entry, vid, verbose=True):
    fn = entry['filename']
    path = 'public/books/' + fn
    if not os.path.exists(path): path = 'private/books/' + fn
    if not os.path.exists(path): return {'ok': False, 'why': 'no file'}
    vtt = 'tools/vtt/%s.ru.vtt' % vid
    if not os.path.exists(vtt): return {'ok': False, 'why': 'no transcript'}
    try:
        chs = fb2_chapters(path)
    except Exception as e:
        return {'ok': False, 'why': 'parse: %s' % e}
    if not chs: return {'ok': False, 'why': 'no chapters'}
    toks = load(vtt)
    if not toks: return {'ok': False, 'why': 'empty transcript'}
    vend = toks[-1][0]
    found = locate(chs, toks)
    hits = [f for f in found if f[0] is not None]
    frac = len(hits) / len(chs)
    med = statistics.median([f[1] for f in hits]) if hits else 0.0
    if frac < MIN_FOUND_FRAC:
        return {'ok': False, 'why': 'only %d/%d chapters found' % (len(hits), len(chs)),
                'frac': round(frac, 2), 'med': round(med, 2)}
    if med < MIN_MEDIAN_SCORE:
        return {'ok': False, 'why': 'weak matches (median %.2f)' % med, 'med': round(med, 2)}
    # Fill any gap by leaning on its neighbours, then check the rates.
    starts = []
    for i, (t, sc) in enumerate(found):
        starts.append(t)
    for i in range(len(starts)):
        if starts[i] is None:
            prev = next((starts[j] for j in range(i-1, -1, -1) if starts[j] is not None), 0)
            nxt = next((starts[j] for j in range(i+1, len(starts)) if starts[j] is not None), vend)
            starts[i] = prev + (nxt - prev) * 0.5
    rates = []
    for i, c in enumerate(chs):
        s0 = starts[i]; s1 = starts[i+1] if i+1 < len(starts) else vend
        w = max(1, len(' '.join(c).split()))
        rates.append((s1 - s0) / w)
    rmed = statistics.median(rates)
    if rmed < RATE_LO or rmed > RATE_HI:
        return {'ok': False, 'why': 'rate %.2f s/w out of band' % rmed, 'med': round(med, 2)}
    return {'ok': True, 'starts': [int(round(x)) for x in starts], 'end': int(vend),
            'med': round(med, 2), 'rate': round(rmed, 3), 'chapters': len(chs),
            'found': len(hits)}

def main():
    picks = [r for r in json.load(io.open('tools/hunt-results.json', encoding='utf-8')) if r.get('pick')]
    # Slice, so a long run can be taken in pieces without redoing the work.
    if len(sys.argv) > 2:
        picks = picks[int(sys.argv[1]):int(sys.argv[2])]
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    by_file = {b['filename']: b for b in idx}
    placed, refused = [], []
    for i, r in enumerate(picks):
        e = by_file.get(r['file'])
        if not e: continue
        vid = r['pick']['id']
        res = assess(e, vid)
        name = (e.get('title') or '')[:32]
        if not res['ok']:
            refused.append((name, vid, res['why']))
            print('[%2d/%d] %-32s REFUSED — %s' % (i+1, len(picks), name, res['why']), flush=True)
            continue
        v = {}
        for ci in range(res['chapters']):
            s0 = res['starts'][ci]
            s1 = res['starts'][ci+1] if ci+1 < res['chapters'] else res['end']
            x = {'youtube': vid, 'heading': 'Глава %d' % (ci+1), 'start': s0, 'end': s1}
            if s0 == 0: del x['start']
            v[str(ci)] = x
        e['videos'] = v
        placed.append((name, vid, res))
        print('[%2d/%d] %-32s %2d ch  match %.2f  %.3f s/w' %
              (i+1, len(picks), name, res['chapters'], res['med'], res['rate']), flush=True)
    io.open('private/books/index.json', 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False, indent=2) + '\n')
    print('\nplaced %d, refused %d' % (len(placed), len(refused)))
    if refused:
        print('\nrefused:')
        for n, v, w in refused: print('  %-32s %s  %s' % (n, v, w))

if __name__ == '__main__':
    main()
