#!/usr/bin/env python3
# Second pass: find MULTI-PART readings for the books the single-video hunt
# could not place. A long novel is rarely uploaded as one file — Воскресшие
# боги is 181,000 words, a twenty-eight-hour reading — so the recordings that
# exist are playlists, which ytsearch never returns.
#
# YouTube's own results page can be filtered to playlists (sp=EgIQAw%3D%3D).
# If yt-dlp will not follow that, the fallback is to search for the first part
# by name ("часть 1") and take the playlist that video sits in.
import json, subprocess, sys, os

RATE_LO, RATE_HI = 0.38, 0.85
OUT = 'tools/hunt-playlists.json'

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

def playlist_search(q, n=12):
    """Playlists matching a query, via YouTube's playlist-filtered results."""
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
    total = sum((e.get('duration') or 0) for e in ents)
    return {'id': pid, 'title': d.get('title') or '', 'n': len(ents), 'total': total,
            'first': ents[0]['id'],
            'videos': [{'id': e['id'], 'dur': e.get('duration') or 0,
                        'title': (e.get('title') or '')[:80]} for e in ents]}

def probe_one(vid):
    j = jload(yt(['--skip-download', '-J', 'https://www.youtube.com/watch?v=' + vid], 90))
    if not j: return None
    ac = j.get('automatic_captions') or {}
    return {'embed': bool(j.get('playable_in_embed')),
            'ru_orig': ('ru-orig' in ac) or ('ru' in (j.get('subtitles') or {}))}

def hunt(book):
    title, author, words = book['title'], book['author_short'], book['words']
    qs = ['%s %s аудиокнига' % (author, title), '%s аудиокнига по главам' % title,
          '%s читает часть 1' % title]
    seen, best = set(), None
    for q in qs:
        for pl in playlist_search(q):
            if not pl['id'] or pl['id'] in seen: continue
            seen.add(pl['id'])
            if title_match(title, author, pl['title']) < 0.6: continue
            d = playlist_detail(pl['id'])
            if not d or d['n'] < 2 or not d['total']: continue
            rate = d['total'] / max(words, 1)
            if rate < RATE_LO or rate > RATE_HI: continue
            # Captions are checked on the first part; a channel that captions
            # one part almost always captions the rest, and the aligner will
            # skip any part that turns out to have none.
            c = probe_one(d['first'])
            if not c or not c['embed'] or not c['ru_orig']: continue
            d['rate'] = round(rate, 3)
            if best is None or abs(rate - 0.55) < abs(best['rate'] - 0.55):
                best = d
    return best

def main():
    books = json.load(open(sys.argv[1], encoding='utf-8'))
    # Only the ones the single-video pass could not place.
    skip = set()
    if os.path.exists('tools/hunt-results.json'):
        for r in json.load(open('tools/hunt-results.json', encoding='utf-8')):
            if r.get('pick'): skip.add(r['file'])
    done = {}
    if os.path.exists(OUT):
        done = {r['file']: r for r in json.load(open(OUT, encoding='utf-8'))}
    todo = [b for b in books if b['file'] not in skip and b['file'] not in done]
    print('%d books still without a recording\n' % len(todo), flush=True)
    results = list(done.values())
    for i, b in enumerate(todo):
        print('[%d/%d] %s (%d words)' % (i + 1, len(todo), b['title'], b['words']), flush=True)
        pl = hunt(b)
        results.append({'file': b['file'], 'title': b['title'], 'words': b['words'], 'playlist': pl})
        json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('     %s' % (('PLAYLIST %s  %d parts  %.1fh  %.2f s/w  %s'
              % (pl['id'], pl['n'], pl['total']/3600, pl['rate'], pl['title'][:44]))
              if pl else 'nothing'), flush=True)
    print('\ndone — %d with a playlist' % sum(1 for r in results if r.get('playlist')))

if __name__ == '__main__':
    main()
