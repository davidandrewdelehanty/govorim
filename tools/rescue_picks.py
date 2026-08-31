#!/usr/bin/env python3
# Second look at the recordings place_picks.py refused.
#
# place_picks asks one question: can every chapter's opening be found in the
# transcript? That question is unfair to verse. YouTube's speech recognition
# mangles poetry — "Печальный Демон, дух изгнанья" comes back as "реальный
# демон дух изгнать и ой их дней" — so a perfectly good reading of Демон
# scored 0.43 on its own first line and the whole book was thrown out. Worse,
# the same test cannot tell that apart from a recording that ISN'T the book:
# a lecture about Домик в Коломне also fails to match its opening.
#
# So this asks a different question, one that does not depend on any single
# passage surviving transcription: sample the work at even intervals and see
# whether the transcript walks through those samples in order, at a steady
# rate. A reading of the text does; a lecture about it does not, and neither
# does an abridgement — it runs out of text early or skips whole stretches.
#
# Chapters are then placed by interpolating between the samples that did
# match, in proportion to the words between them. Nothing is placed unless
# the coverage check passes first.
import json, io, os, sys, difflib, statistics
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters
from vtt_tokens import load, norm

K            = 14      # sample points across the work
MIN_COVER    = 0.60    # of them found, in order
MIN_MED      = 0.70    # median match score of those found
RATE_LO, RATE_HI = 0.35, 0.90

def wordsof(p):
    return [x for x in (norm(y) for y in p.split()) if x]

def flatten(chs):
    """Every paragraph with the running word count that precedes it."""
    out, n = [], 0
    for ci, c in enumerate(chs):
        for p in c:
            w = wordsof(p)
            out.append({'ci': ci, 'at': n, 'w': w})
            n += len(w)
    return out, n

def sample(paras, k):
    """k probes spread evenly through the text, by word position."""
    total = paras[-1]['at'] + len(paras[-1]['w']) if paras else 0
    picks, used = [], set()
    for i in range(k):
        want = total * i // k
        best = None
        for j, p in enumerate(paras):
            if len(p['w']) < 8: continue
            if best is None or abs(p['at'] - want) < abs(paras[best]['at'] - want):
                best = j
        if best is not None and best not in used:
            used.add(best)
            picks.append(paras[best])
    return picks

def index(toks):
    words = [norm(w) for _, w in toks]
    where = {}
    for i, w in enumerate(words):
        if w: where.setdefault(w, []).append(i)
    return words, where

def find(op, words, where, floor):
    """Best position for this probe at or after `floor`."""
    cands = set()
    for k in range(min(4, len(op))):
        for j in where.get(op[k], ()):
            if j - k >= floor: cands.add(j - k)
    best = (0.0, None)
    for j in sorted(cands):
        if j + len(op) > len(words): continue
        r = difflib.SequenceMatcher(None, words[j:j+len(op)], op).ratio()
        if r > best[0]:
            best = (r, j)
            if r > 0.95: break
    return best

def walk(probes, toks, words, where):
    """Locate each probe after the last one found — order is the point."""
    out, floor = [], 0
    for p in probes:
        op = p['w'][:14]
        if len(op) < 8:
            out.append(None); continue
        sc, j = find(op, words, where, floor)
        if j is not None and sc >= 0.62:
            out.append({'at': p['at'], 't': toks[j][0], 'sc': sc})
            floor = j + len(op)
        else:
            out.append(None)
    return out

def check(entry, vid):
    fn = entry['filename']
    path = 'public/books/' + fn
    if not os.path.exists(path): path = 'private/books/' + fn
    if not os.path.exists(path): return {'ok': False, 'why': 'no file'}
    vtt = 'tools/vtt/%s.ru.vtt' % vid
    if not os.path.exists(vtt): return {'ok': False, 'why': 'no transcript'}
    chs = fb2_chapters(path)
    toks = load(vtt)
    if not chs or not toks: return {'ok': False, 'why': 'empty'}
    paras, total = flatten(chs)
    words, where = index(toks)
    hits = [h for h in walk(sample(paras, K), toks, words, where) if h]
    cover = len(hits) / float(K)
    med = statistics.median([h['sc'] for h in hits]) if hits else 0.0
    if cover < MIN_COVER:
        return {'ok': False, 'why': 'transcript follows only %d%% of the text' % (cover*100)}
    if med < MIN_MED:
        return {'ok': False, 'why': 'weak throughout (median %.2f)' % med}
    # Rate across the anchored span — a lecture or an abridgement lands outside.
    span_w = hits[-1]['at'] - hits[0]['at']
    span_t = hits[-1]['t'] - hits[0]['t']
    rate = span_t / float(span_w) if span_w else 0
    if not (RATE_LO <= rate <= RATE_HI):
        return {'ok': False, 'why': '%.2f s/w across the reading' % rate}
    # Chapter starts, interpolated between anchors by word count.
    firsts = {}
    for p in paras:
        if p['ci'] not in firsts and len(p['w']) >= 4: firsts[p['ci']] = p['at']
    starts = []
    for ci in range(len(chs)):
        at = firsts.get(ci, 0)
        if at <= hits[0]['at']:
            starts.append(0 if ci == 0 else hits[0]['t'] * at / max(hits[0]['at'], 1))
            continue
        lo = max([h for h in hits if h['at'] <= at], key=lambda h: h['at'], default=hits[0])
        hi = min([h for h in hits if h['at'] > at], key=lambda h: h['at'], default=None)
        if hi is None:
            starts.append(lo['t'] + (at - lo['at']) * rate)
        else:
            f = (at - lo['at']) / float(hi['at'] - lo['at'])
            starts.append(lo['t'] + f * (hi['t'] - lo['t']))
    starts = [max(0, int(round(s))) for s in starts]
    for i in range(1, len(starts)):
        if starts[i] <= starts[i-1]:
            return {'ok': False, 'why': 'chapters would not stay in order'}
    return {'ok': True, 'starts': starts, 'end': int(toks[-1][0]),
            'cover': cover, 'med': med, 'rate': rate, 'chapters': len(chs)}

def main():
    res = json.load(io.open('tools/hunt-results.json', encoding='utf-8'))
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    by = {b['filename']: b for b in idx}
    only = sys.argv[1:] 
    saved = 0
    for r in res:
        if not r.get('pick'): continue
        e = by.get(r['file'])
        if not e or e.get('videos'): continue          # already placed
        if only and r['title'] not in only: continue
        vid = r['pick']['id']
        out = check(e, vid)
        name = (e.get('title') or '')[:32]
        if not out['ok']:
            print('%-32s no — %s' % (name, out['why']), flush=True)
            continue
        v = {}
        for ci in range(out['chapters']):
            s0 = out['starts'][ci]
            s1 = out['starts'][ci+1] if ci+1 < out['chapters'] else out['end']
            x = {'youtube': vid, 'heading': 'Глава %d' % (ci+1), 'start': s0, 'end': s1}
            if s0 == 0: del x['start']
            v[str(ci)] = x
        e['videos'] = v
        saved += 1
        print('%-32s YES %2d ch  cover %.0f%%  med %.2f  %.2f s/w' %
              (name, out['chapters'], out['cover']*100, out['med'], out['rate']), flush=True)
    io.open('private/books/index.json', 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False, indent=2) + '\n')
    print('\nrescued %d' % saved)

if __name__ == '__main__':
    main()
