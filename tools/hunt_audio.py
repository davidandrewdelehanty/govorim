#!/usr/bin/env python3
# Screen YouTube for a readable recording of every book that has none.
#
# For each book: search a few phrasings, then extract each candidate to learn
# three things a title cannot tell you —
#   * playable_in_embed, because a video the site cannot embed is no use;
#   * whether the ORIGINAL captions are Russian ('ru-orig'), not merely that a
#     Russian track exists — YouTube auto-translates into dozens of languages,
#     so a bare 'ru' can mean an English recording with translated subtitles;
#   * duration against the book's own word count, which is what separates a
#     complete reading from an abridgement or a discussion about the book.
# The pick is the captioned, embeddable candidate whose seconds-per-word lands
# closest to 0.55 — this library's measured narration rate — inside a band wide
# enough for slow and brisk readers but not for a podcast.
#
# Nothing is placed here. Captions are pulled for the picks; sync_all.py and
# its gates decide afterwards what is actually good enough to ship.
import json, subprocess, sys, os, time

RATE_LO, RATE_HI, RATE_IDEAL = 0.38, 0.85, 0.55
SEARCH_N = 20
OUT = 'tools/hunt-results.json'

def yt(args, timeout=120):
    try:
        r = subprocess.run(['yt-dlp'] + args, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except Exception:
        return ''

def search(q, n=SEARCH_N):
    out = yt(['--skip-download', '--flat-playlist', '-J', 'ytsearch%d:%s' % (n, q)])
    try:
        d = json.loads(out)
    except Exception:
        return []
    return [e for e in (d.get('entries') or []) if e and e.get('id')]

def norm_t(s):
    """Lowercase, ё→е, letters and digits only — for comparing titles."""
    s = (s or '').lower().replace('ё', 'е')
    return [w for w in ''.join(c if c.isalnum() else ' ' for c in s).split() if len(w) > 2]

def title_match(book_title, author, video_title):
    """Does this video claim to be this book?

    The screen that was missing: duration, captions and embeddability say a
    video is USABLE, never that it is the right work. Without this, Мелкий бес
    was matched to a reading of the Thousand and One Nights that happened to be
    the right length and carry Russian captions.
    """
    want = norm_t(book_title)
    if not want:
        return 0.0
    got = set(norm_t(video_title))
    hit = sum(1 for w in want if w in got)
    frac = hit / len(want)
    # A one-word title ("Мать", "Новь") is a common word and matches by
    # accident, so it must be carried by the author's name as well.
    if len(want) == 1 and author and norm_t(author) and norm_t(author)[0] not in got:
        return frac * 0.5
    return frac

def probe(vid):
    out = yt(['--skip-download', '-J', 'https://www.youtube.com/watch?v=' + vid], timeout=90)
    try:
        j = json.loads(out)
    except Exception:
        return None
    if not isinstance(j, dict):      # yt-dlp prints "null" when extraction fails
        return None
    ac = j.get('automatic_captions') or {}
    subs = j.get('subtitles') or {}
    return {
        'id': vid,
        'dur': j.get('duration') or 0,
        'embed': bool(j.get('playable_in_embed')),
        # 'ru-orig' is the original transcription; a bare 'ru' may be translated.
        'ru_orig': ('ru-orig' in ac) or ('ru' in subs),
        'title': (j.get('title') or '')[:90],
    }

TITLE_FLOOR = 0.8

def score(c, words, book_title, author):
    if not c or not c['embed'] or not c['ru_orig'] or not c['dur']:
        return None
    if title_match(book_title, author, c['title']) < TITLE_FLOOR:
        return None
    r = c['dur'] / max(words, 1)
    if r < RATE_LO or r > RATE_HI:
        return None
    return abs(r - RATE_IDEAL)

def hunt(title, author, words, queries):
    seen, cands = set(), []
    for q in queries:
        for e in search(q):
            if e['id'] in seen:
                continue
            seen.add(e['id'])
            d = e.get('duration') or 0
            # Skip what cannot possibly be a reading of this text.
            if d < words * RATE_LO * 0.5 or d > words * RATE_HI * 2.5:
                continue
            cands.append(e['id'])
    best, rows = None, []
    for vid in cands[:14]:
        c = probe(vid)
        if not c:
            continue
        sc = score(c, words, title, author)
        rows.append(dict(c, rate=round(c['dur'] / max(words, 1), 3),
                         tmatch=round(title_match(title, author, c['title']), 2),
                         ok=(sc is not None)))
        if sc is not None and (best is None or sc < best[0]):
            best = (sc, c)
    return {'title': title, 'author': author, 'words': words,
            'pick': best[1] if best else None, 'candidates': rows}

def main():
    books = json.load(open(sys.argv[1], encoding='utf-8'))
    done = {}
    if os.path.exists(OUT):
        done = {r['file']: r for r in json.load(open(OUT, encoding='utf-8'))}
    results = list(done.values())
    for i, b in enumerate(books):
        if b['file'] in done:
            continue
        qs = ['%s %s аудиокнига' % (b['author_short'], b['title']),
              '%s читает' % b['title'],
              '%s аудиокнига полностью' % b['title']]
        print('[%d/%d] %s' % (i + 1, len(books), b['title']), flush=True)
        r = hunt(b['title'], b['author_short'], b['words'], qs)
        r['file'] = b['file']
        results.append(r)
        json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        p = r['pick']
        print('     %s' % (('PICK %s  %dm  %.2f s/w  %s' % (
              p['id'], p['dur'] // 60, p['dur'] / max(b['words'], 1), p['title'][:50]))
              if p else 'no captioned candidate (%d probed)' % len(r['candidates'])), flush=True)
    print('\ndone — %d books, %d with a pick' % (len(results), sum(1 for r in results if r['pick'])))

if __name__ == '__main__':
    main()
