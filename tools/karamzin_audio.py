#!/usr/bin/env python3
"""Find YouTube readings for Карамзин, «История государства Российского»,
fetch their Russian transcripts, map every chapter, and build the jump points.

The work is one book on the shelf but no one reads it in one sitting, so the
search is per volume: for each Том it looks for a playlist (one video per
chapter or per part) and for single long videos, keeps the captioned,
embeddable candidate whose length fits the volume's word count, pulls its
transcripts, and finds each chapter's opening line in them — in order, the
same test place_playlists.py applies. A volume whose recording does not hold
up is left without audio rather than mapped wrongly.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/karamzin_audio.py --hunt     # search only; writes tools/karamzin-audio.json
    python3 tools/karamzin_audio.py            # search (cached), transcripts, map, jump points

Needs yt-dlp and the network, so it runs in WSL. Re-running is safe: the
search results and transcripts are cached.
"""
import io, json, os, re, subprocess, sys, statistics
sys.path.insert(0, 'tools')
from hunt_playlists import playlist_search, playlist_detail, probe_one, yt, jload
from place_playlists import stream, locate
from scan_alignment import chapters as fb2_chapters

BOOK = 'public/books/novel/karamzin-igr.fb2'
SLUG = 'karamzin-igr'
OUT = 'tools/karamzin-audio.json'
VTT = 'tools/vtt'
RATE_LO, RATE_HI, IDEAL = 0.38, 0.90, 0.55
ROM = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']


def volumes():
    """[(roman, arabic, [global chapter indexes])] from the FB2's own parts."""
    t = io.open(BOOK, encoding='utf-8').read()
    body = t[t.index('<body>'):]
    out, ci = [], 0
    for m in re.finditer(r'<section><title><p>Том ([IVX]+)</p></title>([\s\S]*?)\n</section>\n(?=<section><title><p>Том|</body>)', body):
        n = len(re.findall(r'<section>', m.group(2)))
        out.append((m.group(1), ROM.index(m.group(1)) + 1, list(range(ci, ci + n))))
        ci += n
    return out


def vol_match(title, r, n):
    t = (title or '').lower().replace('ё', 'е')
    if 'государства российского' not in t and 'карамзин' not in t:
        return False
    pats = [r'\bтом\s*%d\b' % n, r'\bтом\s*%s\b' % r.lower(), r'\b%d\s*том' % n, r'\bт\.\s*%d\b' % n]
    return any(re.search(p, t) for p in pats)


def search_videos(q, n=15):
    d = jload(yt(['--skip-download', '--flat-playlist', '-J', 'ytsearch%d:%s' % (n, q)]))
    return [e for e in ((d or {}).get('entries') or []) if e and e.get('id')]


def hunt(r, n, words):
    qs = ['Карамзин История государства Российского том %d аудиокнига' % n,
          'История государства Российского том %s Карамзин' % r,
          'Карамзин том %d аудиокнига' % n]
    cands, seen = [], set()
    for q in qs:
        for pl in playlist_search(q):
            if pl['id'] in seen or not vol_match(pl['title'], r, n):
                continue
            seen.add(pl['id'])
            d = playlist_detail(pl['id'])
            if not d or not d['total']:
                continue
            rate = d['total'] / max(words, 1)
            if RATE_LO <= rate <= RATE_HI:
                cands.append({'kind': 'playlist', 'id': d['id'], 'title': d['title'], 'rate': round(rate, 3),
                              'videos': [v['id'] for v in d['videos']], 'probe': d['first']})
        for e in search_videos(q):
            if e['id'] in seen or not vol_match(e.get('title'), r, n):
                continue
            seen.add(e['id'])
            rate = (e.get('duration') or 0) / max(words, 1)
            if RATE_LO <= rate <= RATE_HI:
                cands.append({'kind': 'video', 'id': e['id'], 'title': e.get('title') or '', 'rate': round(rate, 3),
                              'videos': [e['id']], 'probe': e['id']})
    # One video per volume beats a playlist: the reader plays one video per
    # chapter, and a playlist cut every twenty minutes splits most chapters
    # across two parts, so only their first part could ever play.
    cands.sort(key=lambda c: (c['kind'] != 'video', abs(c['rate'] - IDEAL)))
    for c in cands:
        p = probe_one(c['probe'])
        if p and p['embed'] and p['ru_orig']:
            return c
    return None


