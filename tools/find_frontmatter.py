#!/usr/bin/env python3
"""Find the scanned volume's own furniture sitting in the text.

These English folders were made from scans, and a scan contains more than the
work: a publisher's list of other titles, a title page, a printer's colophon,
a copyright notice, running headers. OCR does not know which is which, so it
all arrives as prose and gets paired against the Russian — Красный смех opened
with "A LIST OF BOOKS ON RUSSIA AND SIBERIA" against Andreyev's first line.

Nothing here is deleted on a guess. A paragraph has to look like publisher
matter on SEVERAL counts at once, and short entries are judged more harshly
than long ones, because a real paragraph of Tolstoy does not fit in a line.

    python3 tools/find_frontmatter.py            # report only
    python3 tools/find_frontmatter.py --apply    # remove what it reports
"""
import io, json, os, re, sys

# Each pattern carries a weight, and an entry needs 2 to be called publisher
# matter. Some signs are conclusive on their own and score 2: nothing inside a
# novel is a list of the publisher's other books, or a bare run of act names.
# Others are only suggestive and score 1 — a city and a colon, a date in roman
# numerals — so two of them must agree before anything is removed.
SIGNS = [
    (2, re.compile(r'\bA LIST OF BOOKS\b')),
    (2, re.compile(r'^Author of\b')),
    (2, re.compile(r'\bPrivately Printed\b')),
    (2, re.compile(r'\bPublished by\b')),
    (2, re.compile(r'\bILLUSTRATED EDITION\b')),
    (2, re.compile(r'\bTHE (NOVELS|WORKS|PLAYS|TALES) OF\b')),
    # Case-sensitive, both of them. "a white uniform with green plumes" and
    # "the series of Russian victories" are Война и мир, not a catalogue.
    (2, re.compile(r'\bUniform with\b|\bSERIES OF RUSSIAN\b')),
    # Case matters here. A printer's notice shouts; a character complaining
    # that he "would not let anything be printed in those papers" does not,
    # and case-insensitivity was enough to condemn that line of Дым.
    (2, re.compile(r'\bPRINTED (BY|IN)\b|\bCOPYRIGHT\b')),
    (2, re.compile(r'\bAll rights reserved\b', re.I)),
    (2, re.compile(r'\bPrinted by [A-Z]')),
    # A contents list: several divisions named in one short entry and nothing
    # else. "Act One Act Two" is a table of contents; a sentence that mentions
    # Act Two is not, which is why this must match the WHOLE entry.
    (2, re.compile(r'^(?:(?:Act|Chapter|Scene|Part)\s+[A-Za-z0-9]+[ .,]*){2,}$', re.I)),
    (2, re.compile(r'\bCast of Characters\s*$')),
    (1, re.compile(r'\b(Crown|Fcap|Demy|Royal)\.? ?8vo\b', re.I)),
    (1, re.compile(r'\b\d+s\.? ?\d*d\.? net\b|\bnet\.\s*$|\bprice \d', re.I)),
    (1, re.compile(r'\bSecond Edition\b|\bNew Edition\b')),
    (1, re.compile(r'\b(Adapted|Edited|Translated) by [A-Z]', re.I)),
    (1, re.compile(r'\b(MACMILLAN|Heinemann|Chatto|Duckworth|Constable|T\. FISHER UNWIN|BELL AND SONS)\b', re.I)),
    (1, re.compile(r"\bLIBRARY\)|\(Children's Library\)|\bSERIES\b")),
    (1, re.compile(r'^[A-Z][A-Z .,\'"-]{18,}$')),
    (1, re.compile(r'\bLONDON\b *[:.]|\bNEW YORK\b *[:.]', re.I)),
    (1, re.compile(r"\bPOUSHKIN'S PROSE TALES\b|\bPROSE TALES\b", re.I)),
    (1, re.compile(r'\bPrinted in England\b|\bMCM[IVXLC]{0,6}\b')),
]

# A colophon can arrive stuck to the end of the last real paragraph — Ася's
# closing line ends "...outlives man himself. 1857. Printed by T. and A." The
# paragraph is the novel and must stay; only the tail is the printer's.
TAIL = re.compile(r'\s*(?:\b\d{4}\.\s*)?(?:Printed by [A-Z][A-Za-z.,& ]*|PRINTED IN [A-Z ]+|All rights reserved\.?)\s*$')
# And it can arrive as a PREFIX, with the work's own dedication behind it:
# "PRINTED IN THE UNITED STATES OF AMERICA To Ivan Alexeievich Bunin".
HEAD = re.compile(r'^(?:PRINTED IN [A-Z ]+?|All rights reserved\.?)\s+(?=[A-Z][a-z])')

def trim_tail(t):
    out = HEAD.sub('', TAIL.sub('', t).rstrip()).strip()
    return out if out != t and len(out) >= 20 else None

def score(t):
    t = t.strip()
    # Length alone disqualifies. A publisher's advertisement, a colophon, a
    # title page and a contents list are all SHORT; a paragraph of Tolstoy is
    # not. Letting long entries qualify by accumulating weak signs was enough
    # to condemn a real paragraph of Война и мир and one of Олеся, which is
    # exactly the kind of mistake that must not be made by a tool that deletes.
    if len(t) >= 300:
        return 0, 99
    return sum(w for w, p in SIGNS if p.search(t)), 2

def main():
    apply = '--apply' in sys.argv
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    total = 0
    for b in idx:
        d = b.get('parallelEn')
        root = 'public/books/' + str(d)
        if not d or not os.path.isdir(root): continue
        for f in sorted(os.listdir(root)):
            p = os.path.join(root, f)
            if not (os.path.isfile(p) and f.endswith('.json')): continue
            try: m = json.load(io.open(p, encoding='utf-8'))
            except Exception: continue
            hits, trims = [], []
            for k, v in list(m.items()):
                if k == '_note': continue
                whole = str(v)
                cut = trim_tail(whole.strip())
                if cut is not None:
                    trims.append((k, cut)); continue
                for part in whole.split('\n\n'):
                    n, need = score(part)
                    if n >= need:
                        hits.append((k, part.strip()[:88], n)); break
            if not hits and not trims: continue
            total += len(hits) + len(trims)
            print('%-26s %-24s %s' % (b['title'][:26], d[:24], f))
            for k, t, n in hits[:6]:
                print('      drop [%s] (%d signs) %s' % (k, n, t))
            for k, t in trims[:4]:
                print('      trim [%s] ...%s' % (k, t[-60:]))
            if apply:
                for k, cut in trims: m[k] = cut
                keys = set(k for k, _, _ in hits)
                note = m.get('_note')
                left = [(int(k), v) for k, v in m.items()
                        if k != '_note' and k not in keys and str(k).lstrip('-').isdigit()]
                left.sort()
                out = dict((str(k), v) for k, v in left)
                if note: out['_note'] = note
                io.open(p, 'w', encoding='utf-8').write(
                    json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('\n%d entries look like publisher matter%s' % (total, ' — removed' if apply else ''))

if __name__ == '__main__':
    main()
