#!/usr/bin/env python3
# Jump points for filmed stage productions (the спектакль entries), and the
# act boundaries that come with them.
#
# para_sync probes each paragraph's first ten words against the transcript
# and wants a 0.6 match. That works for a narrator reading the text as
# printed. A stage production is harder in three ways at once: the captions
# are machine-made from actors talking over each other, dialect and music;
# most speeches are a few words long; and productions cut lines. The probe
# then finds almost nothing — Власть тьмы anchored 0–17% per act.
#
# This aligns the WHOLE play against the WHOLE transcript instead, as two
# word sequences, and keeps the matching runs (difflib's matching blocks —
# monotonic by construction, so nothing can run backwards). A paragraph is
# placed only where enough of its own opening words sit in one of those runs:
# at least three of its first twelve spoken words, in order, inside a run the
# global alignment already committed to. Its time is the first such word's
# time, pulled back by the words before it. Paragraphs that do not meet that
# get no arrow, exactly as in para_sync.
#
# Acts: the first placed paragraph among an act's opening lines is a
# measurement of when the act begins; the boundary moves there when one is
# found, and each act then ends where the next begins.
import json, io, os, re, sys, difflib, bisect
sys.path.insert(0, 'tools')
from reader_chapters import reader_chapters
from para_sync import words_of, spoken
from vtt_tokens import load, norm

def align_play(chs, toks):
    tw = [norm(w) for _, w in toks]
    tt = [t for t, _ in toks]
    pw, owner = [], []          # play words, and (act, para, word-in-para) for each
    for ci, paras in enumerate(chs):
        for pi, p in enumerate(paras):
            ws = words_of(spoken(p))
            for k, w in enumerate(ws):
                pw.append(w); owner.append((ci, pi, k))
    sm = difflib.SequenceMatcher(None, pw, tw, autojunk=False)
    hit = {}                    # play word index -> transcript word index
    for a, b, n in sm.get_matching_blocks():
        for d in range(n):
            hit[a + d] = b + d
    placed = {}                 # (ci, pi) -> seconds
    first_word = {}
    for i, o in enumerate(owner):
        first_word.setdefault((o[0], o[1]), i)
    counts = {}
    for (ci, pi), i0 in first_word.items():
        ws = []
        j = i0
        while j < len(owner) and owner[j][0] == ci and owner[j][1] == pi and owner[j][2] < 12:
            if j in hit: ws.append(j)
            j += 1
        n_words = j - i0
        need = 3 if n_words >= 5 else max(2, n_words)
        if len(ws) >= need and n_words >= 2:
            k0 = owner[ws[0]][2]
            t = tt[hit[ws[0]]] - 0.35 * k0
            placed[(ci, pi)] = max(0, int(round(t)))
    # A short run matched by chance can still sit in order and be minutes
    # out. Each placed line is checked against the placed lines either side
    # of it: where both neighbours are close in the text, a line that lands
    # far from the time between them is dropped. What survives agrees with
    # para_sync's hand-checked maps to the second on Чайка and Горе от ума.
    wpos = {}
    n = 0
    for ci, paras in enumerate(chs):
        for pi, p in enumerate(paras):
            wpos[(ci, pi)] = n; n += max(1, len(words_of(spoken(p))))
    keys = sorted(placed, key=lambda k: wpos[k])
    drop = set()
    for i in range(1, len(keys) - 1):
        a, k, b = keys[i - 1], keys[i], keys[i + 1]
        wa, wk, wb = wpos[a], wpos[k], wpos[b]
        if wb - wa > 150 or placed[b] <= placed[a]: continue
        f = (wk - wa) / float(max(wb - wa, 1))
        guess = placed[a] + f * (placed[b] - placed[a])
        if abs(placed[k] - guess) > 20 + 0.25 * (placed[b] - placed[a]):
            drop.add(k)
    for k in drop: del placed[k]
    return placed

def probeable(p):
    return len(words_of(spoken(p))) >= 2

# Maps older than this run's baseline were made by para_sync and are kept;
# newer ones were made by this tool and may be remade.
KEEP_BEFORE = float(os.environ.get('PLAY_SYNC_KEEP_BEFORE', '1e12'))