def fetch_vtt(vid):
    dest = os.path.join(VTT, vid + '.ru.vtt')
    if not os.path.exists(dest):
        subprocess.call(['yt-dlp', '--write-auto-sub', '--sub-lang', 'ru', '--skip-download', '--quiet',
                         '--no-warnings', '-o', os.path.join(VTT, '%(id)s'), 'https://youtu.be/' + vid])
    return os.path.exists(dest)


def main():
    hunt_only = '--hunt' in sys.argv
    chs = fb2_chapters(BOOK)
    vols = volumes()
    if sum(len(v[2]) for v in vols) != len(chs):
        sys.exit('chapter count mismatch: parts say %d, reader says %d' % (sum(len(v[2]) for v in vols), len(chs)))
    found = json.load(io.open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    for r, n, idxs in vols:
        words = sum(len(' '.join(chs[i]).split()) for i in idxs)
        if found.get(r) and found[r].get('kind') == 'playlist' and not found[r].get('rehunted'):
            del found[r]          # searched before single videos were preferred
        if r not in found:
            print('Том %-4s %6d words  searching…' % (r, words), flush=True)
            found[r] = hunt(r, n, words)
            if found[r]: found[r]['rehunted'] = True
            json.dump(found, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        c = found[r]
        print('Том %-4s %s' % (r, ('%s %s  %d part(s)  %.2f s/w  %s' % (c['kind'], c['id'], len(c['videos']), c['rate'], c['title'][:50]))
                                if c else 'nothing usable'), flush=True)
    if hunt_only:
        return
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    entry = next(b for b in idx if b.get('slug') == SLUG)
    vmap = {}
    for r, n, idxs in vols:
        c = found.get(r)
        if not c:
            continue
        have = [v for v in c['videos'] if fetch_vtt(v)]
        if not have:
            print('Том %-4s no transcripts came down' % r); continue
        vids = c['videos']
        toks, ends = stream(vids)
        sub = [chs[i] for i in idxs]
        hits = locate(sub, toks)
        ok = [h for h in hits if h[0] is not None]
        med = statistics.median([h[2] for h in ok]) if ok else 0
        if len(ok) < 0.85 * len(sub) or med < 0.70:
            print('Том %-4s REFUSED — %d/%d chapters found, median %.2f' % (r, len(ok), len(sub), med)); continue
        placed, split = 0, []
        for k, (pk, sec, sc) in enumerate(hits):
            if pk is None:
                continue
            nxt = next((h for h in hits[k + 1:] if h[0] is not None), None)
            end = nxt[1] if (nxt and nxt[0] == pk) else ends[pk]
            if nxt and nxt[0] != pk:
                # The chapter runs on into the next part. If much of it is
                # there, leave it unmapped rather than play half a chapter.
                spill = nxt[1] if nxt[0] == pk + 1 else sum(ends[pk + 1:nxt[0]]) + nxt[1]
                heard = max(0, end - sec)
                if heard + spill > 0 and spill / (heard + spill) > 0.25:
                    split.append(k + 1); continue
            x = {'youtube': vids[pk], 'heading': 'Том %s, глава %d' % (r, k + 1), 'start': int(sec), 'end': int(end)}
            if x['start'] == 0:
                del x['start']
            vmap[str(idxs[k])] = x
            placed += 1
        print('Том %-4s placed %d/%d chapters, median match %.2f%s' % (r, placed, len(sub), med,
              ('  (left out, split across parts: глава %s)' % ', '.join(map(str, split))) if split else ''))
    if vmap:
        entry['videos'] = vmap
        io.open('private/books/index.json', 'w', encoding='utf-8').write(json.dumps(idx, ensure_ascii=False, indent=2) + '\n')
        import sync_all
        print('jump points:', sync_all.run(entry))
    print('\n%d of %d chapters have a recording.' % (len(vmap), len(chs)))


if __name__ == '__main__':
    main()
