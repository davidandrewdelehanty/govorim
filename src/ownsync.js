// Where every paragraph of the reader's own book falls in the recording they
// pasted beside it — worked out here, in the browser, from the recording's
// subtitles.
//
// This is tools/para_sync.py (the catalogue's paragraph aligner) and
// tools/place_picks.py (its chapter placer) carried over to JavaScript, so
// that a book that never leaves the reader's machine gets the same jump
// arrows the catalogue books have. The book text stays on the device: the
// only thing asked of the site is the subtitles themselves (/api/sync fetches
// them from YouTube, which a browser cannot do directly, and keeps nothing).
// A transcript pasted by the reader never goes anywhere at all.
//
//   alignBook(chapters, cues, seconds, onProgress)
//     chapters: the reader's chapters, [{ text }] — paragraphs are the runs
//               between blank lines, numbered the way the page numbers them
//     cues:     [[seconds, "words"], …] from parseCues
//     → { bounds: { "<chapter>": { start, end } },      where each chapter runs
//         sync:   { "<chapter>": { "<paragraph>": sec } },  the jump points
//         chapters, chaptersFound, paras, parasFound, median, end, ok, why }
//
// A paragraph gets a time only when its opening words were actually found in
// the subtitles; the rest get no arrow, which is honest — a button that lands
// thirty seconds out is worse than none.

export function norm(w) {
  return String(w || "").toLowerCase().replace(/ё/g, "е").replace(/[^а-я]/g, "");
}

function clock(h, m, s, ms) {
  return (+h || 0) * 3600 + (+m || 0) * 60 + (+s || 0) + (+(String(ms || "0").slice(0, 3).padEnd(3, "0"))) / 1000;
}

