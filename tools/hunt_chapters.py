#!/usr/bin/env python3
# Find chapter-by-chapter readings for the books nothing else could place.
#
# Two strategies, because the shape of a multi-part reading on YouTube varies:
#
#   A. A real playlist. Searched through YouTube's playlist-filtered results.
#
#   B. A channel that uploaded the chapters as separate videos and never made
#      a playlist — or made one the search will not surface. These are found by
#      searching for the chapters themselves ("<book> глава", "<book> часть"),
#      grouping the hits by uploader, and keeping any group of three or more
#      whose titles carry the book's name and a chapter number. Ordering comes
#      from the numbers in the titles, and is only a first guess: placement
#      re-derives the true order from the transcripts, so a mislabelled part
#      is corrected rather than believed.
#
# Either way the group is accepted only if its total running time divided by
# the book's word count lands in a plausible narration band, and the first
# part carries an original Russian transcript.
import json, re, subprocess, sys, os

RATE_LO, RATE_HI = 0.38, 0.85
DEFAULT_OUT = 'tools/hunt-chapters.json'

def yt(args, timeout=180):
    try:
        return subprocess.run(['yt-dlp'] + args, capture_output=True, text=True,
                              timeout=timeout).stdout
    except Exception:
        return ''

def jload(s):
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else None
    except Exception:
        return None

def norm_t(s):
    s = (s or '').lower().replace('ё', 'е')
    return [w for w in ''.join(c if c.isalnum() else ' ' for c in s).split() if len(w) > 2]

def title_match(book_title, author, cand):
    want = norm_t(book_title)
    if not want: return 0.0
    got = set(norm_t(cand))
    frac = sum(1 for w in want if w in got) / len(want)
    if len(want) == 1 and author and norm_t(author) and norm_t(author)[0] not in got:
        return frac * 0.5
    return frac

NUM = re.compile(r'(?:глава|часть|ч\.|гл\.|part|chapter)\s*[№#]?\s*(\d{1,3})', re.I)
def part_no(title):
    m = NUM.search(title or '')
    if m: return int(m.group(1))
    m = re.search(r'\b(\d{1,3})\s*(?:глава|часть)', title or '', re.I)
    return int(m.group(1)) if m else None

def probe(vid):
    j = jload(yt(['--skip-download', '-J', 'https://www.youtube.com/watch?v=' + vid], 90))
    if not j: return None
    ac = j.get('automatic_captions') or {}
    return {'embed': bool(j.get('playable_in_embed')),
            'ru_orig': ('ru-orig' in ac) or ('ru' in (j.get('subtitles') or {}))}

# ── strategy A: a real playlist ───────────────────────────────────────────────
def playlist_search(q, n=12):
    url = ('https://www.youtube.com/results?search_query=%s&sp=EgIQAw%%3D%%3D'
           % q.replace(' ', '+'))
    d = jload(yt(['--skip-download', '--flat-playlist', '--playlist-end', str(n), '-J', url]))
    out = []
    for e in ((d or {}).get('entries') or []):
        if not e: continue
        pid = e.get('id') or ''
        if e.get('_type') == 'playlist' or pid.startswith('PL') or pid.startswith('OLAK'):
            out.append({'id': pid, 'title': e.get('title') or ''})
    return out

def playlist_detail(pid):
    d = jload(yt(['--skip-download', '--flat-playlist', '-J',
                  'https://www.youtube.com/playlist?list=' + pid]))
    if not d: return None
    ents = [e for e in (d.get('entries') or []) if e and e.get('id')]
    if not ents: return None
    return {'kind': 'playlist', 'id': pid, 'title': d.get('title') or '',
            'n': len(ents), 'total': sum((e.get('duration') or 0) for e in ents),
            'videos': [{'id': e['id'], 'dur': e.get('duration') or 0,
                        'title': (e.get('title') or '')[:90]} for e in ents]}

# ── strategy B: loose chapters from one channel ───────────────────────────────
def video_search(q, n=25):
    d = jload(yt(['--skip-download', '--flat-playlist', '-J', 'ytsearch%d:%s' % (n, q)]))
    return [e for e in ((d or {}).get('entries') or []) if e and e.get('id')]

def loose_chapters(title, author, queries):
    by_ch = {}
    for q in queries:
        for e in video_search(q):
            t = e.get('title') or ''
            if title_match(title, author, t) < 0.8: continue
            no = part_no(t)
            if no is None: continue
            ch = e.get('channel') or e.get('uploader') or '?'
            by_ch.setdefault(ch, {})[no] = {
                'id': e['id'], 'dur': e.get('duration') or 0, 'title': t[:90]}
    best = None
    for ch, parts in by_ch.items():
        if len(parts) < 3: continue
        vids = [parts[k] for k in sorted(parts)]
        total = sum(v['dur'] for v in vids)
        cand = {'kind': 'loose', 'id': ch, 'title': ch, 'n': len(vids),
                'total': total, 'videos': vids, 'numbers': sorted(parts)}
        if best is None or cand['n'] > best['n']:
            best = cand
    return best

def hunt(book):
    title, author, words = book['title'], book['author_short'], book['words']
    qs = ['%s %s аудиокнига' % (author, title), '%s аудиокнига по главам' % title,
          '%s читает часть 1' % title]
    cands, seen = [], set()
    for q in qs:
        for pl in playlist_search(q):
            if not pl['id'] or pl['id'] in seen: continue
            seen.add(pl['id'])
            if title_match(title, author, pl['title']) < 0.6: continue
            d = playlist_detail(pl['id'])
            if d and d['n'] >= 2: cands.append(d)
    loose = loose_chapters(title, author,
                           ['%s глава' % title, '%s часть' % title,
                            '%s %s глава' % (author, title)])
    if loose: cands.append(loose)
    best = None
    for d in cands:
        if not d['total']: continue
        rate = d['total'] / max(words, 1)
        if rate < RATE_LO or rate > RATE_HI: continue
        c = probe(d['videos'][0]['id'])
        if not c or not c['embed'] or not c['ru_orig']: continue
        d['rate'] = round(rate, 3)
        if best is None or abs(rate - 0.55) < abs(best['rate'] - 0.55):
            best = d
    return best

def main():
    books = json.load(open(sys.argv[1], encoding='utf-8'))
    results_file = sys.argv[2] if len(sys.argv) > 2 else 'tools/hunt-results.json'
    out_file = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_OUT
    skip = set()
    if os.path.exists(results_file):
        for r in json.load(open(results_file, encoding='utf-8')):
            if r.get('pick'): skip.add(r['file'])
    done = {}
    if os.path.exists(out_file):
        done = {r['file']: r for r in json.load(open(out_file, encoding='utf-8'))}
    todo = [b for b in books if b['file'] not in skip and b['file'] not in done]
    print('%d books to try\n' % len(todo), flush=True)
    results = list(done.values())
    for i, b in enumerate(todo):
        print('[%d/%d] %s (%d words)' % (i + 1, len(todo), b['title'], b['words']), flush=True)
        pl = hunt(b)
        results.append({'file': b['file'], 'title': b['title'], 'words': b['words'], 'playlist': pl})
        json.dump(results, open(out_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('     %s' % (('%s %s  %d parts  %.1fh  %.2f s/w  %s'
              % (pl['kind'].upper(), pl['id'][:24], pl['n'], pl['total']/3600, pl['rate'],
                 pl['title'][:38])) if pl else 'nothing'), flush=True)
    print('\ndone — %d found' % sum(1 for r in results if r.get('playlist')))

if __name__ == '__main__':
    main()
