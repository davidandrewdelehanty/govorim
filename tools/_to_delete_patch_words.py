#!/usr/bin/env python3
"""How long a book is, and how far through it you are.

Three places, one measure — Russian words, counted the way the reading record
already counts them:

  * the library index says how long each book is, from the count
    tools/word_counts.py writes into the catalogue;
  * the open book says the same number, and what share of it is behind you;
  * Continue reading carries that share for every book on the shelf, so it
    survives the book being closed.

Chapters were a poor ruler for the progress bar. They are wildly uneven —
Anna Karenina's are a page each, Мелкий бес's are scenes, Му-му is one — so
"chapter 34 of 239" and a bar to match said much less than they appeared to.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (n, old[:70])
    s = s.replace(old, new)


# ---------------------------------------------------------------- helpers --
rep(
    '''function bookLabel(book) {''',
    '''// A length, written out: "13,758 words". The catalogue carries the count for
// every preset book (tools/word_counts.py counts them the way the reader does,
// so the card and the open book never disagree); an upload has none until it
// is open, and then the reader counts its own.
function fmtWords(n) {
  n = Math.round(Number(n) || 0);
  if (!n) return "";
  return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ",") + " words";
}

function bookLabel(book) {''',
)

# ------------------------------------------------- progress, by words read --
rep(
    '  var pct  = chapters.length > 0 ? Math.round((cidx / chapters.length) * 100) : 0;',
    '''  // Where the reader has got to, measured in words rather than in chapters.
  // Counted once per book (the same expression as `ruCount` below, which
  // cannot be used here — it is declared further down and this runs during
  // render). `upto[i]` is the words lying behind chapter i.
  var bookWords = useMemo(function() {
    var upto = [], total = 0;
    for (var i = 0; i < chapters.length; i++) {
      upto.push(total);
      total += (String((chapters[i] && chapters[i].text) || "")
        .match(/[А-Яа-яЁё][А-Яа-яЁё-]*/g) || []).length;
    }
    return { upto: upto, total: total };
  }, [chapters]);
  // The catalogue's count is the one shown, everywhere, so the number on the
  // library card and the number in the open book are the same number.
  var bookWordsShown = (bookMeta && bookMeta.words) || bookWords.total;
  var pct  = isFinished(bookMeta) ? 100
           : bookWords.total ? Math.round(((bookWords.upto[cidx] || 0) / bookWords.total) * 100)
           : (chapters.length > 0 ? Math.round((cidx / chapters.length) * 100) : 0);''',
)

# ---------------------------------------------------- carried into storage --
rep(
    '''  var saveBookProgress = async function(meta, ci, pi, totalChapters) {''',
    '''  var saveBookProgress = async function(meta, ci, pi, totalChapters, words, wordsRead) {''',
)
rep(
    '''        splitByNumberedSections: !!meta.splitByNumberedSections,
        totalChapters: totalChapters || 0,
      };''',
    '''        splitByNumberedSections: !!meta.splitByNumberedSections,
        totalChapters: totalChapters || 0,
        // How long the book is and how much of it is behind the reader, so
        // Continue reading can show real progress for a book that is not
        // open — chapter counts alone made a scene of Мелкий бес look like
        // the same stride as a part of Anna Karenina.
        words: words || 0,
        wordsRead: wordsRead || 0,
      };''',
)
rep(
    '    saveBookProgress(bookMeta, cidx, pidx, chapters.length);',
    '    saveBookProgress(bookMeta, cidx, pidx, chapters.length,\n                     bookWordsShown, bookWords.upto[cidx] || 0);',
)

# ------------------------------------------------------- the library index --
rep(
    '''                                          {(function() {
                                            // An empty videos object is a slot waiting to be
                                            // filled, not a recording anyone can play.
                                            var hasVid = !!(book.videos && Object.keys(book.videos).length);
                                            if (!book.audiobook && !hasVid) return null;
                                            return (
                                              <span className="lib-tag">
                                                {(cat === "Theatrical Performances" && hasVid)
                                                  ? "video"
                                                  : "audio"}
                                              </span>
                                            );
                                          })()}''',
    '''                                          {(function() {
                                            // An empty videos object is a slot waiting to be
                                            // filled, not a recording anyone can play.
                                            var hasVid = !!(book.videos && Object.keys(book.videos).length);
                                            if (!book.audiobook && !hasVid) return null;
                                            return (
                                              <span className="lib-tag">
                                                {(cat === "Theatrical Performances" && hasVid)
                                                  ? "video"
                                                  : "audio"}
                                              </span>
                                            );
                                          })()}
                                          {/* How long it is. The one thing a reader choosing
                                              between a story and a novel most wants to know,
                                              and the shelf could not say. */}
                                          {book.words ? <span className="lib-tag len">{fmtWords(book.words)}</span> : null}''',
)

# ---------------------------------------------------- Continue reading row --
rep(
    '                                var pct = total > 1 ? Math.round((rec.cidx / total) * 100) : (rec.pidx > 0 ? 50 : 0);',
    '''                                // Words where they were recorded, chapters for a
                                // record written before the reader counted words.
                                var recWords = rec.words || (match.book && match.book.words) || 0;
                                var pct = (rec.words && rec.wordsRead != null)
                                  ? Math.round((rec.wordsRead / rec.words) * 100)
                                  : (total > 1 ? Math.round((rec.cidx / total) * 100) : (rec.pidx > 0 ? 50 : 0));''',
)
rep(
    '''                                    <div style={{marginTop:8,fontSize:11,color:"rgba(0,0,0,.55)"}}>
                                      {pct + "%"}
                                    </div>''',
    '''                                    <div style={{marginTop:8,fontSize:11,color:"rgba(0,0,0,.55)"}}>
                                      {recWords ? pct + "% of " + fmtWords(recWords) : pct + "%"}
                                    </div>''',
)

# ------------------------------------------------------ the open book says --
rep(
    '''                            <div className="book-line">
                              {bookLabel(bookMeta)}
                            </div>''',
    '''                            <div className="book-line">
                              {bookLabel(bookMeta)}
                              {bookWordsShown ? (
                                <span className="book-len">
                                  {" · "}
                                  {chapters.length > 1 ? pct + "% of " : ""}
                                  {fmtWords(bookWordsShown)}
                                </span>
                              ) : null}
                            </div>''',
)

rep(
    '''        .book-line{font-family:var(--serif)!important;font-style:italic!important;font-size:14px!important;color:var(--ink-2)!important;letter-spacing:0!important}''',
    '''        .book-line{font-family:var(--serif)!important;font-style:italic!important;font-size:14px!important;color:var(--ink-2)!important;letter-spacing:0!important}
        .book-line .book-len{font-style:normal;color:var(--ink-3);font-variant-numeric:tabular-nums}
        .lib-tag.len{font-variant-numeric:tabular-nums;letter-spacing:.1em}''',
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
