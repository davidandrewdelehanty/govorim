#!/usr/bin/env python3
"""How close is each English text to the Russian it sits beside?

Three measures, none of which needs anyone to read the book:

  ratio     English words per Russian word. English translations of Russian
            run long — no cases means more prepositions, no aspect means more
            auxiliaries — so a faithful prose translation lands around 1.05 to
            1.30. Well under 1.0 means text is missing: the translator cut, or
            summarised, or the source is abridged.
  cover     how many Russian paragraphs have any English at all. A translation
            answers nearly all of them; a retelling skips.
  spread    how much the ratio varies from chapter to chapter, as the gap
            between the 20th and 80th percentile. A translator keeps roughly
            the same expansion throughout. A reteller does not: he renders one
            scene fully and waves at the next.

A book can fail one and be fine — verse compresses, a play's cast list is
never translated — so all three are printed and nothing is judged on one.
"""
import io, json, os, re, sys, statistics
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters

RU = re.compile(r'[А-Яа-яЁё]+')
EN = re.compile(r"[A-Za-z']+")

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
        rw = ew = 0; paras = 0; withen = 0; per = []; pairs = []
        for ci, c in enumerate(chs):
            f = 'public/books/%s/%02d.json' % (d, ci + 1)
            m = {}
            if os.path.exists(f):
                try: m = json.load(io.open(f, encoding='utf-8'))
                except Exception: m = {}
            r = sum(len(RU.findall(p)) for p in c)
            e = sum(len(EN.findall(str(v))) for k, v in m.items() if k != '_note')
            paras += len(c)
            withen += len([k for k in m if k != '_note'])
            rw += r; ew += e
            if r > 300 and e > 0: per.append(e / float(r))
            # Per-PAIR ratios, which is what separates the two ways a book can
            # score badly. A whole-book ratio cannot tell a translator who
            # compresses from a pairing that is simply out of step: Вечный муж
            # scores 0.91 overall and turns out to be answering a 23-word
            # Russian line with 204 words of unrelated English. Compression
            # shows up as a low MEDIAN pair; misalignment shows up as pairs
            # scattered far from it in both directions.
            for k, v in m.items():
                if k == '_note' or not str(k).lstrip('-').isdigit(): continue
                ki = int(k)
                if ki >= len(c): continue
                a = len(RU.findall(c[ki])); bb = len(EN.findall(str(v)))
                if a >= 12 and bb > 0: pairs.append(bb / float(a))
        if rw < 200: continue
        per.sort()
        spread = (per[int(len(per) * 0.8)] - per[int(len(per) * 0.2)]) if len(per) >= 5 else None
        pairs.sort()
        pmed = statistics.median(pairs) if pairs else None
        wild = (len([x for x in pairs if x < 0.55 or x > 2.6]) / float(len(pairs))) if pairs else None
        rows.append({'pmed': pmed, 'wild': wild, 'npairs': len(pairs),
                     'title': b['title'], 'dir': d, 'flow': bool(b.get('flowEn')),
                     'verse': bool(b.get('verse')) or b.get('category') == 'Poetry',
                     'ru': rw, 'en': ew, 'ratio': ew / float(rw),
                     'cover': withen / float(max(paras, 1)), 'spread': spread,
                     'chapters': len(chs)})
    rows.sort(key=lambda r: r['ratio'])
    io.open('/tmp/tscan.json', 'w', encoding='utf-8').write(json.dumps(rows, ensure_ascii=False, indent=1))
    rows.sort(key=lambda r: (r['pmed'] is None, r['pmed'] or 0))
    print('%-36s %6s %6s %6s %6s  %s' % ('book', 'pair', 'wild', 'cover', 'ru w', 'verdict'))
    for r in rows:
        f = []
        if r['flow']:
            f.append('flow - not paired by line')
        else:
            if r['wild'] is not None and r['wild'] > 0.30: f.append('MISALIGNED')
            elif r['pmed'] is not None and r['pmed'] < 1.05: f.append('COMPRESSED')
            if r['cover'] < 0.80: f.append('gaps')
        if r['verse']: f.append('(verse)')
        print('%-36s %6s %5s%% %5.0f%% %6d  %s' % (
            r['title'][:36],
            ('%.2f' % r['pmed']) if r['pmed'] is not None else '-',
            ('%.0f' % (r['wild'] * 100)) if r['wild'] is not None else '-',
            r['cover'] * 100, r['ru'], ' '.join(f)))
    print('\n%d paired books measured' % len(rows))

if __name__ == '__main__':
    main()
