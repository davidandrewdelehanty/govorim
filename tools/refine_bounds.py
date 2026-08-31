#!/usr/bin/env python3
# Replace guessed chapter boundaries with the transcript's own answer.
#
# A few books have one recording covering several chapters and captions too
# poor to locate the chapter openings — the verse ones, where speech
# recognition turns "Печальный Демон, дух изгнанья" into "реальный демон дух
# изгнать". Their boundaries were placed in proportion to word count, which is
# a guess, and a guess that can sit twenty or thirty seconds out.
#
# But once para_sync has run, the first ANCHORED paragraph of a chapter is a
# real measurement of where that chapter begins — found in the transcript, not
# inferred from it. So there is no reason to keep the guess: the map's first
# entry becomes the chapter's start, and the chapter before it ends there.
# Chapters whose map came back empty keep what they had, because nothing
# better is known about them.
import json, io, os, glob, sys

def main():
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    only = set(sys.argv[1:])
    for b in idx:
        v = b.get('videos') or {}
        if not v: continue
        if only and b.get('title') not in only: continue
        ids = set(x.get('youtube') for x in v.values())
        if len(ids) != 1 or len(v) < 2: continue      # one recording, several chapters
        base = os.path.basename(b['filename']).rsplit('.', 1)[0]
        # Paragraph ZERO, not the first anchored paragraph. Those are different
        # numbers whenever a chapter's opening line was garbled in the
        # transcript, and using the earliest anchor would move the chapter's
        # start PAST its own first paragraphs — Красный смех would have begun
        # 193 seconds in, with the opening simply unreachable. If paragraph
        # zero was not found, nothing better than the existing boundary is
        # known, so it is left alone.
        firsts = {}
        for f in glob.glob('public/books/audio-sync/%s/*.json' % base):
            ci = int(os.path.basename(f).split('.')[0])
            m = json.load(io.open(f, encoding='utf-8'))
            if '0' in m: firsts[ci] = m['0']
        if not firsts: continue
        keys = sorted(v, key=int)
        moved = []
        for k in keys:
            ci = int(k)
            if ci not in firsts: continue
            old = v[k].get('start', 0)
            new = firsts[ci]
            if abs(new - old) < 2: continue
            v[k]['start'] = new
            if 'approx' in v[k]: del v[k]['approx']
            moved.append((ci + 1, old, new))
        # Each chapter ends where the next one starts; the last keeps its end.
        for i, k in enumerate(keys[:-1]):
            nxt = v[keys[i + 1]].get('start')
            if nxt is not None: v[k]['end'] = nxt
        for k in keys:
            if v[k].get('start') == 0: v[k].pop('start', None)
        if moved:
            print('%-26s %s' % (b['title'][:26],
                  ', '.join('ch%d %ds->%ds' % m for m in moved)))
    io.open('private/books/index.json', 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    main()
