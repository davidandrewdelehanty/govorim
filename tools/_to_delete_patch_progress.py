import sys
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
def rep(old,new,count=1):
    global s
    n=s.count(old); assert n==count,(n,old[:70]); s=s.replace(old,new)

# 1. the two operations, next to toggleFinished
rep('''  var toggleFinished = function(meta) {
    var k = bookKey(meta);
    if (!k) return;
    var nowFinished = false;''','''  // Two ways of undoing a reading. "Reset" puts a book back at its first
  // page — for the reader who skimmed ahead to see what a book is like and
  // now means to read it properly — and keeps it on the Continue list at 0%.
  // "Forget" drops it from the list altogether, as if it had never been
  // opened. Both act on the same record the reader resumes from, so the next
  // opening honours them. The server copy of progress feeds only the admin's
  // "books opened" count and is left alone.
  var writeProgressMap = async function(fn) {
    try {
      var r = await storage.get(BOOK_PROGRESS);
      var all = r ? (JSON.parse(r.value) || {}) : {};
      all = fn(all) || all;
      await storage.set(BOOK_PROGRESS, JSON.stringify(all));
      setProgressMap(all);
    } catch (e) {}
  };
  var resetBookProgress = function(key) {
    if (!key) return;
    return writeProgressMap(function(all) {
      if (all[key]) all[key] = Object.assign({}, all[key], { cidx: 0, pidx: 0, sec: 0, lastRead: Date.now() });
      return all;
    });
  };
  var forgetBookProgress = function(key) {
    if (!key) return;
    return writeProgressMap(function(all) { delete all[key]; return all; });
  };

  var toggleFinished = function(meta) {
    var k = bookKey(meta);
    if (!k) return;
    var nowFinished = false;''')

# 2. Continue reading rows: carry the key, offer reset / remove
rep('''                        var entries = Object.keys(progressMap).map(function(k){ return progressMap[k]; });
                        // A book marked read is finished, and there is nothing to''','''                        var entries = Object.keys(progressMap).map(function(k){ return Object.assign({ key: k }, progressMap[k]); });
                        // A book marked read is finished, and there is nothing to''')
rep('''                                    <div className="lcn" style={{color:"rgba(0,0,0,.5)"}}>
                                      {humanLast}
                                      {isFinished(match.book) && <span className="lib-done" style={{marginLeft:8}}>read</span>}
                                    </div>''','''                                    <div className="lcn" style={{color:"rgba(0,0,0,.5)"}}>
                                      {humanLast}
                                      {isFinished(match.book) && <span className="lib-done" style={{marginLeft:8}}>read</span>}
                                      {/* Undo, two ways: back to the first page, or off the
                                          list entirely. Both stop the click reaching the
                                          row, which would open the book instead. */}
                                      {(rec.cidx > 0 || rec.pidx > 0) && (
                                        <button type="button" className="lcard-act" title="Back to the first page — for a book you skimmed and now mean to read"
                                          onClick={function(e){ e.stopPropagation(); resetBookProgress(rec.key); }}>reset</button>
                                      )}
                                      <button type="button" className="lcard-act" title="Take this book off the list"
                                        onClick={function(e){ e.stopPropagation(); forgetBookProgress(rec.key); }}>remove</button>
                                    </div>''')

# 3. In the reader, beside "Mark as read": start over
rep('''                            <button
                              className={"mark-read" + (isFinished(bookMeta) ? " on" : "")}
                              onClick={function(){ toggleFinished(bookMeta); }}
                              title={isFinished(bookMeta) ? "Marked as read — click to undo" : "Mark this book as read"}>
                              {isFinished(bookMeta) ? "Read" : "Mark as read"}
                            </button>''','''                            <span className="read-acts">
                              {(cidx > 0 || pidx > 0) && (
                                <button className="mark-read" title="Back to the first page and forget where you were — for a book you skimmed and now mean to read"
                                  onClick={function(){ resetBookProgress(bookKey(bookMeta)); setCbm(0); startLit(0, chapters); }}>
                                  Start over
                                </button>
                              )}
                              <button
                                className={"mark-read" + (isFinished(bookMeta) ? " on" : "")}
                                onClick={function(){ toggleFinished(bookMeta); }}
                                title={isFinished(bookMeta) ? "Marked as read — click to undo" : "Mark this book as read"}>
                                {isFinished(bookMeta) ? "Read" : "Mark as read"}
                              </button>
                            </span>''')

# 4. styles (theme layer)
rep('''        .lcp{font-family:var(--serif)}
        /* Contents drawer (same .lcard) */''','''        .lcp{font-family:var(--serif)}
        .lcard-act{background:none;border:0;border-bottom:1px solid transparent;padding:0;margin-left:12px;cursor:pointer;
          font-family:var(--sans);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}
        .lcard-act:hover{color:var(--rubric);border-bottom-color:var(--rubric)}
        .read-acts{display:inline-flex;align-items:center;gap:16px;flex:none}
        /* Contents drawer (same .lcard) */''')
rep('''grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"head when" "bar bar";gap:2px 16px;align-items:baseline}''',
    '''grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"head when" "pct pct" "bar bar";gap:2px 16px;align-items:baseline}''')
rep('''.lcard > div[style*="marginTop:8"],.lcard > div[style*="margin-top: 8px"]{grid-area:bar;font-family:var(--sans);font-size:10px;letter-spacing:.1em;margin-top:2px!important}''',
    '''.lcard > div[style*="marginTop:8"],.lcard > div[style*="margin-top: 8px"]{grid-area:pct;font-family:var(--sans);font-size:10px;letter-spacing:.1em;margin-top:2px!important}''')
rep('''.pjump,.pbm{background:none;border:0;opacity:.3;filter:none;''','''.pjump,.pbm{background:none;border:0;opacity:.22;filter:none;''')
open(p,"w",encoding="utf-8",newline="\n").write(s); print("ok")
