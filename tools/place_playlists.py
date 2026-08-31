#!/usr/bin/env python3
# Place a multi-part reading: find each chapter across the parts, in order.
#
# A playlist's part numbers say nothing reliable — Фивейский's ran 1-8, 10, 11,
# 12 for a book of thirteen chapters, and one of its parts held no chapter
# opening at all because it continued the one before. So the parts are read as
# one long recording laid end to end: chapters are searched in sequence through
# the concatenated transcripts, and each is placed in whichever part it turns
# out to begin in.
#
# A chapter that starts in one part and finishes in the next gets no map, and
# is reported: the window would hold only its first half, and the aligner would
# squeeze the whole chapter into it so that every button landed early.
import json, io, os, sys, difflib, statistics
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters
from vtt_tokens import load, norm

MIN_MEDIAN_SCORE, MIN_FOUND_FRAC = 0.70, 0.85
RATE_LO, RATE_HI = 0.35, 0.90

def stream(vids):
    """Every part's transcript, concatenated, each token tagged with its part."""
    toks, ends = [], []
    for k, v in enumerate(vids):
        p = 'tools/vtt/%s.ru.vtt' % v
        if not os.path.exists(p):
            ends.append(0); continue
        t = load(p)
        ends.append(t[-1][0] if t else 0)
        for sec, w in t:
            toks.append((k, sec, w))
    return toks, ends

def locate(chs, toks):
    words = [norm(w) for _, _, w in toks]
    where = {}
    for i, w in enumerate(words):
        if w: where.setdefault(w, []).append(i)
    out, cur = [], 0
    for c in chs:
        best = (0.0, None, 0)
        probes = []
        for para in c[:6]:
            pw = [x for x in (norm(y) for y in para.split()) if x]
            if len(pw) >= 8: probes.append(pw[:14])
            if len(probes) >= 4: break
        for op in probes:
            cands = set()
            for k in range(min(3, len(op))):
                for j in where.get(op[k], ()):
                    if j - k >= cur: cands.add(j - k)
            for j in sorted(cands):
                if j + len(op) > len(words): continue
                r = difflib.SequenceMatcher(None, words[j:j+len(op)], op).ratio()
                if r > best[0]:
                    best = (r, j, len(op))
                    if r > 0.97: break
            if best[0] >= 0.8: break
        if best[1] is not None and best[0] >= 0.55:
            out.append((toks[best[1]][0], toks[best[1]][1], best[0]))   # part, sec, score
            cur = best[1] + best[2]
        else:
            out.append((None, None, best[0]))
    return out

def run(entry, vids, apply_it=True):
    fn = entry['filename']
    path = 'public/books/' + fn
    if not os.path.exists(path): path = 'private/books/' + fn
    chs = fb2_chapters(path)
    toks, ends = stream(vids)
    if not toks: return {'ok': False, 'why': 'no transcripts'}
    found = locate(chs, toks)
    hits = [f for f in found if f[0] is not None]
    frac = len(hits) / len(chs)
    med = statistics.median([f[2] for f in hits]) if hits else 0
    if frac < MIN_FOUND_FRAC:
        return {'ok': False, 'why': 'only %d/%d chapters found' % (len(hits), len(chs))}
    if med < MIN_MEDIAN_SCORE:
        return {'ok': False, 'why': 'weak matches (median %.2f)' % med}
    # Each chapter runs to the next chapter's start when they share a part, or
    # to the end of its own part when they do not.
    vids_out, split = {}, []
    rates = []
    for i, (pk, sec, sc) in enumerate(found):
        if pk is None: continue
        nxt = next((f for f in found[i+1:] if f[0] is not None), None)
        if nxt and nxt[0] == pk:
            end = nxt[1]
        else:
            end = ends[pk]
            # The next chapter begins in a later part. Usually that means the
            # parts are cut at the chapters and this one bleeds a second or two
            # past the join — Яма loses a median of nothing that way. But when
            # the cut falls mid-chapter the tail is genuinely unreachable, and
            # a chapter that would play only its first half is worse than one
            # that plays nothing, because the reader cannot tell it is missing.
            if nxt:
                spill = nxt[1] if nxt[0] == pk + 1 else sum(ends[pk+1:nxt[0]]) + nxt[1]
                heard = max(0, end - sec)
                if heard + spill > 0 and spill / (heard + spill) > 0.25:
                    split.append(i)
                    continue
        w = max(1, len(' '.join(chs[i]).split()))
        if end > sec: rates.append((end - sec) / w)
        x = {'youtube': vids[pk], 'heading': 'Глава %d' % (i+1),
             'start': int(sec), 'end': int(end)}
        if x['start'] == 0: del x['start']
        vids_out[str(i)] = x
    rmed = statistics.median(rates) if rates else 0
    if rmed < RATE_LO or rmed > RATE_HI:
        return {'ok': False, 'why': 'rate %.2f s/w out of band' % rmed}
    if apply_it: entry['videos'] = vids_out
    return {'ok': True, 'chapters': len(vids_out), 'total': len(chs),
            'med': round(med, 2), 'rate': round(rmed, 3), 'split': split}

def main():
    # A later pass writes its finds to its own file; point at it with HUNT_PL
    # rather than overwriting pass one's results.
    src = os.environ.get('HUNT_PL', 'tools/hunt-playlists.json')
    pls = [r for r in json.load(io.open(src, encoding='utf-8')) if r.get('playlist')]
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    by = {b['filename']: b for b in idx}
    a = int(sys.argv[1]) if len(sys.argv) > 2 else 0
    z = int(sys.argv[2]) if len(sys.argv) > 2 else len(pls)
    for r in pls[a:z]:
        e = by.get(r['file'])
        if not e: continue
        vids = [v['id'] for v in r['playlist']['videos']]
        res = run(e, vids)
        name = (e.get('title') or '')[:30]
        if res['ok']:
            print('%-30s %d/%d chapters  match %.2f  %.3f s/w  dropped (cut mid-chapter): %s'
                  % (name, res['chapters'], res['total'], res['med'], res['rate'],
                     [x+1 for x in res['split']] or 'none'), flush=True)
        else:
            print('%-30s REFUSED — %s' % (name, res['why']), flush=True)
    io.open('private/books/index.json', 'w', encoding='utf-8').write(
        json.dumps(idx, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    main()
