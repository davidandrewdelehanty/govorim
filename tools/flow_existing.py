#!/usr/bin/env python3
"""Turn an existing paired folder into a flowing one, keeping every word.

Some pairings drift. The translation is sound and the text is all there, but
the line sitting beside a given Russian paragraph is not its counterpart —
Крейцерова соната answers "Ведь вы подумайте, что бы должно быть и что есть"
with "It is necessary to go back to my sixteenth year". A reader trusts that
line, so a drifted pairing is worse than none.

Flow mode is the honest form for these: the English runs alongside at its own
length and claims no row. That needs no alignment at all — only that the
English stays in ORDER and is spread across the chapter so the reader's page
shows roughly the right stretch of it.

So this reads what is already there, takes the entries of each chapter in key
order, and lays them back down at even intervals across that chapter's Russian
paragraphs. Nothing is translated, nothing is dropped, and nothing afterwards
asserts that a particular English line renders a particular Russian one.

    python3 tools/flow_existing.py <parallelEn-dir> <fb2-path>
"""
import io, json, os, sys
sys.path.insert(0, 'tools')
from scan_alignment import chapters as fb2_chapters

def main():
    d, fb2 = sys.argv[1], sys.argv[2]
    root = 'public/books/' + d
    chs = fb2_chapters(fb2)
    if not chs: sys.exit('could not read ' + fb2)
    moved = 0
    for ci, c in enumerate(chs):
        f = os.path.join(root, '%02d.json' % (ci + 1))
        if not os.path.exists(f): continue
        m = json.load(io.open(f, encoding='utf-8'))
        note = m.get('_note')
        ks = sorted(int(k) for k in m if k != '_note' and str(k).lstrip('-').isdigit())
        # Each stored entry may itself hold several paragraphs already.
        text = []
        for k in ks:
            for part in str(m[str(k)]).split('\n\n'):
                if part.strip(): text.append(part.strip())
        M, N = max(len(c), 1), len(text)
        if not N: continue
        slot = {}
        for j, para in enumerate(text):
            slot.setdefault(min(M - 1, (j * M) // N), []).append(para)
        out = dict((str(k), '\n\n'.join(v)) for k, v in slot.items())
        if note: out['_note'] = note
        io.open(f, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
        moved += N
        print('ch%-3d ru %3d  en %3d  spread over %3d slots' % (ci + 1, len(c), N, len(slot)))
    print('\n%d english paragraphs kept, in order, none claiming a particular Russian line' % moved)

if __name__ == '__main__':
    main()
