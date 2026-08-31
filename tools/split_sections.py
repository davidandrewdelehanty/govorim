#!/usr/bin/env python3
# Give a one-section FB2 the chapters its own text already declares.
#
# Six books in this library are a single <section> holding the whole novel —
# Дым is 1,261 paragraphs in one, Новь 2,559 — even though the chapter numbers
# are sitting right there in the text as paragraphs of their own. Nothing reads
# them, so the reader shows one endless page, one video covers the lot, and
# para_sync is asked to anchor two thousand paragraphs against a ten-hour
# transcript in a single pass. It anchors under a quarter of them and the book
# is refused. Split the same text into the chapters it names and every one of
# those problems is local instead of global.
#
# The edit is textual and surgical: </section><section> inserted before each
# marker paragraph, nothing removed, nothing reordered, encoding untouched.
# That matters because the paragraph sequence is the key the English is stored
# under — public/books/<x>-en/NN.json maps RUSSIAN paragraph index to English
# text — so dropping or moving a single <p> would shift every English line
# after it. The check below proves the sequence came through unchanged before
# anything is written.
import io, os, re, sys, json
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters

ROMAN = r'<p[^>]*>\s*(?:[IVXLC]{1,7}|\d{1,3})\s*\.?\s*</p>'
ACT   = r'<p[^>]*>\s*(?:ДЕЙСТВИЕ|Действие)\s+[^<]{0,20}</p>'

def read(path):
    raw = io.open(path, 'rb').read()
    m = re.match(rb'<\?xml[^>]*encoding=["\']([\w-]+)', raw[:200])
    enc = m.group(1).decode('ascii', 'ignore') if m else 'utf-8'
    try:
        return raw.decode(enc), enc
    except (UnicodeDecodeError, LookupError):
        return raw.decode('utf-8', 'replace'), 'utf-8'

def flat(path):
    chs = fb2_chapters(path)
    return [p for c in (chs or []) for p in c]

def split(path, pattern, dry=False):
    src, enc = read(path)
    if src.count('<section') != 1:
        return {'ok': False, 'why': '%d sections already' % src.count('<section')}
    before = flat(path)
    marks = [m for m in re.finditer(pattern, src)]
    # The first marker opens chapter two; whatever precedes it is chapter one.
    # A marker at the very top would make an empty section, so it is skipped.
    body = src.index('<section')
    marks = [m for m in marks if m.start() > body]
    if len(marks) < 2:
        return {'ok': False, 'why': 'only %d markers' % len(marks)}
    # Whatever precedes the first marker is front matter — an author line, a
    # title, a cast list. Given a section of its own it does not survive:
    # walk_section drops an untitled short section on purpose, and the reader's
    # walkSection does the same, so those paragraphs would vanish from both and
    # every English key after them would move. They belong to chapter one.
    cuts = [m.start() for m in marks[1:]]
    out, at = [], 0
    for c in cuts:
        out.append(src[at:c])
        out.append('</section>\n<section>\n')
        at = c
    out.append(src[at:])
    new = ''.join(out)
    # Scratch lives outside the repository: this shell cannot delete files,
    # so a check file written beside the book would stay there forever.
    tmp = os.path.join(os.environ.get('HOME', '/tmp'), '.split-check.fb2')
    io.open(tmp, 'w', encoding=enc).write(new)
    after = flat(tmp)
    nch = len(fb2_chapters(tmp) or [])
    same = (before == after)
    if not same or nch < 2:
        return {'ok': False, 'why': 'check failed — %d paras before, %d after, %d chapters'
                % (len(before), len(after), nch), 'tmp': tmp}
    if not dry:
        io.open(path, 'w', encoding=enc).write(new)
    return {'ok': True, 'chapters': nch, 'paras': len(before),
            'bounds': [len(c) for c in fb2_chapters(tmp)], 'tmp': tmp}

def split_english(endir, path):
    """Cut the single English file at the same paragraph boundaries.

    The keys are Russian paragraph indices with gaps where the printed text
    had none, so a chapter's English is exactly the keys inside its range,
    rebased to start at zero — no alignment, no guessing.
    """
    one = os.path.join('public/books', endir, '01.json')
    if not os.path.isdir(os.path.join('public/books', endir)):
        return 'no such folder'
    if len(os.listdir(os.path.join('public/books', endir))) != 1:
        return 'already split (%d files)' % len(os.listdir(os.path.join('public/books', endir)))
    en = json.load(io.open(one, encoding='utf-8'))
    note = en.pop('_note', None)
    chs = fb2_chapters(path)
    starts, n = [], 0
    for c in chs:
        starts.append(n); n += len(c)
    moved = 0
    for i, a in enumerate(starts):
        b = starts[i+1] if i + 1 < len(starts) else n
        part = {}
        for k, v in en.items():
            ki = int(k)
            if a <= ki < b:
                part[str(ki - a)] = v
        if note and i == 0: part['_note'] = note
        moved += len([k for k in part if k != '_note'])
        io.open(os.path.join('public/books', endir, '%02d.json' % (i + 1)),
                'w', encoding='utf-8').write(json.dumps(part, ensure_ascii=False, indent=1) + '\n')
    return 'split into %d files, %d of %d english paragraphs placed' % (len(starts), moved, len(en))

if __name__ == '__main__':
    path = sys.argv[1]
    pat = ACT if (len(sys.argv) > 2 and sys.argv[2] == 'act') else ROMAN
    endir = sys.argv[3] if len(sys.argv) > 3 else None
    r = split(path, pat, dry=('--dry' in sys.argv))
    print(os.path.basename(path), r)
    if r.get('ok') and endir and '--dry' not in sys.argv:
        print('   english:', split_english(endir, path))
