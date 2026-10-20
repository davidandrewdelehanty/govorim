# -*- coding: utf-8 -*-
"""Check every Russian word in tables_data.json back against the dictionary.

The tables were generated from OpenCorpora, so this should find nothing; it is
here so that a later hand-edit of the data cannot slip an invented form in.
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paradigms as P

CYR = re.compile(r"[а-яёА-ЯЁ]+", re.U)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    d = json.load(io.open(os.path.join(here, "tables_data.json"), encoding="utf-8"))
    bad, seen, n = [], set(), 0
    for key, t in d.items():
        if key.startswith("_"):
            continue
        for row in [t["head"]] + t["rows"]:
            for cell in row:
                for w in CYR.findall(cell or ""):
                    if len(w) < 3:
                        continue   # a bare letter in a column label (х, щ, бл)
                    n += 1
                    if w.lower() in seen:
                        continue
                    seen.add(w.lower())
                    if not [p for p in P.M.parse(w) if "UNKN" not in str(p.tag)]:
                        bad.append((key, w))
    print("%d word tokens, %d distinct, %d not in the dictionary" % (n, len(seen), len(bad)))
    for key, w in bad:
        print("   %-24s %s" % (key, w))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
