#!/usr/bin/env python3
"""Score each Translations alignment by name agreement: of the Russian
paragraphs that name someone (a name the English also uses somewhere), how
many sit beside English that names them too. A correct alignment of even a
loose translation scores well above 50%; a wrong one falls toward chance.

    python3 tools/translations_audit.py [--only slug ...]
"""
import csv, io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translations_build as tb
from reader_chapters import reader_chapters

a = sys.argv[1:]
only = a[a.index("--only") + 1:] if "--only" in a else None
rows = [r for r in csv.reader(io.open("tools/translations/list.tsv", encoding="utf-8"), delimiter="\t") if r and not r[0].startswith("#")]
for r in rows:
    s = r[0]
    if only and s not in only:
        continue
    d = "public/books/%s-en" % s
    if not os.path.isdir(d):
        continue
    chs, _ = reader_chapters("public/books/novel/%s.fb2" % s)
    ru = [p for c in chs for p in c["paras"]]
    if not os.path.exists("tools/translations/en/%s.txt" % s): continue
    en_all = tb.en_paragraphs(s)
    enkeys = set().union(*tb.name_keys(en_all, False)) if en_all else set()
    rk = tb.name_keys(ru, True)
    hit = tot = 0
    g = 0
    for ci, c in enumerate(chs):
        f = os.path.join(d, "%02d.json" % (ci + 1))
        m = json.load(io.open(f, encoding="utf-8")) if os.path.exists(f) else {}
        for pi in range(len(c["paras"])):
            ks = {k for k in rk[g] if k in enkeys and not k.startswith("#")}
            g += 1
            t = m.get(str(pi))
            if not ks or not t:
                continue
            ek = set().union(*tb.name_keys(t.split("\n\n"), False))
            tot += 1
            hit += bool(ks & ek)
    print("%-28s %5.1f%%  (%d named paragraphs)" % (s, 100.0 * hit / max(tot, 1), tot), flush=True)
