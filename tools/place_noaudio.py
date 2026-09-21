#!/usr/bin/env python3
# Place the recordings found for the books that had no audio, then build their
# paragraph jump points — the same two steps every other book went through
# (place_playlists.run for the chapter boundaries, sync_all.run for the ▶
# maps), with one difference: chapters come from reader_chapters.py.
#
# Why: place_playlists and sync_all split the FB2 with scan_alignment, which
# predates the reader's marker splitting. For the Wikisource imports — Вешние
# воды, Мы, Обломов and the rest, whose chapters are "I", "II" inside one body —
# scan_alignment sees ONE chapter where the reader shows twelve, so a map keyed
# by its indices would point every button at the wrong page. reader_chapters is
# the port that was validated against the live site; both tools are pointed at
# it here without changing either of them.
#
#   python3 tools/place_noaudio.py            # dry run: what would be placed
#   python3 tools/place_noaudio.py --write    # write videos + audio-sync maps
import json, io, os, sys, copy
sys.path.insert(0, 'tools')
from reader_chapters import reader_chapters
import place_playlists as pp
import sync_all as sa

def as_paras(path, *a, **k):
    chs, _how = reader_chapters(path)
    return [c['paras'] for c in chs]

pp.fb2_chapters = as_paras
sa.fb2_chapters = as_paras

# A recording that opens straight into chapter one has nothing to match at its
# start but the chapter itself, and when that chapter is the book's preface or
# its cast of characters the matcher misses it — Пиковая дама loses its first
# chapter that way, На дне its list of persons. Chapter two is then found where
# chapter one ends; if the time before it is what chapter one's length would
# take to read, chapter one is simply the start of the recording.
_locate = pp.locate
def locate_fill_first(chs, toks):
    found = _locate(chs, toks)
    if len(found) > 1 and found[0][0] is None and found[1][0] == 0 and found[1][1]:
        w = max(1, len(' '.join(chs[0]).split()))
        # A cast list is read with a pause after every name, so a short first
        # chapter is allowed a slower pace than running prose.
        hi = pp.RATE_HI * (1.5 if w < 200 else 1.0)
        if pp.RATE_LO <= found[1][1] / w <= hi:
            found[0] = (0, 0.0, found[1][2])
    return found
pp.locate = locate_fill_first

def main():
    write = '--write' in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    picks = json.load(io.open('tools/hunt-noaudio.json', encoding='utf-8'))
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    by = {b['filename']: b for b in idx}
    placed = 0
    for o in picks:
        if only and o['title'] not in only: continue
        e = by.get(o['file'])
        if not e: continue
        if e.get('videos'):
            print('%-30s already has videos — left alone' % o['title'][:30]); continue
        vids = o.get('videos') or [o['video']]
        if not all(os.path.exists('tools/vtt/%s.ru.vtt' % v) for v in vids):
            print('%-30s no captions yet' % o['title'][:30]); continue
        trial = copy.deepcopy(e)
        r = pp.run(trial, vids, apply_it=True)
        if not r.get('ok'):
            print('%-30s REFUSED — %s' % (o['title'][:30], r.get('why'))); continue
        s = sa.run(trial) if write else None
        msg = '%-30s placed %d/%d chapters  match %.2f  %.3f s/w' % (
            o['title'][:30], r['chapters'], r['total'], r['med'], r['rate'])
        if r.get('split'): msg += '  (cut mid-chapter: %s)' % [x + 1 for x in r['split']]
        if s: msg += '  | jump points: %s chapters, median anchored %s%%' % (s.get('chapters'), s.get('median_anchor'))
        print(msg, flush=True)
        if write:
            e['videos'] = trial['videos']
            placed += 1
    if write and placed:
        io.open('private/books/index.json', 'w', encoding='utf-8').write(
            json.dumps(idx, ensure_ascii=False, indent=2) + '\n')
        print('wrote private/books/index.json — %d book(s) placed' % placed)

if __name__ == '__main__':
    main()
