#!/usr/bin/env python3
# Attach a recording whose transcript is too garbled to search, but which is
# demonstrably a complete reading of the book.
#
# YouTube's speech recognition falls apart on verse — "Печальный Демон, дух
# изгнанья" comes back as "реальный демон дух изгнать и ой их дней" — so no
# amount of matching will find a chapter opening in it. But the transcript
# still tells the truth about LENGTH, and length is enough to prove the
# recording is the whole book: 6,532 spoken words for Полтава's 6,499 is a
# complete reading, while 5,490 for Руслан и Людмила's 11,290 is an
# abridgement and 1,908 slow ones for Домик в Коломне is a lecture.
#
# For a complete reading, chapter boundaries can be placed in proportion to
# the words that precede them. That is approximate — a reader pauses, and an
# epigraph takes longer than its word count — so these books get chapter
# audio but no paragraph jump points, which need real anchors.
import json, io, os, sys, difflib
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters
from vtt_tokens import load, norm

MIN_RATIO, MAX_RATIO = 0.80, 1.15   # spoken words against the book's own
MAX_CHAPTERS = 4                    # see below

# Proportional placement assumes the reader works through the book front to
# back. A continuous poem in two or three cantos always does. A COLLECTION
# does not: the reading of Повести Белкина attached to this library goes
# backwards through the tales, and placing its six chapters in proportion put
# every one of them on the wrong story — silently, because nothing in a word
# count can notice. So this refuses anything with more than a handful of
# chapters, where that risk lives, and leaves it to place_scattered.py, which
# locates each chapter and lets the recording declare its own order.

def wl(p): return [x for x in (norm(y) for y in p.split()) if x]

def place(entry, vid):
    fn = entry['filename']
    path = 'public/books/' + fn
    if not os.path.exists(path): path = 'private/books/' + fn
    chs = fb2_chapters(path)
    toks = load('tools/vtt/%s.ru.vtt' % vid)
    if not chs or not toks: return {'ok': False, 'why': 'empty'}
    spoken = len([1 for _, w in toks if norm(w)])
    counts = [sum(len(wl(p)) for p in c) for c in chs]
    total = sum(counts) or 1
    ratio = spoken / float(total)
    if not (MIN_RATIO <= ratio <= MAX_RATIO):
        return {'ok': False, 'why': 'transcript is %d%% of the book' % (ratio * 100)}
    if len(chs) > MAX_CHAPTERS:
        return {'ok': False, 'why': '%d chapters — too many to place blind' % len(chs)}
    dur = toks[-1][0]
    # Chapter starts in proportion to preceding words.
    starts, n = [], 0
    for c in counts:
        starts.append(int(round(dur * n / float(total))))
        n += c
    # Sanity: the book's own opening should turn up somewhere in the first
    # stretch of the recording, else this is the wrong book entirely.
    op = []
    for p in chs[0]:
        op = wl(p)
        if len(op) >= 8: break
    words = [norm(w) for _, w in toks]
    head = words[:max(400, len(words) // 8)]
    best = 0.0
    for j in range(max(1, len(head) - len(op))):
        best = max(best, difflib.SequenceMatcher(None, head[j:j+len(op)], op).ratio())
    return {'ok': True, 'starts': starts, 'end': int(dur), 'ratio': ratio,
            'open': best, 'chapters': len(chs)}

def main():
    res = {r['title']: r for r in json.load(io.open('tools/hunt-results.json', encoding='utf-8'))}
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    by = {b['filename']: b for b in idx}
    for title in sys.argv[1:]:
        r = res.get(title)
        if not r or not r.get('pick'):
            print('%-28s ? not in results' % title[:28]); continue
        e = by.get(r['file'])
        if not e: continue
        if e.get('videos'):
            print('%-28s already placed' % title[:28]); continue
        out = place(e, r['pick']['id'])
        if not out['ok']:
            print('%-28s no — %s' % (title[:28], out['why'])); continue
        v = {}
        for ci in range(out['chapters']):
            s0 = out['starts'][ci]
            s1 = out['starts'][ci+1] if ci+1 < out['chapters'] else out['end']
            x = {'youtube': r['pick']['id'], 'heading': 'Глава %d' % (ci+1),
                 'start': s0, 'end': s1, 'approx': True}
            if s0 == 0: del x['start']
            v[str(ci)] = x
        e['videos'] = v
        print('%-28s %2d ch  length %.0f%% of book  opening matched %.2f'
              % (title[:28], out['chapters'], out['ratio']*100, out['open']))
    io.open('private/books/index.json', 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    main()