def main():
    write = '--write' in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    changed = False
    for x in idx:
        if 'Theatrical' not in str(x.get('category') or ''): continue
        if only and not any(o in x['title'] for o in only): continue
        v = x.get('videos') or {}
        ids = {s.get('youtube') for s in v.values()}
        if len(ids) != 1: continue
        vid = ids.pop()
        vtt = 'tools/vtt/%s.ru.vtt' % vid
        if not os.path.exists(vtt): print(x['title'], '— no captions'); continue
        fn = x['filename']; path = 'public/books/' + fn
        if not os.path.exists(path): path = 'private/books/' + fn
        chs = [c['paras'] for c in reader_chapters(path)[0]]
        toks = load(vtt)
        placed = align_play(chs, toks)
        base = os.path.basename(fn).rsplit('.', 1)[0]
        print('%s  (%d acts, %d paragraphs placed)' % (x['title'], len(chs), len(placed)))
        # act starts
        starts, first_pi = {}, {}
        for ci in range(len(chs)):
            # Only an act's own opening lines say when it begins: the cast
            # list and the first stage direction are unspoken, so allow a
            # dozen paragraphs, and no further — a line found forty
            # paragraphs in says where the act is, not where it starts.
            # Counted in SPOKEN lines, so an act that opens with a
            # long cast list ("Лица четвертого действия", then one name per
            # line) is judged by its dialogue, not by its programme.
            spoken_idx = [pi for pi, p in enumerate(chs[ci]) if len(words_of(spoken(p))) >= 3][:12]
            opening = [pi for pi in spoken_idx if (ci, pi) in placed]
            if not opening:
                # A production that cuts an act's opening still says one thing
                # for certain: if the act's first surviving line is heard
                # BEFORE the act's current start, that start is late.
                anyp = [pi for pi in range(len(chs[ci])) if (ci, pi) in placed]
                cur0 = (v.get(str(ci)) or {}).get('start')
                if anyp and cur0 is not None and placed[(ci, anyp[0])] < cur0:
                    opening = anyp[:1]
            if opening:
                pi = opening[0]
                first_pi[ci] = pi
                # before the first placed line there may be a cast list and
                # stage directions nobody speaks: start a little before it
                starts[ci] = max(0, placed[(ci, pi)] - (8 if pi > 0 else 2))
        keys = sorted(v, key=int)
        for ci in range(len(chs)):
            ps = [pi for pi in range(len(chs[ci])) if (ci, pi) in placed]
            pr = sum(1 for p in chs[ci] if probeable(p))
            cur = v.get(str(ci), {})
            print('   act %d: %3d/%3d placed (%2d%%)  start %s -> %s%s' % (
                ci + 1, len(ps), pr, 100 * len(ps) // max(pr, 1),
                cur.get('start', 0) if cur else '-', starts.get(ci, '(kept)'),
                '' if ci not in first_pi else '  (from line %d)' % first_pi[ci]))
        if not write: continue
        # A scene with no segment of its own gets one when its very first
        # lines were found — Предложение had only its first scene timed.
        for ci in range(len(chs)):
            if str(ci) not in v and ci in starts and first_pi.get(ci, 99) <= 3 and ci > int(keys[0]):
                v[str(ci)] = {'youtube': vid, 'heading': 'Глава %d' % (ci + 1), 'start': starts[ci]}
        keys = sorted(v, key=int)
        # boundaries: the first act always starts at 0 (Dave, Sep 1 2026)
        for k in keys:
            ci = int(k)
            if ci in starts and k != keys[0]:
                v[k]['start'] = starts[ci]
        # starts must still run forward; if a found start would overtake its
        # neighbour, the old one stays
        for i in range(1, len(keys)):
            if (v[keys[i]].get('start') or 0) <= (v[keys[i - 1]].get('start') or 0):
                raise SystemExit('%s: act starts out of order at %s — nothing written' % (x['title'], keys[i]))
        for i, k in enumerate(keys[:-1]):
            nxt = v[keys[i + 1]].get('start')
            if nxt is not None: v[k]['end'] = nxt
        # maps: an act's jump points are the placed paragraphs inside its span
        out = 'public/books/audio-sync/%s' % base
        os.makedirs(out, exist_ok=True)
        for k in keys:
            ci = int(k)
            # An act that already has a map keeps it: those were checked by
            # hand, and this agrees with them to the second where both exist.
            f = out + '/%02d.json' % ci
            if os.path.exists(f) and os.path.getmtime(f) < KEEP_BEFORE: continue
            s0 = v[k].get('start', 0); s1 = v[k].get('end') or 10 ** 9
            m = {str(pi): placed[(ci, pi)] for pi in range(len(chs[ci]))
                 if (ci, pi) in placed and s0 - 5 <= placed[(ci, pi)] <= s1 + 5}
            ts = [m[k2] for k2 in sorted(m, key=int)]
            if len(m) < 5 or any(a > b for a, b in zip(ts, ts[1:])):
                continue
            json.dump(m, io.open(out + '/%02d.json' % ci, 'w', encoding='utf-8'))
        changed = True
    if write and changed:
        io.open('private/books/index.json', 'w', encoding='utf-8').write(
            json.dumps(idx, ensure_ascii=False, indent=2) + '\n')
        print('wrote private/books/index.json')

if __name__ == '__main__':
    main()