// Cues out of whatever came in: WebVTT, SRT, YouTube's json3, or the text a
// reader copies out of YouTube's own "Show transcript" panel — "0:00" on a
// line and the words on the next, or, as the panel is copied in some
// browsers, "2:44:412 часа 44 минуты 41 секундаЯ был уверен…": the time, then
// the time read out in words for a screen reader, then the words themselves.
export function parseCues(raw) {
  var s = String(raw || "");
  if (/^\s*\{/.test(s)) {
    try {
      var j = JSON.parse(s);
      var ev = Array.isArray(j.events) ? j.events : [];
      var out0 = [];
      for (var i = 0; i < ev.length; i++) {
        var e = ev[i];
        var txt0 = (e.segs || []).map(function(x){ return x.utf8 || ""; }).join("").replace(/\s+/g, " ").trim();
        if (txt0 && typeof e.tStartMs === "number") out0.push([e.tStartMs / 1000, txt0]);
      }
      return out0;
    } catch (e0) { /* fall through */ }
  }
  var out = [];
  if (/-->/.test(s)) {
    var blocks = s.replace(/\r/g, "").split(/\n\s*\n/);
    for (var b = 0; b < blocks.length; b++) {
      var blk = blocks[b];
      var m = blk.match(/(?:(\d+):)?(\d\d):(\d\d)[.,](\d+)\s+-->/);
      if (!m) continue;
      var t = clock(m[1], m[2], m[3], m[4]);
      var txt = blk.slice(blk.indexOf("-->"));
      txt = txt.replace(/^[^\n]*\n?/, "");
      txt = txt.replace(/<[^>]*>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");
      txt = txt.replace(/\s+/g, " ").trim();
      if (txt) out.push([t, txt]);
    }
    return out;
  }
  var lines = s.replace(/\r/g, "").split("\n");
  var cur = null, buf = [];
  var flush = function() { if (cur !== null && buf.length) out.push([cur, buf.join(" ").replace(/\s+/g, " ").trim()]); buf = []; };
  var spoken = /^\s*(?:\d+\s*час(?:а|ов)?\s*)?(?:\d+\s*минут[аы]?\s*)?(?:\d+\s*секунд[аы]?\s*)?/;
  for (var k = 0; k < lines.length; k++) {
    var line = lines[k];
    var mm = line.match(/^\s*(?:(\d+):)?(\d{1,2}):(\d{2})\s*(.*)$/);
    if (mm) {
      flush();
      cur = clock(mm[1], mm[2], mm[3], 0);
      // "2:44:41" is sometimes followed, with no space, by "2 часа 44 минуты
      // 41 секунда" — the same time read aloud — before the words.
      var rest = mm[4].replace(spoken, "").trim();
      if (rest) buf.push(rest);
    } else if (line.trim()) buf.push(line.trim());
  }
  flush();
  return out;
}

// Timed words. Rolling captions repeat the previous line, so each cue
// contributes only its new tail; and those new words are spread evenly from
// this cue's start to the next cue's, since that span is when they were
// actually spoken.
export function tokens(cues) {
  var toks = [];
  for (var ci = 0; ci < cues.length; ci++) {
    var t = cues[ci][0], txt = cues[ci][1];
    var ws = txt.split(/\s+/).filter(Boolean);
    if (toks.length) {
      var prev = toks.slice(-40).map(function(x){ return x[1]; });
      var best = 0;
      for (var k = Math.min(ws.length, prev.length); k > 0; k--) {
        var same = true;
        for (var i = 0; i < k; i++) if (prev[prev.length - k + i] !== ws[i]) { same = false; break; }
        if (same) { best = k; break; }
      }
      ws = ws.slice(best);
    }
    if (!ws.length) continue;
    var tNext = ci + 1 < cues.length ? cues[ci + 1][0] : t + 4.0;
    var span = Math.max(0.5, tNext - t);
    for (var wi = 0; wi < ws.length; wi++) toks.push([t + span * wi / ws.length, ws[wi]]);
  }
  return toks;
}

// difflib's ratio: twice the matched words over the words in both, matches
// found the Ratcliff/Obershelp way.
function ratio(a, b) {
  if (!a.length && !b.length) return 1;
  var matched = 0;
  var stack = [[0, a.length, 0, b.length]];
  while (stack.length) {
    var fr = stack.pop();
    var alo = fr[0], ahi = fr[1], blo = fr[2], bhi = fr[3];
    var bi = alo, bj = blo, bsz = 0;
    var prev = new Map();
    for (var i = alo; i < ahi; i++) {
      var cur = new Map();
      for (var j = blo; j < bhi; j++) {
        if (a[i] !== b[j]) continue;
        var k = (prev.get(j - 1) || 0) + 1;
        cur.set(j, k);
        if (k > bsz) { bi = i - k + 1; bj = j - k + 1; bsz = k; }
      }
      prev = cur;
    }
    if (!bsz) continue;
    matched += bsz;
    if (alo < bi && blo < bj) stack.push([alo, bi, blo, bj]);
    if (bi + bsz < ahi && bj + bsz < bhi) stack.push([bi + bsz, ahi, bj + bsz, bhi]);
  }
  return 2 * matched / (a.length + b.length);
}

function wordsOf(text) {
  return String(text || "").split(/\s+/).map(norm).filter(Boolean);
}

// The paragraphs of a chapter, numbered as the page numbers them: the runs
// between blank lines, the empty ones left out.
export function paragraphsOf(text) {
  return String(text || "").split(/\n{2,}/).filter(function(p){ return p.trim().length > 0; });
}

// A printed play names the speaker and puts the stage business in
// parentheses; neither is read aloud. Only the probe is cleaned.
var SPEAKER = /^\s*(?:[А-ЯЁ][а-яё]*\.?\s*){1,3}\s*(?:\([^)]*\)\s*)?\.\s+/;
function spokenText(text) {
  return String(text || "").replace(SPEAKER, "").replace(/\([^)]*\)/g, " ");
}

