// Transcript ↔ FB2 alignment engine.
//
// Given an audiobook chapter transcript (ASR word timings + sentence fragments)
// and the book's FB2 source text, this locates the chapter inside the FB2 and
// produces a list of *discrepancies*, each classified as:
//
//   - "sub"     : transcript word(s) differ from FB2 word(s).
//                 High-confidence = ASR mishearing → fix the JSON to match FB2.
//                 Low-confidence  = the narration genuinely differs (variant).
//   - "missing" : transcript has text absent from the FB2 → candidate to INSERT
//                 into the FB2 (the case Dave flagged for «Лето»).
//   - "omitted" : FB2 has text the audio never speaks → the recording is
//                 abridged there (informational; e.g. Crime & Punishment).
//
// Nothing here writes files. scanChapter() returns discrepancies for review;
// applyTranscriptEdits() / applyFb2Insertions() produce *new file contents*
// from a set of admin-approved edits, which the endpoint then commits.

// ---------------------------------------------------------------------------
// Normalization (mirrors normWordForAlign in the app: lowercase, ё→е, strip
// everything that isn't a Cyrillic/Latin letter or digit).
// ---------------------------------------------------------------------------
function normWord(s) {
  return String(s == null ? "" : s)
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[^а-яa-z0-9]/g, "");
}

// Split leading / trailing punctuation off a raw word so we can swap the core
// while preserving the transcript's own punctuation (…«Гаретовка.» → «Горетовка.»).
function splitAffix(raw) {
  const s = String(raw == null ? "" : raw);
  const m = s.match(/^([^а-яёa-z0-9]*)(.*?)([^а-яёa-z0-9]*)$/i);
  if (!m) return { pre: "", core: s, post: "" };
  return { pre: m[1] || "", core: m[2] || "", post: m[3] || "" };
}

