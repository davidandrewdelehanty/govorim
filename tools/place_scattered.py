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
from para_sync import spoken

MIN_SCORE = 0.62
# A performance cuts, paraphrases and buries lines under music, so an act's
# printed opening rarely matches as cleanly as a narrator reading it aloud.
# The forward march and the rate check below are what keep this honest; the
# score is only there to reject a match that is pure noise.
PLAY_SCORE = 0.45
# A cast list is a few dozen words. Anything longer that happens to sit in
# chapter one is the play itself.
CAST_MAX_WORDS = 400
RATE_LO, RATE_HI = 0.30, 1.00

def wl(p): return [x for x in (norm(y) for y in p.split()) if x]

def openings(chapter, n=14, tries=4, play=False):
    """Several candidate openings, not one.

    Гробовщик begins with a Derzhavin epigraph in verse, and speech
    recognition turns verse to mush — matching only the chapter's first words
    scored it 0.50 and lost the tale. Its first PROSE line, 'Последние пожитки
    гробовщика Адриана Прохорова...', matches cleanly. So each of the first
    few paragraphs is offered and the best one decides."""
    out, ws = [], []
    for para in chapter[:tries * 3 + 3]:
        w = wl(spoken(para) if play else para)
        if len(w) >= 8:
            out.append(w[:n])
        if len(out) >= tries: break
    if not out:
        for para in chapter:
            ws += wl(para)
            if len(ws) >= n: break
        if ws: out.append(ws[:n])
    return out