function lowerBound(arr, x) {
  var lo = 0, hi = arr.length;
  while (lo < hi) { var mid = (lo + hi) >> 1; if (arr[mid] < x) lo = mid + 1; else hi = mid; }
  return lo;
}

// The timed token stream with its word index: built once per recording.
function stream(toks) {
  var times = toks.map(function(x){ return x[0]; });
  var words = toks.map(function(x){ return norm(x[1]); });
  var where = new Map();
  for (var i = 0; i < words.length; i++) {
    var w = words[i];
    if (!w) continue;
    var arr = where.get(w);
    if (!arr) { arr = []; where.set(w, arr); }
    arr.push(i);
  }
  return { times: times, words: words, where: where, n: words.length };
}

// Score `op` at every position in [a, b) where one of its first three words
// occurs; the best match, or null.
function bestAt(st, op, a, b, minScore) {
  if (op.length < 4) return null;
  a = Math.max(0, a); b = Math.min(st.n, b);
  if (b <= a) return null;
  var cands = new Set();
  for (var k = 0; k < Math.min(3, op.length); k++) {
    var occ = st.where.get(op[k]);
    if (!occ) continue;
    var lo = lowerBound(occ, a + k), hi = lowerBound(occ, b + k);
    for (var q = lo; q < hi; q++) cands.add(occ[q] - k);
  }
  var best = [0, null];
  var sorted = Array.from(cands).sort(function(x, y){ return x - y; });
  for (var c = 0; c < sorted.length; c++) {
    var j = sorted[c];
    if (j < 0 || j + op.length > st.n) continue;
    var r = ratio(st.words.slice(j, j + op.length), op);
    if (r > best[0]) { best = [r, j]; if (r > 0.95) break; }
  }
  return best[0] >= minScore ? { at: best[1], score: best[0] } : null;
}

// Opening phrases of a chapter, one per early paragraph: several books open
// with the publisher's boilerplate, which a narrator skips.
function probesOf(paras, n) {
  var out = [];
  for (var i = 0; i < Math.min(paras.length, (n || 4) + 2); i++) {
    var w = wordsOf(paras[i]);
    if (w.length >= 8) out.push(w.slice(0, 14));
    if (out.length >= (n || 4)) break;
  }
  if (!out.length) {
    var w2 = wordsOf(paras.join(" "));
    if (w2.length >= 5) out.push(w2.slice(0, 14));
  }
  return out;
}

// Where each chapter starts, searched forward so order is structural.
function locateChapters(chaptersParas, st) {
  var out = [];
  var cur = 0;
  for (var c = 0; c < chaptersParas.length; c++) {
    var best = null, len = 0;
    var ops = probesOf(chaptersParas[c]);
    for (var p = 0; p < ops.length; p++) {
      var op = ops[p];
      if (op.length < 5) continue;
      var got = bestAt(st, op, cur, st.n, 0.55);
      if (got && (!best || got.score > best.score)) { best = got; len = op.length; }
      if (best && best.score >= 0.8) break;
    }
    if (best) { out.push({ start: st.times[best.at], score: best.score, at: best.at }); cur = best.at + len; }
    else out.push(null);
  }
  return out;
}

