#!/usr/bin/env python3
# Place a recording that reads the book's parts in an order of its own.
#
# place_picks.py searches forward: each chapter must appear after the last, so
# order is structural and a wrong recording cannot fake it. That is right for a
# novel and wrong for a collection. The reading of Повести Белкина attached
# here works backwards through the tales — Барышня-крестьянка at nine minutes,
# Выстрел at two hours twenty — and a forward search finds two of six while a
# proportional fallback quietly points every chapter at the wrong story.
#
# So each chapter is located independently, and the recording's own order is
# whatever comes back. What replaces the forward constraint as the guard
# against a wrong recording is that EVERY chapter must be found, each at a
# distinct place, and the spans they carve out must all divide into a sane
# reading rate. A recording of a different book cannot produce six openings.
import json, io, os, sys, difflib, statistics
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters
from vtt_tokens import load, norm

MIN_SCORE = 0.62
RATE_LO, RATE_HI = 0.30, 1.00

def wl(p): return [x for x in (norm(y) for y in p.split()) if x]

def openings(chapter, n=14, tries=4):
    """Several candidate openings, not one.

    Гробовщик begins with a Derzhavin epigraph in verse, and speech
    recognition turns verse to mush — matching only the chapter's first words
    scored it 0.50 and lost the tale. Its first PROSE line, 'Последние пожитки
    гробовщика Адриана Прохорова...', matches cleanly. So each of the first
    few paragraphs is offered and the best one decides."""
    out, ws = [], []
    for para in chapter[:tries + 3]:
        w = wl(para)
        if len(w) >= 8:
            out.append(w[:n])
        if len(out) >= tries: break
    if not out:
        for para in chapter:
            ws += wl(para)
            if len(ws) >= n: break
        if ws: out.append(ws[:n])
    return out

def place(path, vid):
    chs = fb2_chapters(path)
    toks = load('tools/vtt/%s.ru.vtt' % vid)
    if not chs or not toks: return {'ok': False, 'why': 'empty'}
    words = [norm(w) for _, w in toks]
    where = {}
    for i, w in enumerate(words):
        if w: where.setdefault(w, []).append(i)
    found = []
    for c in chs:
        best = (0.0, None)
        for op in openings(c):
            cands = set()
            for k in range(min(4, len(op))):
                for j in where.get(op[k], ()): cands.add(j - k)
            for j in sorted(x for x in cands if x >= 0):
                if j + len(op) > len(words): continue
                r = difflib.SequenceMatcher(None, words[j:j+len(op)], op).ratio()
                if r > best[0]:
                    best = (r, j)
                    if r > 0.97: break
            if best[0] >= 0.85: break
        found.append((best[0], toks[best[1]][0] if best[1] is not None else None,
                      sum(len(wl(x)) for x in c)))
    missing = [i for i, f in enumerate(found) if f[1] is None or f[0] < MIN_SCORE]
    if missing:
        return {'ok': False, 'why': 'chapters not found: %s' % [i+1 for i in missing]}
    order = sorted(range(len(chs)), key=lambda i: found[i][1])
    if len(set(found[i][1] for i in range(len(chs)))) != len(chs):
        return {'ok': False, 'why': 'two chapters landed on the same spot'}
    end = int(toks[-1][0])
    span = {}
    for n, i in enumerate(order):
        nxt = found[order[n+1]][1] if n + 1 < len(order) else end
        span[i] = (int(found[i][1]), int(nxt))
    rates = [(span[i][1] - span[i][0]) / float(max(found[i][2], 1)) for i in range(len(chs))]
    bad = [i+1 for i, r in enumerate(rates) if not (RATE_LO <= r <= RATE_HI)]
    if bad:
        return {'ok': False, 'why': 'chapters %s run at an impossible rate' % bad}
    return {'ok': True, 'span': span, 'order': [i+1 for i in order],
            'med': statistics.median([f[0] for f in found]),
            'rate': statistics.median(rates), 'chapters': len(chs)}

def main():
    fn, vid = sys.argv[1], sys.argv[2]
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    e = next((b for b in idx if b['filename'] == fn), None)
    if not e: print('no such book'); return
    path = 'public/books/' + fn
    if not os.path.exists(path): path = 'private/books/' + fn
    out = place(path, vid)
    if not out['ok']:
        print('%s — %s' % (e['title'], out['why'])); return
    v = {}
    for ci in range(out['chapters']):
        s0, s1 = out['span'][ci]
        x = {'youtube': vid, 'heading': 'Глава %d' % (ci + 1), 'start': s0, 'end': s1}
        if s0 == 0: del x['start']
        v[str(ci)] = x
    e['videos'] = v
    io.open('private/books/index.json', 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False, indent=2) + '\n')
    print('%s — %d chapters, read in order %s, median match %.2f, %.2f s/w'
          % (e['title'], out['chapters'], out['order'], out['med'], out['rate']))

if __name__ == '__main__':
    main()
