#!/usr/bin/env python3
"""Open a book at the top of its text.

On a phone the PAGE scrolls, not the reading column, and React swapping the
library for the reader leaves that scroll where it was — so a book opened from
halfway down the shelf began halfway down its first page. Same on turning a
chapter from the buttons at the foot of one. Desktop was fine: there the
library and the reader are different scrollers.
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
    '''  // Reopening a merged story returns the reader to the section they left, once
  // the text is on the page. Runs once per book: after that the scroll listener
  // above owns secAt, and re-running would yank the reader back.''',
    '''  // A book, and every chapter in it, opens at the first line of the text.
  //
  // On a phone the document itself scrolls (see the max-width:900px block in
  // the stylesheet), so swapping the library for the reader kept the shelf's
  // scroll position: a book opened from the foot of a long shelf began
  // partway down its own first page, and turning a chapter from the buttons
  // at the foot of one started the next chapter at ITS foot. Desktop never
  // had this — there the library and the reading column are separate
  // scrollers, each starting at nought.
  //
  // Deliberate landings are left alone: a bookmark, a search result and a
  // vocabulary source-link all set srcJumpOffsetRef and place the reader
  // themselves, and a merged story restores its own section just below.
  var atTopRef = useRef("");
  useEffect(function() {
    if (!(started && isLit) || lview !== "read") return;
    if (srcJumpOffsetRef.current != null) return;
    if (mergedCh && mergedCh.merged) return;
    var key = (bookKey(bookMeta) || "") + "|" + cidx + "|" + pidx;
    if (atTopRef.current === key) return;
    atTopRef.current = key;
    try { window.scrollTo(0, 0); } catch (e) {}
    var col = document.querySelector(".lit-left");
    if (col) col.scrollTop = 0;
  }, [started, isLit, lview, cidx, pidx, bookMeta.title, mergedCh && mergedCh.merged]);

  // Reopening a merged story returns the reader to the section they left, once
  // the text is on the page. Runs once per book: after that the scroll listener
  // above owns secAt, and re-running would yank the reader back.''',
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