// Every paragraph of one chapter, looked for where it ought to fall: a coarse
// pass that samples one paragraph in twenty-four with a wide window, then a
// fine pass between the anchors that found; the longest forward-moving run of
// matches is kept so one wrong match cannot fold time backwards.
function alignChapter(paras, st, t0, t1, loose) {
  var lo = lowerBound(st.times, t0);
  var hi = t1 ? lowerBound(st.times, t1) : st.n;
  var wc = paras.map(function(p){ return Math.max(1, wordsOf(p).length); });
  var total = wc.reduce(function(a, b){ return a + b; }, 0);
  var span = (t1 ? t1 : (st.times[st.n - 1] || t0)) - t0;
  var rate = Math.max(0.05, span / Math.max(total, 1));
  var cumAt = [], cum = 0;
  for (var i = 0; i < paras.length; i++) { cumAt.push(cum); cum += wc[i]; }

  var probe = function(pi, centre, half) {
    var op = wordsOf(spokenText(paras[pi])).slice(0, 10);
    if (op.length < 4) return null;
    var a = Math.max(lo, lowerBound(st.times, centre - half));
    var b = Math.min(hi, lowerBound(st.times, centre + half));
    var got = bestAt(st, op, a, b, 0.6);
    return got ? st.times[got.at] : null;
  };

  var wide = loose ? 600 : 300, tight = loose ? 150 : 75;
  var coarse = {};
  var step = Math.max(1, Math.floor(paras.length / 24));
  for (var pi = 0; pi < paras.length; pi += step) {
    var t = probe(pi, t0 + rate * cumAt[pi], wide);
    if (t !== null) coarse[pi] = t;
  }
  var ck = Object.keys(coarse).map(Number).sort(function(a, b){ return a - b; });
  var fwd = [], lastT = -1;
  for (var q = 0; q < ck.length; q++) if (coarse[ck[q]] >= lastT) { fwd.push(ck[q]); lastT = coarse[ck[q]]; }
  var anchors = fwd;
  var expected = function(p) {
    if (!anchors.length) return t0 + rate * cumAt[p];
    var before = null, after = null;
    for (var z = 0; z < anchors.length; z++) { if (anchors[z] <= p) before = anchors[z]; else { after = anchors[z]; break; } }
    if (before !== null && after !== null) {
      var f = (cumAt[p] - cumAt[before]) / Math.max(cumAt[after] - cumAt[before], 1);
      return coarse[before] + f * (coarse[after] - coarse[before]);
    }
    if (before !== null) return coarse[before] + rate * (cumAt[p] - cumAt[before]);
    return coarse[after] - rate * (cumAt[after] - cumAt[p]);
  };
  var cands = [];
  for (var p2 = 0; p2 < paras.length; p2++) {
    if (anchors.indexOf(p2) !== -1) { cands.push([p2, coarse[p2]]); continue; }
    var t2 = probe(p2, expected(p2), tight);
    if (t2 !== null) cands.push([p2, t2]);
  }
  // longest non-decreasing run of times, by paragraph order
  var n = cands.length, bestLen = [], prev = [];
  for (var x = 0; x < n; x++) {
    bestLen.push(1); prev.push(-1);
    for (var y = 0; y < x; y++) {
      if (cands[y][1] <= cands[x][1] && bestLen[y] + 1 > bestLen[x]) { bestLen[x] = bestLen[y] + 1; prev[x] = y; }
    }
  }
  var keep = {};
  if (n) {
    var bi = 0;
    for (var z2 = 1; z2 < n; z2++) if (bestLen[z2] > bestLen[bi]) bi = z2;
    while (bi >= 0) { keep[String(cands[bi][0])] = Math.round(cands[bi][1]); bi = prev[bi]; }
  }
  return { map: keep, found: Object.keys(keep).length, total: paras.length, rate: rate };
}

function median(xs) {
  if (!xs.length) return 0;
  var s = xs.slice().sort(function(a, b){ return a - b; });
  var h = s.length >> 1;
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
}

function tick() { return new Promise(function(r){ setTimeout(r, 0); }); }

