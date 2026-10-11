#!/usr/bin/env python3
"""Recordings and jump points for the rest of the Synodal Bible.

The entry's own videos cover the five books of Moses and the four Gospels —
one long reading per book, with the creator's chapter timestamps. Everything
else comes from the «Библия Онлайн» channel (tools/bible-channel.json), which
keeps one playlist per book and one video per chapter, read from the Synodal
text. Books it has no playlist for (the deuterocanonical ones, Даниил,
Екклесиаст) simply have no recording.

    python3 tools/bible_videos.py --ids      # video ids still needing captions
    python3 tools/bible_videos.py            # dry run: what would be added
    python3 tools/bible_videos.py --write    # add the videos, then rebuild every
                                             # chapter's jump points (sync_all)

Run tools/bible_fetch.sh first (WSL — it needs YouTube): it lists the
playlists into tools/bible-pl/ and downloads the Russian captions into
tools/vtt/, which is all this needs.
"""
import glob, io, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
INDEX = 'private/books/index.json'
FB2 = 'public/books/novel/bible-synodal.fb2'
SLUG = 'bibliya-sinodalnyy-perevod'

ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}
NEUT = {'Царств', 'Паралипоменон'}          # «1-я Царств»; epistles take «1-е»
RENAME = {'Ездра': '1-я Ездры', 'Неемия': 'Неемии', 'Песни Песней': 'Песнь песней',
          'Песнь Песней': 'Песнь песней'}

def book_name(pl_title):
    # Some titles spell «й» as и + a combining breve, which looks the same and
    # matches nothing: «Филиппийцам» and both Thessalonians were missed so.
    t = unicodedata.normalize('NFC', pl_title or '')
    t = re.sub(r'\(.*$', '', t).strip()
    t = re.sub(r'\s+', ' ', t)
    m = re.match(r'^(I{1,3}|IV)\s+(.+)$', t)
    if m:
        n, rest = ROMAN[m.group(1)], m.group(2)
        return ('%d-я %s' if rest in NEUT else '%d-е %s') % (n, rest)
    return RENAME.get(t, t)

def chapter_no(title):
    for rx in (r'(\d+)\s*глав', r'[Cc]hapter\s*(\d+)', r'[Пп]сал[оа]м\s*(\d+)', r'(\d+)\s*\(', r'(\d+)\s*$'):
        m = re.search(rx, title)
        if m: return int(m.group(1))
    return None

def headings():
    s = io.open(FB2, encoding='utf-8').read()
    return [h.strip() for h in re.findall(r'<section>\s*<title><p>(.*?)</p></title>', s)]

def proposals():
    hs = headings()
    hidx = {h: i for i, h in enumerate(hs)}
    out, unknown = {}, set()
    for f in sorted(glob.glob('tools/bible-pl/*.json')):
        try: pl = json.load(io.open(f, encoding='utf-8'))
        except Exception: continue
        book = book_name(pl.get('title') or '')
        if book.isupper(): book = book[:1] + book[1:].lower()      # «БЫТИЕ»
        for e in pl.get('entries') or []:
            n = chapter_no(e.get('title') or '')
            if not n or not e.get('id'): continue
            h = '%s %d' % (book, n)
            if h not in hidx: unknown.add(book); continue
            out.setdefault(hidx[h], {'youtube': e['id'], 'heading': h, 'start': 0,
                                     'source': 'Библия Онлайн'})
    return out, unknown, len(hs)

def entry_of(d):
    for b in d:
        if b.get('slug') == SLUG: return b
    raise SystemExit('Synodal entry not found')

if __name__ == '__main__':
    d = json.load(io.open(INDEX, encoding='utf-8'))
    b = entry_of(d)
    have = b.get('videos') or {}
    prop, unknown, total = proposals()
    new = {k: v for k, v in prop.items() if str(k) not in have}
    if '--ids' in sys.argv:
        # New chapters, and any chapter already in the catalogue whose
        # captions never arrived (a download that failed last time).
        ids = [new[k]['youtube'] for k in sorted(new)]
        for k in sorted(have, key=int):
            v = have[k].get('youtube')
            if v and v not in ids and not os.path.exists('tools/vtt/%s.ru.vtt' % v): ids.append(v)
        for v in ids: print(v)
        sys.exit(0)
    print('chapters %d · with a video already %d · new from the channel %d' % (total, len(have), len(new)))
    if unknown: print('playlists whose book name did not match a heading:', ', '.join(sorted(unknown)))
    missing_vtt = [v['youtube'] for v in new.values() if not os.path.exists('tools/vtt/%s.ru.vtt' % v['youtube'])]
    print('still without captions: %d' % len(missing_vtt))
    if '--write' not in sys.argv:
        sys.exit(0)
    vids = dict(have)
    for k, v in new.items(): vids[str(k)] = v
    b['videos'] = dict(sorted(vids.items(), key=lambda x: int(x[0])))
    io.open(INDEX, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    print('videos now %d' % len(b['videos']))
    import sync_all
    print(sync_all.run(b))
