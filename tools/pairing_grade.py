#!/usr/bin/env python3
"""Grade every pairing on evidence length cannot fake, and say which should flow.

translation_scan.py measures expansion, which answers "is this a translation or
a retelling" and answers it well. It is the wrong instrument for "is this
pairing correct": short dialogue paragraphs make the ratio noisy, so Вий and
Тарас Бульба flagged high while their pairs are visibly right.

scan_alignment.score_file already has the right measure. Names and numbers
survive translation, so a correct pairing shares them far more often than a
wrong one — and it grades that against the SAME paragraphs matched to the
wrong English, rotated half a chapter along. That baseline is what matters: a
book thick with names scores high either way, and only the LIFT over its own
null means anything.

Books whose lift collapses toward 1 are not pairing; they are guessing. Those
are the ones to switch to flow mode, where the English claims no row.

    python3 tools/pairing_grade.py
"""
import io, json, os, sys, statistics
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters, score_file

def main():
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    rows = []
    for b in idx:
        d = b.get('parallelEn')
        if not d or not os.path.isdir('public/books/' + d): continue
        path = 'public/books/' + b['filename']
        if not os.path.exists(path): path = 'private/books/' + b['filename']
        try: chs = fb2_chapters(path) or []
        except Exception: continue
        if not chs: continue
        lifts, anchors, offs = [], [], []
        for ci, c in enumerate(chs):
            f = 'public/books/%s/%02d.json' % (d, ci + 1)
            if not os.path.exists(f): continue
            try: m = json.load(io.open(f, encoding='utf-8'))
            except Exception: continue
            r = score_file(c, m)
            if r.get('lift') is not None:
                lifts.append(r['lift']); anchors.append(r.get('anchor') or 0)
                if r.get('offset'): offs.append(r['offset'])
        if len(lifts) < 2: continue
        rows.append({'title': b['title'], 'dir': d, 'flow': bool(b.get('flowEn')),
                     'verse': bool(b.get('verse')) or b.get('category') == 'Poetry',
                     'lift': statistics.median(lifts), 'anchor': statistics.median(anchors),
                     'chapters': len(lifts),
                     'offset': statistics.median(offs) if offs else None})
    rows.sort(key=lambda r: r['lift'])
    io.open('/tmp/grade.json', 'w', encoding='utf-8').write(json.dumps(rows, ensure_ascii=False, indent=1))
    print('%-38s %6s %7s %7s  %s' % ('book', 'lift', 'anchor', 'offset', 'verdict'))
    for r in rows:
        v = []
        if r['flow']: v.append('(already flows)')
        elif r['lift'] < 1.6: v.append('SHOULD FLOW')
        if r['offset']: v.append('displaced %+d rows' % r['offset'])
        if r['verse']: v.append('(verse)')
        print('%-38s %6.2f %6.0f%% %7s  %s' % (
            r['title'][:38], r['lift'], r['anchor'] * 100,
            ('%+d' % r['offset']) if r['offset'] else '-', ' '.join(v)))
    print('\n%d graded' % len(rows))

if __name__ == '__main__':
    main()
