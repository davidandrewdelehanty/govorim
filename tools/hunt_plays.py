#!/usr/bin/env python3
# Look for a STAGED PERFORMANCE of a play, not a reading of it.
#
# The audio hunt ranks a candidate by how close its seconds-per-word lands to
# 0.55, this library's measured narration rate. A performance is not narration
# and must not be judged as one: Чайка's спектакль runs at 0.74 s/w, because
# staging, music and silence take time that no word count predicts. Judged by
# the reading band it would look too slow and be thrown out; judged by this one
# a plain audiobook looks too fast and is thrown out, which is the point —
# there is already an audiobook entry for every one of these plays.
#
# The title must also say what it is. That is a claim about INTENT, not about
# content, and it is the one thing a duration cannot tell you: a two-hour
# recording of Гроза at 0.9 s/w might be a filmed production or might be a
# lecture with long pauses. Everything the title claims is checked afterwards
# against the transcript by place_scattered.py, which does not care what
# anybody called it.
import json, sys, os
sys.path.insert(0, 'tools')
from hunt_audio import search, probe, title_match

RATE_LO, RATE_HI, RATE_IDEAL = 0.55, 1.45, 0.75
TITLE_FLOOR = 0.8
OUT = 'tools/hunt-plays-results.json'

# What a staged production calls itself. «Экранизация» and «фильм» catch the
# films of plays; «радиоспектакль» is deliberately absent — it is audio, and
# these entries exist to offer something to watch.
PERF = ('спектакль', 'постановка', 'театр', 'экранизация', 'фильм',
        'телеспектакль', 'телеверсия', 'сцена', 'мхат', 'малый театр')

def is_perf(t):
    low = (t or '').lower().replace('ё', 'е')
    if 'радиоспектакль' in low or 'аудиокнига' in low or 'аудиоспектакль' in low:
        return False
    return any(k in low for k in PERF)

def score(c, words, title, author):
    if not c or not c['embed'] or not c['ru_orig'] or not c['dur']:
        return None
    if title_match(title, author, c['title']) < TITLE_FLOOR:
        return None
    if not is_perf(c['title']):
        return None
    r = c['dur'] / max(words, 1)
    if r < RATE_LO or r > RATE_HI:
        return None
    return abs(r - RATE_IDEAL)

def hunt(b):
    t, a, words = b['title'], b['author_short'], b['words']
    queries = ['%s спектакль' % t,
               '%s %s спектакль' % (a, t),
               '%s фильм-спектакль' % t,
               '%s телеспектакль' % t,
               '%s постановка театр' % t]
    seen, cands = set(), []
    for q in queries:
        for e in search(q):
            if e['id'] in seen: continue
            seen.add(e['id'])
            d = e.get('duration') or 0
            if d < words * RATE_LO * 0.6 or d > words * RATE_HI * 2.0:
                continue
            if not is_perf(e.get('title') or ''):
                continue
            cands.append(e['id'])
    best, rows = None, []
    for vid in cands[:14]:
        c = probe(vid)
        if not c: continue
        sc = score(c, words, t, a)
        rows.append(dict(c, rate=round(c['dur'] / max(words, 1), 3),
                         tmatch=round(title_match(t, a, c['title']), 2),
                         perf=is_perf(c['title']), ok=(sc is not None)))
        if sc is not None and (best is None or sc < best[0]):
            best = (sc, c)
    return {'title': t, 'author': a, 'words': words, 'file': b['file'],
            'pick': best[1] if best else None, 'candidates': rows}

def main():
    books = json.load(open(sys.argv[1], encoding='utf-8'))
    done = {}
    if os.path.exists(OUT):
        done = {r['file']: r for r in json.load(open(OUT, encoding='utf-8'))}
    results = list(done.values())
    todo = [b for b in books if b['file'] not in done]
    print('%d plays to search\n' % len(todo), flush=True)
    for i, b in enumerate(todo):
        print('[%d/%d] %s' % (i + 1, len(todo), b['title']), flush=True)
        r = hunt(b)
        results.append(r)
        json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        p = r['pick']
        print('     %s' % (('PICK %s  %dm  %.2f s/w  %s' % (
              p['id'], p['dur'] // 60, p['dur'] / max(b['words'], 1), p['title'][:52]))
              if p else 'nothing (%d probed)' % len(r['candidates'])), flush=True)
    print('\ndone — %d of %d have a performance' %
          (sum(1 for r in results if r['pick']), len(results)))

if __name__ == '__main__':
    main()
