# Build paragraph->seconds maps for every book whose chapters carry a YouTube
# video and whose video has a Russian transcript on disk (tools/vtt/<id>.ru.vtt).
#
# Chapters come from scan_alignment.chapters(), which mirrors walkSection in
# App.jsx — the same splitting the reader performs — so paragraph indices line
# up with entry.chIdx, which is what the buttons key on. Where a book ships a
# parallel English folder, its files are keyed by that same index, so their
# highest key + 1 is an independent check on the paragraph count: if those
# disagree the map would be pointing at the wrong paragraphs and the book is
# skipped rather than shipped wrong.
import re, io, json, os, sys
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters
from para_sync import align_chapter
from vtt_tokens import load

VTT = 'tools/vtt/%s.ru.vtt'
OUT = 'public/books/audio-sync/%s'
_cache = {}

def toks_for(vid):
    if vid not in _cache:
        p = VTT % vid
        _cache[vid] = load(p) if os.path.exists(p) else None
    return _cache[vid]

def en_para_count(entry, cidx):
    """Highest English key + 1 for this chapter, or None."""
    d = entry.get('parallelEn')
    if not d: return None
    p = 'public/books/%s/%02d.json' % (d, cidx + 1)
    if not os.path.exists(p): return None
    try:
        m = json.load(io.open(p, encoding='utf-8'))
        ks = [int(k) for k in m if k.lstrip('-').isdigit()]
        return (max(ks) + 1) if ks else None
    except Exception:
        return None

def run(entry, verbose=True):
    fn = entry.get('filename')
    path = 'public/books/' + fn
    if not os.path.exists(path):
        path = 'private/books/' + fn
        if not os.path.exists(path): return None
    base = os.path.basename(fn).rsplit('.', 1)[0]
    try:
        chs = fb2_chapters(path)
    except Exception as e:
        return {'book': base, 'error': 'parse: %s' % e}
    if not chs: return {'book': base, 'error': 'no chapters'}
    vids = entry.get('videos') or {}
    made, skipped, notrans, mismatch = 0, 0, 0, 0
    rates = []
    os.makedirs(OUT % base, exist_ok=True)
    for k in sorted(vids, key=int):
        c = int(k)
        if c >= len(chs):
            skipped += 1; continue
        v = vids[k]; vid = v.get('youtube')
        t = toks_for(vid) if vid else None
        if not t: notrans += 1; continue
        paras = chs[c]
        enc = en_para_count(entry, c)
        if enc is not None and abs(enc - len(paras)) > 1:
            mismatch += 1; continue
        m, anchored, total = align_chapter(paras, t, v.get('start', 0), v.get('end', 0))
        if not m: skipped += 1; continue
        ts = [m[x] for x in sorted(m, key=int)]
        if any(a > b for a, b in zip(ts, ts[1:])):
            skipped += 1; continue          # never ship a map that runs backwards
        # A map that anchored almost nothing is proportional guesswork wearing
        # a transcript's clothes: every button would land plausibly and none
        # would land right. Plays fail here honestly — a one-line retort has
        # too few words to match on — and they are better left without buttons
        # than given ones that miss.
        if anchored * 100 // max(total, 1) < 25:
            skipped += 1; continue
        json.dump(m, io.open((OUT % base) + '/%02d.json' % c, 'w', encoding='utf-8'))
        made += 1
        rates.append(100 * anchored // max(total, 1))
    if not made:
        try: os.rmdir(OUT % base)
        except Exception: pass
    med = sorted(rates)[len(rates)//2] if rates else 0
    return {'book': base, 'chapters': made, 'no_transcript': notrans,
            'mismatch': mismatch, 'skipped': skipped, 'median_anchor': med}