export async function alignBook(chapters, cues, seconds, onProgress) {
  var toks = tokens(cues || []);
  var res = { chapters: chapters.length, chaptersFound: 0, paras: 0, parasFound: 0, bounds: {}, sync: {}, median: 0, end: 0, ok: false, why: "" };
  if (toks.length < 50) { res.why = "The subtitles are too short to place anything."; return res; }
  var st = stream(toks);
  var end = Math.max(seconds || 0, st.times[st.n - 1] + 4);
  res.end = Math.round(end);
  var chParas = chapters.map(function(ch){ return paragraphsOf(ch && ch.text); });
  var chWords = chParas.map(function(ps){ return ps.reduce(function(a, p){ return a + wordsOf(p).length; }, 0); });
  res.paras = chParas.reduce(function(a, ps){ return a + ps.length; }, 0);

  // 1. the chapters' openings
  var starts = locateChapters(chParas.map(function(ps){ return ps.slice(0, 6).map(function(p){ return p.slice(0, 600); }); }), st);
  var hits = starts.filter(Boolean);
  res.median = +median(hits.map(function(h){ return h.score; })).toFixed(2);
  if (!hits.length) { res.why = "None of the chapter openings is in these subtitles — is this a reading of the same book?"; return res; }
  // the narrator's pace, from the chapters that were found
  var firstFound = starts.findIndex(Boolean);
  var wordsAfter = 0;
  for (var c = firstFound; c < chapters.length; c++) wordsAfter += chWords[c];
  var rate = Math.min(1.5, Math.max(0.2, (end - starts[firstFound].start) / Math.max(wordsAfter, 1)));

  // 2. every paragraph of every chapter
  var t0s = [];
  for (var i = 0; i < chapters.length; i++) {
    var est = false;
    var t0;
    if (starts[i]) t0 = starts[i].start;
    else {
      // not found: where it ought to fall, counting words on from the last
      // chapter that was
      est = true;
      var pv = -1;
      for (var j = i - 1; j >= 0; j--) if (t0s[j] !== undefined) { pv = j; break; }
      if (pv >= 0) { var w = 0; for (var j2 = pv; j2 < i; j2++) w += chWords[j2]; t0 = t0s[pv] + rate * w; }
      else t0 = 0;
    }
    var t1 = 0;
    for (var k = i + 1; k < chapters.length; k++) if (starts[k]) { t1 = starts[k].start; break; }
    if (!t1) t1 = end;
    if (t0 >= t1) { t0s.push(undefined); continue; }
    var al = chParas[i].length ? alignChapter(chParas[i], st, t0, t1, est) : { map: {}, found: 0, total: 0 };
    // The chapter starts where its first located paragraph does, less the
    // words before that one — which is exact when the first paragraph itself
    // was found, and places a chapter whose opening the chapter search
    // missed (a publisher's note the narrator skipped, say) all the same.
    var ks = Object.keys(al.map).map(Number).sort(function(a, b){ return a - b; });
    if (ks.length >= (est ? 2 : 1)) {
      var before = 0;
      for (var z = 0; z < ks[0]; z++) before += wordsOf(chParas[i][z]).length;
      var t0b = Math.max(0, al.map[String(ks[0])] - (al.rate || rate) * before);
      if (est || ks[0] === 0 || Math.abs(t0b - t0) < 120) t0 = t0b;
      if (est) starts[i] = { start: t0, score: 0, estimated: true };
    } else if (est) { t0s.push(undefined); if (onProgress) onProgress(i + 1, chapters.length); await tick(); continue; }
    t0s.push(t0);
    res.sync[String(i)] = al.map;
    res.parasFound += al.found;
    if (onProgress) onProgress(i + 1, chapters.length);
    await tick();
  }
  // 3. the chapters' bounds: each runs to the start of the next one placed
  for (var b = 0; b < chapters.length; b++) {
    if (t0s[b] === undefined) continue;
    var en = end;
    for (var b2 = b + 1; b2 < chapters.length; b2++) if (t0s[b2] !== undefined) { en = t0s[b2]; break; }
    res.bounds[String(b)] = { start: Math.round(t0s[b]), end: Math.round(en) };
    res.chaptersFound++;
  }
  var frac = res.chaptersFound / Math.max(chapters.length, 1);
  if (frac < 0.5) { res.why = "Only " + res.chaptersFound + " of " + chapters.length + " chapters were found in the subtitles."; return res; }
  res.ok = true;
  if (frac < 0.85) res.why = res.chaptersFound + " of " + chapters.length + " chapters were found; the rest have no jump points.";
  return res;
}
