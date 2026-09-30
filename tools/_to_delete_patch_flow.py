#!/usr/bin/env python3
"""Let both languages run at their own length.

The reader paired the English to the Russian paragraph by paragraph, and where
the pairing was good it was very good — but a translator is not a machine that
emits one paragraph per paragraph. Garnett breaks a long Russian paragraph in
two, joins two short ones, moves a line of dialogue. Every one of those shifts
everything after it by one, and a translation sitting beside the wrong
paragraph reads as a translation OF it: confident nonsense, worse than no
English at all.

Flow mode — already built, and switched on for nineteen books whose alignment
score was poor — stops pretending: the Russian runs down its column, the
English runs down its own, and the reader matches them by eye the way they
would with two books open. This makes it how every book behaves.

Scripture keeps its verse pairing. A verse number is a real correspondence
that both texts carry, not a guess made from paragraph order, and the Bible
lays its English under each verse rather than in a second column.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (n, old[:70])
    s = s.replace(old, new)


rep(
    '''  // Flow mode stops pretending. The Russian runs down its column and the
  // English runs down its own, each at its natural length, and the reader
  // matches them by eye the way they would with two books open. Set per book
  // in the catalogue, from the alignment score.
  var flowEn = !!(bookMeta && bookMeta.flowEn) && !bibleInline;''',
    '''  // Flow mode stops pretending. The Russian runs down its column and the
  // English runs down its own, each at its natural length, and the reader
  // matches them by eye the way they would with two books open.
  //
  // It used to be set per book, from the alignment score, and the books that
  // scored well kept the paragraph-by-paragraph pairing. They should not
  // have: a good score means most paragraphs line up, and the handful that
  // do not are exactly where a reader reaches for the translation. Chapter
  // against chapter is the honest unit, so every book reads this way now.
  // `flowEn` in the catalogue is left alone — it no longer decides anything.
  //
  // Scripture is the exception, and not an arbitrary one: a verse number is a
  // correspondence both texts carry, so the Bible keeps its verse pairing and
  // lays the English under each verse (bibleInline) rather than in a column.
  var flowEn = !bibleInline;''',
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")

# The note that introduces the translation promised something the reader can
# no longer see. 61 of the 114 said "Paired paragraph by paragraph."
import json, os, re

root = os.path.dirname(os.path.dirname(os.path.abspath(p))) or "."
man_path = os.path.join(root, "private", "books", "index.json")
if os.path.exists(man_path):
    man = json.load(open(man_path, encoding="utf-8"))
    pat = re.compile(r"\s*Paired paragraph by paragraph\.")
    n = 0
    for b in man:
        t = b.get("translationNote") or ""
        if pat.search(t):
            b["translationNote"] = pat.sub(
                " The two texts run side by side, each at its own length.", t).strip()
            n += 1
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("notes rewritten: %d" % n)
else:
    print("!! manifest not found at %s — rewrite the notes by hand" % man_path)