def place(path, vid, play=False):
    chs = fb2_chapters(path)
    toks = load('tools/vtt/%s.ru.vtt' % vid)
    if not chs or not toks: return {'ok': False, 'why': 'empty'}
    words = [norm(w) for _, w in toks]
    where = {}
    for i, w in enumerate(words):
        if w: where.setdefault(w, []).append(i)
    # A staged play is the one case where order can be assumed: no production
    # performs act three before act two. That assumption is worth having,
    # because a performance is a CUT text — this Гроза speaks 72% of what
    # Ostrovsky printed — so act openings match weakly and a free search picks
    # the wrong one. Гроза's act four landed before its act three that way.
    # Prose keeps the free search, where order is the evidence, not a given.
    floor = 0
    found = []
    for c in chs:
        best = (0.0, None)
        # Every act, not just the first. An act opens on stage directions and a
        # cast note that nobody speaks, so its first audible line can be far
        # down the page — Гроза matched two of five acts probing eight
        # paragraphs in, and all five at forty.
        deep = 40 if play else 4
        for op in openings(c, play=play, tries=deep):
            cands = set()
            for k in range(min(4, len(op))):
                for j in where.get(op[k], ()):
                    if not play or j - k >= floor: cands.add(j - k)
            for j in sorted(x for x in cands if x >= 0):
                if j + len(op) > len(words): continue
                r = difflib.SequenceMatcher(None, words[j:j+len(op)], op).ratio()
                if r > best[0]:
                    best = (r, j)
                    if r > 0.97: break
            if best[0] >= 0.85: break
        floorable = best[1] is not None and best[0] >= (PLAY_SCORE if play else MIN_SCORE)
        if play and floorable: floor = best[1] + 1
        found.append((best[0], toks[best[1]][0] if best[1] is not None else None,
                      sum(len(wl(x)) for x in c)))
    floorv = PLAY_SCORE if play else MIN_SCORE
    missing = [i for i, f in enumerate(found) if f[1] is None or f[0] < floorv]
    # A printed play opens with its cast list, and no production performs it —
    # so chapter one of a play can never be found in a recording of one, and
    # demanding it would refuse every performance in the library. It is left
    # without audio instead, which is what the Чайка спектакль already does.
    skip = set()
    # Only a SHORT unfound first chapter is a cast list. Several of these FB2s
    # open the play proper in chapter one — Вишнёвый сад has its cast folded
    # into act one, 4,240 words of it — and waving those through as unperformed
    # front matter would have quietly dropped a quarter of four plays.
    if play and missing and missing[0] == 0 and sum(len(wl(x)) for x in chs[0]) < CAST_MAX_WORDS:
        skip.add(0)
        missing = missing[1:]
    if missing:
        return {'ok': False, 'why': 'chapters not found: %s' % [i+1 for i in missing]}
    idxs = [i for i in range(len(chs)) if i not in skip]
    order = sorted(idxs, key=lambda i: found[i][1])
    if len(set(found[i][1] for i in idxs)) != len(idxs):
        return {'ok': False, 'why': 'two chapters landed on the same spot'}
    end = int(toks[-1][0])
    span = {}
    for n, i in enumerate(order):
        nxt = found[order[n+1]][1] if n + 1 < len(order) else end
        span[i] = (int(found[i][1]), int(nxt))
    # Every chapter but the last is bounded by the next chapter's opening — a
    # measurement. The last one has no such neighbour, and handing it the end
    # of the video assumes the recording stops when the book does. It often
    # does not: Мужики's last chapter matched at 0.93 like all the others and
    # then failed at 1.25 s/w purely because eleven minutes of something else
    # follows the story. So the final chapter ends where its own words run
    # out, at the pace the rest of the reading kept, and never past the video.
    interior = [i for i in idxs if i != order[-1]]
    if interior:
        base = statistics.median(
            [(span[i][1] - span[i][0]) / float(max(found[i][2], 1)) for i in interior])
        if RATE_LO <= base <= RATE_HI:
            last = order[-1]
            span[last] = (span[last][0],
                          min(end, span[last][0] + int(found[last][2] * base * 1.15)))
    rates = dict((i, (span[i][1] - span[i][0]) / float(max(found[i][2], 1))) for i in idxs)
    # One anchor landing on a phrase that recurs later throws exactly two
    # chapters out — the one that now runs long and the one that now runs
    # short — while the pair together keeps the reading's own pace. Накануне
    # did this at chapter 26: 0.20 s/w against neighbours at 0.49 to 0.63, and
    # 0.52 across the two of them. Refusing the whole book for that throws away
    # thirty-four good anchors to punish one. The disagreeing anchor is dropped
    # instead and its boundary interpolated between the two that agree, by word
    # count — the same repair para_sync makes at paragraph level.
    dropped = []
    for pass_no in range(3):
        rates = dict((i, (span[i][1] - span[i][0]) / float(max(found[i][2], 1))) for i in idxs)
        worst, worstd = None, 0
        good = [r for r in rates.values() if RATE_LO <= r <= RATE_HI]
        if len(good) < 3: break
        mid = statistics.median(good)
        for n, i in enumerate(order):
            if n == 0: continue          # chapter one starts where it starts
            r = rates[i]
            if RATE_LO <= r <= RATE_HI: continue
            d = abs(r - mid)
            if d > worstd: worst, worstd = n, d
        if worst is None: break
        n = worst
        i = order[n]
        prev = order[n-1]
        nxt = span[i][1]
        wp, wi = max(found[prev][2], 1), max(found[i][2], 1)
        newstart = span[prev][0] + int((nxt - span[prev][0]) * wp / float(wp + wi))
        span[prev] = (span[prev][0], newstart)
        span[i] = (newstart, nxt)
        dropped.append(i + 1)
    rates = dict((i, (span[i][1] - span[i][0]) / float(max(found[i][2], 1))) for i in idxs)
    bad = [i+1 for i, r in rates.items() if not (RATE_LO <= r <= RATE_HI)]
    if bad:
        return {'ok': False, 'why': 'chapters %s run at an impossible rate' % bad}
    return {'ok': True, 'span': span, 'order': [i+1 for i in order], 'dropped': dropped,
            'skipped': sorted(x+1 for x in skip),
            'med': statistics.median([found[i][0] for i in idxs]),
            'rate': statistics.median(list(rates.values())), 'chapters': len(chs)}

def main():
    fn, vid = sys.argv[1], sys.argv[2]
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    e = next((b for b in idx if b['filename'] == fn), None)
    if not e: print('no such book'); return
    path = 'public/books/' + fn
    if not os.path.exists(path): path = 'private/books/' + fn
    play = ('--play' in sys.argv) or bool(e.get('play')) or \
        str(e.get('category') or '') in ('Plays', 'Theatrical Performances')
    out = place(path, vid, play=play)
    if not out['ok']:
        print('%s — %s' % (e['title'], out['why'])); return
    v = {}
    for ci in range(out['chapters']):
        if ci not in out['span']: continue      # unperformed cast list
        s0, s1 = out['span'][ci]
        x = {'youtube': vid, 'heading': 'Глава %d' % (ci + 1), 'start': s0, 'end': s1}
        if s0 == 0: del x['start']
        v[str(ci)] = x
    e['videos'] = v
    io.open('private/books/index.json', 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False, indent=2) + '\n')
    print('%s — %d chapters, read in order %s, median match %.2f, %.2f s/w%s'
          % (e['title'], out['chapters'], out['order'], out['med'], out['rate'],
             ('; boundary interpolated for ' + str(out['dropped'])) if out.get('dropped') else ''))

if __name__ == '__main__':
    main()