function levenshtein(a, b) {
  a = a || ""; b = b || "";
  if (a === b) return 0;
  const m = a.length, n = b.length;
  if (!m) return n; if (!n) return m;
  let prev = new Array(n + 1), cur = new Array(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;
  for (let i = 1; i <= m; i++) {
    cur[0] = i;
    const ai = a.charCodeAt(i - 1);
    for (let j = 1; j <= n; j++) {
      const cost = ai === b.charCodeAt(j - 1) ? 0 : 1;
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
    }
    const t = prev; prev = cur; cur = t;
  }
  return prev[n];
}

// ---------------------------------------------------------------------------
// FB2 parsing. We operate on the ORIGINAL raw string (no stripping) so that
// paragraph offsets stay valid for insertion. Binaries live outside <body>,
// so a within-body scan never touches them.
// ---------------------------------------------------------------------------
function decodeEntities(s) {
  return String(s)
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, function (_, d) { return String.fromCharCode(parseInt(d, 10)); })
    .replace(/&#x([0-9a-fA-F]+);/g, function (_, h) { return String.fromCharCode(parseInt(h, 16)); })
    .replace(/&amp;/g, "&");
}

// Returns { bodyStart, bodyEnd, paras } where each para is
// { rawStart, rawEnd, innerRaw, text, kind } with absolute offsets into `raw`.
function parseFb2(raw) {
  raw = String(raw || "");
  // Choose the main <body> (skip name="notes"/"comments").
  const bodyRe = /<body\b([^>]*)>([\s\S]*?)<\/body>/g;
  let chosen = null, m;
  while ((m = bodyRe.exec(raw))) {
    const attrs = m[1] || "";
    if (/name\s*=\s*["'](notes|comments)["']/i.test(attrs)) continue;
    chosen = { innerStart: m.index + m[0].indexOf(">", 0) + 1, whole: m, inner: m[2], start: m.index };
    break;
  }
  if (!chosen) {
    // fall back to first body
    bodyRe.lastIndex = 0;
    m = bodyRe.exec(raw);
    if (!m) return { bodyStart: 0, bodyEnd: 0, paras: [] };
    chosen = { whole: m, inner: m[2], start: m.index };
  }
  // Absolute offset where the body inner content begins.
  const bodyOpenTag = chosen.whole[0].match(/^<body\b[^>]*>/)[0];
  const bodyInnerStart = chosen.start + bodyOpenTag.length;
  const bodyInnerEnd = bodyInnerStart + chosen.inner.length;

  const paras = [];
  const elRe = /<(p|subtitle|title)\b[^>]*>([\s\S]*?)<\/\1>/g;
  let e;
  while ((e = elRe.exec(chosen.inner))) {
    const innerRaw = e[2];
    let text = decodeEntities(innerRaw.replace(/<[^>]+>/g, " "));
    text = text.replace(/\s+/g, " ").trim();
    if (!text) continue;
    paras.push({
      rawStart: bodyInnerStart + e.index,           // start of "<p ...>"
      rawEnd:   bodyInnerStart + e.index + e[0].length, // just past "</p>"
      innerRaw: innerRaw,
      text:     text,
      kind:     e[1],
    });
  }
  return { bodyStart: bodyInnerStart, bodyEnd: bodyInnerEnd, paras };
}

// FB2 token stream: { norm, raw, paraIdx }. Skips tokens that normalize empty.
function tokenizeFb2(parsed) {
  const toks = [];
  for (let pi = 0; pi < parsed.paras.length; pi++) {
    const words = parsed.paras[pi].text.split(/\s+/);
    for (let w = 0; w < words.length; w++) {
      const n = normWord(words[w]);
      if (n) toks.push({ norm: n, raw: words[w], paraIdx: pi });
    }
  }
  return toks;
}

// ---------------------------------------------------------------------------
// Transcript tokenizing. Source of truth = fragments[].words (each has
// begin/end). We tag every token with its fragment + in-fragment word index so
// edits map back precisely.
// ---------------------------------------------------------------------------
function tokenizeTranscript(js) {
  const toks = [];
  const frags = (js && Array.isArray(js.fragments)) ? js.fragments : [];
  for (let fi = 0; fi < frags.length; fi++) {
    const ws = Array.isArray(frags[fi].words) ? frags[fi].words : [];
    for (let wi = 0; wi < ws.length; wi++) {
      const n = normWord(ws[wi] && ws[wi].word);
      if (n) toks.push({ norm: n, raw: ws[wi].word, fragIdx: fi, wIdx: wi });
    }
  }
  return toks;
}

// Rebuild a fragment's display text from its words. Words carry their own
// punctuation, so a space-join reproduces the original in the common case;
// we suppress the space before pure-punctuation tokens and closing marks.
function smartJoin(words) {
  let out = "";
  for (let i = 0; i < words.length; i++) {
    const t = String(words[i] && words[i].word != null ? words[i].word : "");
    if (!out) { out = t; continue; }
    if (/^[.,!?;:»)\]…%"'-]/.test(t) || /[«([]$/.test(out)) out += t;
    else out += " " + t;
  }
  return out;
}

// ---------------------------------------------------------------------------
// Myers O(ND) diff over two token arrays (compared by .norm). Returns opcodes
// [{tag,i1,i2,j1,j2}] with tags equal|replace|insert|delete (a = FB2 span,
// b = transcript). Near-identical inputs → small D → fast.
// ---------------------------------------------------------------------------
function myersDiff(a, b) {
  const N = a.length, M = b.length;
  const eq = function (i, j) { return a[i].norm === b[j].norm; };
  const MAX = N + M;
  if (MAX === 0) return [];
  const offset = MAX;
  const v = new Int32Array(2 * MAX + 1);
  const trace = [];
  let reached = -1;
  for (let d = 0; d <= MAX; d++) {
    trace.push(v.slice(0));
    for (let k = -d; k <= d; k += 2) {
      let x;
      if (k === -d || (k !== d && v[offset + k - 1] < v[offset + k + 1])) {
        x = v[offset + k + 1];
      } else {
        x = v[offset + k - 1] + 1;
      }
      let y = x - k;
      while (x < N && y < M && eq(x, y)) { x++; y++; }
      v[offset + k] = x;
      if (x >= N && y >= M) { reached = d; break; }
    }
    if (reached >= 0) break;
  }
  // Backtrack into a script of moves.
  const script = []; // {type:'=','-','+', i, j}
  let x = N, y = M;
  for (let d = reached; d > 0; d--) {
    const vPrev = trace[d];
    const k = x - y;
    let prevK;
    if (k === -d || (k !== d && vPrev[offset + k - 1] < vPrev[offset + k + 1])) prevK = k + 1;
    else prevK = k - 1;
    const prevX = vPrev[offset + prevK];
    const prevY = prevX - prevK;
    while (x > prevX && y > prevY) { script.push({ type: "=", i: x - 1, j: y - 1 }); x--; y--; }
    if (d > 0) {
      if (x === prevX) { script.push({ type: "+", j: y - 1 }); y--; }
      else { script.push({ type: "-", i: x - 1 }); x--; }
    }
  }
  while (x > 0 && y > 0) { script.push({ type: "=", i: x - 1, j: y - 1 }); x--; y--; }
  while (x > 0) { script.push({ type: "-", i: x - 1 }); x--; }
  while (y > 0) { script.push({ type: "+", j: y - 1 }); y--; }
  script.reverse();

  // Coalesce into opcodes.
  const ops = [];
  let i = 0, j = 0, s = 0;
  while (s < script.length) {
    const t = script[s].type;
    if (t === "=") {
      const i1 = i, j1 = j;
      while (s < script.length && script[s].type === "=") { i++; j++; s++; }
      ops.push({ tag: "equal", i1: i1, i2: i, j1: j1, j2: j });
    } else {
      const i1 = i, j1 = j;
      let dels = 0, ins = 0;
      while (s < script.length && script[s].type !== "=") {
        if (script[s].type === "-") { i++; dels++; } else { j++; ins++; }
        s++;
      }
      let tag = "replace";
      if (dels === 0) tag = "insert";
      else if (ins === 0) tag = "delete";
      ops.push({ tag: tag, i1: i1, i2: i, j1: j1, j2: j });
    }
  }
  return ops;
}

// Merge non-equal opcodes separated by <= gap equal tokens into single regions.
function mergeOps(ops, gap) {
  gap = gap == null ? 2 : gap;
  const regions = [];
  for (let k = 0; k < ops.length; k++) {
    if (ops[k].tag === "equal") continue;
    const o = ops[k];
    const last = regions[regions.length - 1];
    if (last && (o.i1 - last.i2) <= gap && (o.j1 - last.j2) <= gap) {
      last.i2 = o.i2; last.j2 = o.j2;
    } else {
      regions.push({ i1: o.i1, i2: o.i2, j1: o.j1, j2: o.j2 });
    }
  }
  return regions;
}

// ---------------------------------------------------------------------------
// Anchor a chapter transcript inside the full FB2 token stream. Returns
// { start, end, ok }. Uses n-gram matching biased toward the expected position.
// ---------------------------------------------------------------------------
function findNgram(hayNorm, needleNorm, prior) {
  const k = needleNorm.length;
  if (k === 0 || hayNorm.length < k) return -1;
  const hits = [];
  for (let i = 0; i + k <= hayNorm.length; i++) {
    let ok = true;
    for (let t = 0; t < k; t++) { if (hayNorm[i + t] !== needleNorm[t]) { ok = false; break; } }
    if (ok) { hits.push(i); if (hits.length > 64) break; }
  }
  if (!hits.length) return -1;
  if (prior == null) return hits[0];
  let best = hits[0], bd = Math.abs(hits[0] - prior);
  for (let h = 1; h < hits.length; h++) {
    const d = Math.abs(hits[h] - prior);
    if (d < bd) { bd = d; best = hits[h]; }
  }
  return best;
}

function anchorChapter(fbToks, trToks, chapterIndex, totalChapters) {
  const fbNorm = fbToks.map(function (t) { return t.norm; });
  const trNorm = trToks.map(function (t) { return t.norm; });
  const K = 6;
  const prior = (totalChapters && totalChapters > 0)
    ? Math.round((chapterIndex / totalChapters) * fbNorm.length) : null;

  // Head anchor: slide the window's start offset a bit in case the opening
  // words differ (titles, ASR junk at the very start).
  let start = -1;
  for (let off = 0; off < 40 && off + K <= trNorm.length; off++) {
    const pos = findNgram(fbNorm, trNorm.slice(off, off + K), prior);
    if (pos >= 0) { start = pos - off; break; }
  }
  // Tail anchor.
  let end = -1;
  for (let off = 0; off < 40 && trNorm.length - K - off >= 0; off++) {
    const needle = trNorm.slice(trNorm.length - K - off, trNorm.length - off);
    const priorEnd = (prior == null) ? null : prior + trNorm.length;
    const pos = findNgram(fbNorm, needle, priorEnd);
    if (pos >= 0) { end = pos + K + off; break; }
  }
  let ok = true;
  if (start < 0) { start = (prior == null ? 0 : Math.max(0, prior)); ok = false; }
  if (end < 0 || end <= start) { end = Math.min(fbNorm.length, start + Math.round(trNorm.length * 1.25)); ok = false; }
  if (start < 0) start = 0;
  if (end > fbNorm.length) end = fbNorm.length;
  return { start: start, end: end, ok: ok };
}

// ---------------------------------------------------------------------------
// Classify one merged region into a discrepancy object.
// ---------------------------------------------------------------------------
const STOP = { "и": 1, "в": 1, "во": 1, "не": 1, "на": 1, "я": 1, "а": 1, "с": 1, "к": 1, "у": 1, "о": 1, "же": 1, "бы": 1, "ли": 1, "то": 1, "по": 1, "из": 1, "за": 1, "от": 1};

function contentLen(toks) {
  let c = 0;
  for (let i = 0; i < toks.length; i++) if (!STOP[toks[i].norm] && toks[i].norm.length > 1) c++;
  return c;
}

function classifyRegion(region, fbToks, trToks, spanStart) {
  const fb = [];
  for (let i = region.i1; i < region.i2; i++) fb.push(fbToks[spanStart + i]);
  const tr = [];
  for (let j = region.j1; j < region.j2; j++) tr.push(trToks[j]);

  const fbRaw = fb.map(function (t) { return t.raw; }).join(" ");
  const trRaw = tr.map(function (t) { return t.raw; }).join(" ");
  const fbN = fb.map(function (t) { return t.norm; }).join("");
  const trN = tr.map(function (t) { return t.norm; }).join("");
  if (fbN === trN) return null; // normalize-equal → not a real discrepancy

  const base = { fbText: fbRaw, trText: trRaw, fbCount: fb.length, trCount: tr.length };

  // Pure insert: transcript has content the FB2 lacks.
  if (fb.length === 0) {
    const cl = contentLen(tr);
    return Object.assign(base, {
      kind: "missing",
      confidence: cl >= 3 ? "high" : (cl >= 1 ? "med" : "low"),
      suggest: cl >= 1 ? "insertFb2" : "ignore",
      needsAI: cl >= 1 && cl < 3,
      // where to insert: between FB2 token (spanStart+region.i1-1) and next
      fbAnchorTokenIndex: spanStart + region.i1,
    });
  }
  // Pure delete: FB2 has content the audio never speaks (abridged).
  if (tr.length === 0) {
    const cl = contentLen(fb);
    return Object.assign(base, {
      kind: "omitted",
      confidence: cl >= 3 ? "high" : "low",
      suggest: "info",
      needsAI: false,
    });
  }
  // Replacement.
  const lev = levenshtein(fbN, trN);
  const maxLen = Math.max(fbN.length, trN.length);
  const sim = maxLen ? 1 - lev / maxLen : 1;
  let confidence, needsAI, suggest = "fixJson";
  if (fb.length === tr.length && lev <= 2) { confidence = "high"; needsAI = false; }
  else if (sim >= 0.6) { confidence = "med"; needsAI = false; }
  else { confidence = "low"; needsAI = true; suggest = "review"; }

  // Per-word target pairing when counts match (enables precise JSON fix).
  let target = null;
  if (fb.length === tr.length) {
    target = [];
    for (let n = 0; n < tr.length; n++) {
      const aff = splitAffix(tr[n].raw);
      const fbAff = splitAffix(fb[n].raw);
      target.push({
        fragIdx: tr[n].fragIdx, wIdx: tr[n].wIdx,
        oldWord: tr[n].raw,
        newWord: aff.pre + fbAff.core + aff.post, // FB2 core, transcript punctuation
      });
    }
  }
  return Object.assign(base, {
    kind: "sub", confidence: confidence, needsAI: needsAI, suggest: suggest,
    similarity: Math.round(sim * 100) / 100,
    target: target, // null when counts differ → UI offers manual/whole-run replace
    // fallback whole-run replace info (single fragment only)
    run: singleFragmentRun(tr),
    fbWords: fb.map(function (t) { return splitAffix(t.raw).core; }),
  });
}

// If a transcript run sits inside one fragment, return {fragIdx,wStart,wEnd}.
function singleFragmentRun(tr) {
  if (!tr.length) return null;
  const fi = tr[0].fragIdx;
  for (let i = 1; i < tr.length; i++) if (tr[i].fragIdx !== fi) return null;
  let wStart = tr[0].wIdx, wEnd = tr[0].wIdx;
  for (let i = 0; i < tr.length; i++) {
    if (tr[i].wIdx < wStart) wStart = tr[i].wIdx;
    if (tr[i].wIdx > wEnd) wEnd = tr[i].wIdx;
  }
  return { fragIdx: fi, wStart: wStart, wEnd: wEnd };
}

// Detect whether a transcript run's words already appear (even in ASR-garbled
// form) as a cluster somewhere in the FB2. Used to suppress FALSE "missing"
// insertions: repeated phrases/refrains (e.g. a recurring lullaby) that the
// local anchored diff failed to match, and which would otherwise be proposed
// for insertion into text that already contains them. Anchors on the run's most
// distinctive (longest) content word, then measures multiset overlap in a
// window around each occurrence — order- and typo-tolerant.
function runPresentInFb2(runNorms, fbNorms) {
  const content = runNorms.filter(function (w) { return w.length >= 3 && !STOP[w]; });
  if (content.length < 2 || runNorms.length < 3) return false;
  let pivot = content[0];
  for (let i = 1; i < content.length; i++) if (content[i].length > pivot.length) pivot = content[i];
  const runCounts = {};
  runNorms.forEach(function (w) { runCounts[w] = (runCounts[w] || 0) + 1; });
  let total = 0; for (const w in runCounts) total += runCounts[w];
  const m = runNorms.length;
  for (let i = 0; i < fbNorms.length; i++) {
    if (fbNorms[i] !== pivot) continue;
    const a = Math.max(0, i - m), b = Math.min(fbNorms.length, i + m);
    const wc = {};
    for (let j = a; j < b; j++) wc[fbNorms[j]] = (wc[fbNorms[j]] || 0) + 1;
    let overlap = 0;
    for (const w in runCounts) overlap += Math.min(runCounts[w], wc[w] || 0);
    if (total > 0 && overlap / total >= 0.6) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// scanChapter: full pipeline for one chapter. Returns discrepancies + summary.
// ---------------------------------------------------------------------------
function scanChapter(fb2Parsed, fbToks, transcriptJson, chapterIndex, totalChapters) {
  const trToks = tokenizeTranscript(transcriptJson);
  if (!trToks.length) {
    return { ok: false, error: "empty transcript", discrepancies: [], summary: {}, anchor: null };
  }
  const anchor = anchorChapter(fbToks, trToks, chapterIndex, totalChapters);
  const span = fbToks.slice(anchor.start, anchor.end);
  const ops = myersDiff(span, trToks);
  // match ratio
  let eqCount = 0;
  for (let k = 0; k < ops.length; k++) if (ops[k].tag === "equal") eqCount += (ops[k].i2 - ops[k].i1);
  const ratio = trToks.length ? eqCount / Math.max(span.length, trToks.length) : 0;

  const regions = mergeOps(ops, 2);
  const fbNorms = fbToks.map(function (t) { return t.norm; });
  const discrepancies = [];
  let idc = 0;
  const ctxRaw = function (toks, a, b) {
    const out = [];
    for (let i = Math.max(0, a); i < Math.min(toks.length, b); i++) out.push(toks[i].raw);
    return out.join(" ");
  };
  for (let r = 0; r < regions.length; r++) {
    const d = classifyRegion(regions[r], fbToks, trToks, anchor.start);
    if (!d) continue;
    d.id = "d" + (idc++);
    d.chapterIndex = chapterIndex;
    // Absolute token spans (for apply + context).
    d.fbStart = anchor.start + regions[r].i1;
    d.fbEnd = anchor.start + regions[r].i2;
    d.trStart = regions[r].j1;
    d.trEnd = regions[r].j2;
    // Guard against FALSE "missing" insertions: if the transcript run's text
    // already appears in the FB2 (a repeated phrase the diff mis-aligned),
    // don't propose inserting it — flag it and drop it out of the actionable set.
    if (d.kind === "missing") {
      const runNorms = [];
      for (let j = d.trStart; j < d.trEnd; j++) if (trToks[j]) runNorms.push(trToks[j].norm);
      if (runPresentInFb2(runNorms, fbNorms)) {
        d.inBook = true;
        d.suggest = "ignore";
        d.confidence = "low";
        d.needsAI = false;
        d.note = "This text already appears in the book — likely an alignment artifact from a repeated phrase, not a genuinely missing sentence.";
      }
    }
    // A few words of surrounding context from each side, for the review UI.
    d.fbContextBefore = ctxRaw(fbToks, d.fbStart - 6, d.fbStart);
    d.fbContextAfter = ctxRaw(fbToks, d.fbEnd, d.fbEnd + 6);
    d.trContextBefore = ctxRaw(trToks, d.trStart - 6, d.trStart);
    d.trContextAfter = ctxRaw(trToks, d.trEnd, d.trEnd + 6);
    // Insertion target paragraph (relevant to "missing").
    const afterPara = paraForInsertion(fbToks, (d.fbAnchorTokenIndex != null ? d.fbAnchorTokenIndex : d.fbStart));
    d.afterParaIdx = afterPara;
    d.afterParaPreview = (fb2Parsed.paras[afterPara] ? fb2Parsed.paras[afterPara].text : "").slice(-90);
    discrepancies.push(d);
  }
  const summary = { sub: 0, missing: 0, omitted: 0, high: 0, med: 0, low: 0, needsAI: 0 };
  for (let d = 0; d < discrepancies.length; d++) {
    const x = discrepancies[d];
    summary[x.kind] = (summary[x.kind] || 0) + 1;
    summary[x.confidence] = (summary[x.confidence] || 0) + 1;
    if (x.needsAI) summary.needsAI++;
  }
  summary.total = discrepancies.length;
  summary.ratio = Math.round(ratio * 1000) / 1000;
  return { ok: anchor.ok, anchor: anchor, discrepancies: discrepancies, summary: summary };
}

// ---------------------------------------------------------------------------
// APPLY: transcript JSON edits. edits = [{fragIdx, wIdx, newWord}] (per-word,
// counts-matched subs) and/or [{run:{fragIdx,wStart,wEnd}, newWords:[...]}]
// (whole-run replace). Returns the mutated JSON object (caller re-serializes).
// word_timings is rebuilt from fragments so the two stay consistent.
// ---------------------------------------------------------------------------
function applyTranscriptEdits(js, edits) {
  const frags = js.fragments;

  // Snapshot each fragment's timing envelope + per-word (begin,end) signature so
  // we can prove afterwards that we only disturbed the fragments we meant to.
  const snap = frags.map(function (f) {
    const ws = (f && f.words) || [];
    return {
      begin: ws.length ? ws[0].begin : null,
      end:   ws.length ? ws[ws.length - 1].end : null,
      sig:   ws.map(function (w) { return w.begin + ":" + w.end; }).join("|"),
    };
  });
  const editedSet = {};

  let changed = 0;
  for (let e = 0; e < edits.length; e++) {
    const ed = edits[e];
    if (ed.run) {
      const f = frags[ed.run.fragIdx];
      if (!f || !Array.isArray(f.words)) continue;
      const a = ed.run.wStart, b = ed.run.wEnd;
      const oldSlice = f.words.slice(a, b + 1);
      if (!oldSlice.length) continue;
      const begin = oldSlice[0].begin, end = oldSlice[oldSlice.length - 1].end;
      const nw = ed.newWords && ed.newWords.length ? ed.newWords : [smartJoin(oldSlice)];
      const step = (end - begin) / nw.length;
      const inserted = [];
      for (let n = 0; n < nw.length; n++) {
        inserted.push({ word: nw[n], begin: +(begin + step * n).toFixed(3), end: +(begin + step * (n + 1)).toFixed(3) });
      }
      f.words = f.words.slice(0, a).concat(inserted, f.words.slice(b + 1));
      f.text = smartJoin(f.words);
      editedSet[ed.run.fragIdx] = true;
      changed++;
    } else {
      const f = frags[ed.fragIdx];
      if (!f || !Array.isArray(f.words) || !f.words[ed.wIdx]) continue;
      f.words[ed.wIdx].word = ed.newWord;
      f.text = smartJoin(f.words);
      editedSet[ed.fragIdx] = true;
      changed++;
    }
  }
  // Rebuild flat word_timings from fragments.
  const wt = [];
  for (let fi = 0; fi < frags.length; fi++) {
    const ws = frags[fi].words || [];
    for (let wi = 0; wi < ws.length; wi++) {
      wt.push({ word: ws[wi].word, begin: ws[wi].begin, end: ws[wi].end });
    }
  }
  js.word_timings = wt;

  const integrity = validateTimingIntegrity(frags, snap, editedSet);
  return { js: js, changed: changed, integrity: integrity };
}

// Prove that an edit didn't corrupt timings:
//   1. Fragments we did NOT edit keep byte-identical (begin,end) for every word.
//   2. Edited fragments stay monotonic (begin <= end, begins non-decreasing) and
//      within their original time envelope (no word starts before the fragment
//      used to start, or ends after it used to end — so playback can't drift).
//   3. Globally, begins are non-decreasing across the whole chapter.
// Returns { ok, error }. On failure the caller must NOT commit the file.
function validateTimingIntegrity(frags, snap, editedSet) {
  const EPS = 0.051; // rounding tolerance (timings are stored to 3 decimals)
  let lastBegin = -Infinity;
  for (let fi = 0; fi < frags.length; fi++) {
    const ws = (frags[fi] && frags[fi].words) || [];
    const s = snap[fi] || {};
    if (!editedSet[fi]) {
      // untouched fragment — timing signature must be unchanged
      const sig = ws.map(function (w) { return w.begin + ":" + w.end; }).join("|");
      if (sig !== s.sig) return { ok: false, error: "timing changed in an unedited fragment #" + fi };
    } else {
      for (let wi = 0; wi < ws.length; wi++) {
        const w = ws[wi];
        if (typeof w.begin !== "number" || typeof w.end !== "number" || isNaN(w.begin) || isNaN(w.end))
          return { ok: false, error: "non-numeric timing in fragment #" + fi };
        if (w.end + EPS < w.begin) return { ok: false, error: "end<begin in fragment #" + fi };
        if (s.begin != null && w.begin + EPS < s.begin) return { ok: false, error: "word starts before fragment envelope #" + fi };
        if (s.end != null && w.end - EPS > s.end) return { ok: false, error: "word ends after fragment envelope #" + fi };
      }
    }
    for (let wi = 0; wi < ws.length; wi++) {
      if (ws[wi].begin + EPS < lastBegin) return { ok: false, error: "non-monotonic begin at fragment #" + fi };
      lastBegin = Math.max(lastBegin, ws[wi].begin);
    }
  }
  return { ok: true, error: "" };
}

// ---------------------------------------------------------------------------
// APPLY: FB2 insertions. inserts = [{afterParaIdx, text}] — insert a new <p>
// after the given paragraph's raw end. We sort descending by offset so earlier
// splices don't shift later ones. Returns new raw FB2 string.
// ---------------------------------------------------------------------------
function applyFb2Insertions(raw, parsed, inserts) {
  const items = inserts.slice().filter(function (x) { return x && x.text && x.afterParaIdx != null && parsed.paras[x.afterParaIdx]; });
  items.sort(function (a, b) { return parsed.paras[b.afterParaIdx].rawEnd - parsed.paras[a.afterParaIdx].rawEnd; });
  let out = raw;
  for (let i = 0; i < items.length; i++) {
    const p = parsed.paras[items[i].afterParaIdx];
    const esc = String(items[i].text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const ins = "\n<p>" + esc + "</p>";
    out = out.slice(0, p.rawEnd) + ins + out.slice(p.rawEnd);
  }
  return { raw: out, count: items.length };
}

// Given a discrepancy's fbAnchorTokenIndex, resolve which paragraph to insert
// after (the paragraph of the token just before the insertion point).
function paraForInsertion(fbToks, fbAnchorTokenIndex) {
  const idx = Math.max(0, Math.min(fbAnchorTokenIndex - 1, fbToks.length - 1));
  const t = fbToks[idx];
  return t ? t.paraIdx : 0;
}

export {
  normWord, splitAffix, levenshtein, decodeEntities,
  parseFb2, tokenizeFb2, tokenizeTranscript, smartJoin,
  myersDiff, mergeOps, anchorChapter, classifyRegion, scanChapter,
  applyTranscriptEdits, applyFb2Insertions, paraForInsertion, findNgram,
  validateTimingIntegrity,
};
