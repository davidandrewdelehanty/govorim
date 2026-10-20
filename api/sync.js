// api/sync.js — where each chapter of the reader's own book starts inside the
// recording they pasted beside it, worked out from the recording's subtitles.
//
// This is the catalogue's tools/place_picks.py + tools/vtt_tokens.py, which
// placed fifty-odd library books, carried over to JavaScript so a reader's
// own book can have the same thing — with one difference in what it keeps,
// which is nothing:
//
//   * the subtitles are fetched from YouTube (or come in the request, pasted)
//     and live only for the length of this call. They are not written to R2,
//     not cached, not logged;
//   * the book never comes here whole. The reader's browser sends only the
//     first few paragraphs of each chapter — the words a narrator says when the
//     chapter begins — and nothing else of the text;
//   * the answer goes back to the browser, which stores it in its own
//     localStorage beside the link (gv_own_video_v1). The server has no copy.
//
//   POST /api/sync
//     { youtube: "<id>", captions: true }                           fetch only:
//        → { ok, cues: [[seconds, "words"], …], seconds, auto, lang }
//       The browser does the placing itself now (src/ownsync.js), for every
//       paragraph of the book, so the book text need not come here at all.
//     { youtube: "<id>", chapters: [["para", "para", …], …] }      fetch + place
//     { transcript: "<vtt | srt | json3 | pasted>", chapters: … }  place only
//
//   → { ok, found, chapters, median, rate, end, starts: [{start, score} | null, …], why? }
//
// `starts` is per chapter; a null is a chapter whose opening was not found.
// `ok` is false when the recording does not look like a reading of this book
// (too few chapters found, weak matches, or a seconds-per-word rate no
// narration has) — the starts still come back so the reader can see why.
import { currentUser } from "../lib/auth.js";
import { isPublicSite } from "../lib/site.js";

// The same thresholds that decide whether a hunted recording is placed in the
// catalogue. A reader's own recording is judged by the same standard and told
// plainly when it fails it.
const MIN_MEDIAN_SCORE = 0.70;
const MIN_FOUND_FRAC = 0.85;
const RATE_LO = 0.35, RATE_HI = 0.90;
const MAX_CHAPTERS = 2000;
// Vercel caps a request body at 4.5 MB; a twelve-hour reading's subtitles are
// a tenth of that.
const MAX_TRANSCRIPT_CHARS = 4 * 1024 * 1024;

// ───────────────────────────────────────────────────────────── transcripts

function norm(w) {
  return String(w || "").toLowerCase().replace(/ё/g, "е").replace(/[^а-я]/g, "");
}

function clock(h, m, s, ms) {
  return (+h || 0) * 3600 + (+m || 0) * 60 + (+s || 0) + (+(String(ms || "0").slice(0, 3).padEnd(3, "0"))) / 1000;
}

// Cues out of whatever came in: WebVTT, SRT, YouTube's json3, or the text a
// reader copies out of YouTube's own "Show transcript" panel ("0:00" on a
// line, the words on the next). Each cue is [seconds, text].
function parseCues(raw) {
  const s = String(raw || "");
  // json3
  if (/^\s*\{/.test(s)) {
    try {
      const j = JSON.parse(s);
      const ev = Array.isArray(j.events) ? j.events : [];
      const out = [];
      for (const e of ev) {
        const txt = (e.segs || []).map(x => x.utf8 || "").join("").replace(/\s+/g, " ").trim();
        if (txt && typeof e.tStartMs === "number") out.push([e.tStartMs / 1000, txt]);
      }
      return out;
    } catch { /* fall through */ }
  }
  const out = [];
  // VTT / SRT: a timing line, then the text until a blank line.
  if (/-->/.test(s)) {
    for (const blk of s.replace(/\r/g, "").split(/\n\s*\n/)) {
      const m = blk.match(/(?:(\d+):)?(\d\d):(\d\d)[.,](\d+)\s+-->/);
      if (!m) continue;
      const t = clock(m[1], m[2], m[3], m[4]);
      let txt = blk.slice(blk.indexOf("-->"));
      txt = txt.replace(/^[^\n]*\n?/, "");          // the rest of the timing line
      txt = txt.replace(/<[^>]*>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");
      txt = txt.replace(/\s+/g, " ").trim();
      if (txt) out.push([t, txt]);
    }
    return out;
  }
  // "Show transcript" paste: "0:00" / "1:02:03" alone or at the start of a line.
  const lines = s.replace(/\r/g, "").split("\n");
  let t = null, buf = [];
  const flush = () => { if (t !== null && buf.length) out.push([t, buf.join(" ").replace(/\s+/g, " ").trim()]); buf = []; };
  for (const line of lines) {
    const m = line.match(/^\s*(?:(\d+):)?(\d{1,2}):(\d{2})\s*(.*)$/);
    if (m) { flush(); t = clock(m[1], m[2], m[3], 0); if (m[4].trim()) buf.push(m[4].trim()); }
    else if (line.trim()) buf.push(line.trim());
  }
  flush();
  return out;
}

// Timed words. Rolling captions repeat the previous line, so each cue
// contributes only its new tail; and those new words are spread evenly from
// this cue's start to the next cue's, since that span is when they were
// actually spoken — stamping them all with the cue's start put a word that
// arrives late in a five-second cue five seconds early, which is exactly the
// "jumps a few seconds before the word" a reader feels.
function tokens(cues) {
  const toks = [];
  for (let ci = 0; ci < cues.length; ci++) {
    const [t, txt] = cues[ci];
    let ws = txt.split(/\s+/).filter(Boolean);
    if (toks.length) {
      const prev = toks.slice(-40).map(x => x[1]);
      let best = 0;
      for (let k = Math.min(ws.length, prev.length); k > 0; k--) {
        let same = true;
        for (let i = 0; i < k; i++) if (prev[prev.length - k + i] !== ws[i]) { same = false; break; }
        if (same) { best = k; break; }
      }
      ws = ws.slice(best);
    }
    if (!ws.length) continue;
    const tNext = ci + 1 < cues.length ? cues[ci + 1][0] : t + 4.0;
    const span = Math.max(0.5, tNext - t);
    for (let wi = 0; wi < ws.length; wi++) toks.push([t + span * wi / ws.length, ws[wi]]);
  }
  return toks;
}

// ───────────────────────────────────────────────────────────── YouTube

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

// The caption tracks of a video, asked for the way the apps ask (the
// innertube player call), which answers from a datacenter far more readily
// than the watch page does; the watch page is the fallback.
async function captionTracks(videoId) {
  try {
    const r = await fetch("https://www.youtube.com/youtubei/v1/player?prettyPrint=false", {
      method: "POST",
      headers: { "content-type": "application/json", "user-agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip" },
      body: JSON.stringify({ videoId, context: { client: { clientName: "ANDROID", clientVersion: "19.09.37", androidSdkVersion: 30, hl: "ru", gl: "RU" } } }),
    });
    if (r.ok) {
      const j = await r.json();
      const tr = j && j.captions && j.captions.playerCaptionsTracklistRenderer && j.captions.playerCaptionsTracklistRenderer.captionTracks;
      if (Array.isArray(tr) && tr.length) return { tracks: tr, seconds: +(j.videoDetails && j.videoDetails.lengthSeconds) || 0 };
      if (j && j.playabilityStatus && j.playabilityStatus.status !== "OK") {
        return { error: "YouTube says this video is " + String(j.playabilityStatus.status).toLowerCase() + "." };
      }
    }
  } catch { /* try the page */ }
  try {
    const r = await fetch("https://www.youtube.com/watch?v=" + encodeURIComponent(videoId) + "&hl=ru", {
      headers: { "user-agent": UA, "accept-language": "ru,en;q=0.8", "cookie": "CONSENT=YES+cb; SOCS=CAI" },
    });
    const html = await r.text();
    const m = html.match(/"captionTracks":(\[.*?\])\s*,\s*"/);
    if (m) {
      const tr = JSON.parse(m[1]);
      const lm = html.match(/"lengthSeconds":"(\d+)"/);
      if (tr.length) return { tracks: tr, seconds: lm ? +lm[1] : 0 };
    }
    if (/"captions"/.test(html) === false && /playabilityStatus/.test(html)) return { error: "This video has no subtitles." };
  } catch { /* nothing */ }
  return { error: "YouTube would not hand over the subtitles from here." };
}

// Russian first; a track someone wrote over one YouTube generated; anything
// at all before nothing.
function pickTrack(tracks) {
  const score = t => {
    const lang = String(t.languageCode || "").toLowerCase();
    return (lang.startsWith("ru") ? 10 : 0) + (t.kind === "asr" ? 0 : 1);
  };
  return tracks.slice().sort((a, b) => score(b) - score(a))[0];
}

async function fetchTranscript(videoId) {
  const got = await captionTracks(videoId);
  if (got.error) return got;
  const t = pickTrack(got.tracks);
  if (!t || !t.baseUrl) return { error: "This video has no subtitles." };
  let url = t.baseUrl.replace(/&fmt=[^&]*/, "");
  url += (url.includes("?") ? "&" : "?") + "fmt=json3";
  const r = await fetch(url, { headers: { "user-agent": UA } });
  if (!r.ok) return { error: "YouTube would not hand over the subtitles from here." };
  const body = await r.text();
  if (body.length > MAX_TRANSCRIPT_CHARS) return { error: "The subtitles are too long to read in one go." };
  return { text: body, seconds: got.seconds, auto: t.kind === "asr", lang: t.languageCode || "" };
}

// ───────────────────────────────────────────────────────────── placing

// difflib's ratio: twice the matched words over the words in both, with the
// matches found the Ratcliff/Obershelp way (longest common run, then the same
// on either side). The probes are fourteen words, so there is no junk
// heuristic to reproduce.
function ratio(a, b) {
  if (!a.length && !b.length) return 1;
  let matched = 0;
  const stack = [[0, a.length, 0, b.length]];
  while (stack.length) {
    const [alo, ahi, blo, bhi] = stack.pop();
    let bi = alo, bj = blo, bsz = 0;
    let prev = new Map();
    for (let i = alo; i < ahi; i++) {
      const cur = new Map();
      for (let j = blo; j < bhi; j++) {
        if (a[i] !== b[j]) continue;
        const k = (prev.get(j - 1) || 0) + 1;
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

// Opening phrases to look for, one per early paragraph. A chapter does not
// always begin with words anyone says out loud — several FB2s open with the
// publisher's boilerplate, which a narrator skips — so each of the first few
// paragraphs is offered, and the first one actually spoken is where the audio
// begins.
function probes(paras, n = 4) {
  const out = [];
  for (const para of paras.slice(0, n + 2)) {
    const w = String(para || "").split(/\s+/).map(norm).filter(Boolean);
    if (w.length >= 8) out.push(w.slice(0, 14));
    if (out.length >= n) break;
  }
  if (!out.length) {
    const w = paras.join(" ").split(/\s+/).map(norm).filter(Boolean);
    if (w.length >= 5) out.push(w.slice(0, 14));
  }
  return out;
}

// Where each chapter starts, searched forward so order is structural. The
// transcript is indexed by word once, and only the positions where one of the
// probe's first three words occurs are scored — a few hundred candidates
// rather than the whole transcript, with the same answer.
function locate(chapters, toks) {
  const times = toks.map(x => x[0]);
  const words = toks.map(x => norm(x[1]));
  const where = new Map();
  words.forEach((w, i) => { if (w) { if (!where.has(w)) where.set(w, []); where.get(w).push(i); } });
  const out = [];
  let cur = 0;
  for (const paras of chapters) {
    let best = [0, null, 0];
    for (const op of probes(paras)) {
      if (op.length < 5) continue;
      const cands = new Set();
      for (let k = 0; k < Math.min(3, op.length); k++) {
        for (const j of (where.get(op[k]) || [])) if (j - k >= cur) cands.add(j - k);
      }
      for (const j of Array.from(cands).sort((x, y) => x - y)) {
        if (j + op.length > words.length) continue;
        const r = ratio(words.slice(j, j + op.length), op);
        if (r > best[0]) { best = [r, j, op.length]; if (r > 0.97) break; }
      }
      if (best[0] >= 0.8) break;        // a clear hit on an earlier paragraph wins
    }
    if (best[1] !== null && best[0] >= 0.55) {
      out.push({ start: times[best[1]], score: best[0] });
      cur = best[1] + best[2];
    } else {
      out.push(null);
    }
  }
  return out;
}

function median(xs) {
  if (!xs.length) return 0;
  const s = xs.slice().sort((a, b) => a - b);
  const h = s.length >> 1;
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
}

function assess(chapters, toks, videoSeconds) {
  const vend = Math.max(videoSeconds || 0, toks.length ? toks[toks.length - 1][0] + 4 : 0);
  const found = locate(chapters, toks);
  const hits = found.filter(Boolean);
  const frac = hits.length / chapters.length;
  const med = median(hits.map(h => h.score));
  const res = {
    chapters: chapters.length, found: hits.length, median: +med.toFixed(2), end: Math.round(vend),
    starts: found.map(h => h ? { start: Math.round(h.start), score: +h.score.toFixed(2) } : null),
  };
  if (!hits.length) return Object.assign(res, { ok: false, why: "None of the chapter openings is in these subtitles — is this a reading of the same book?" });
  // The seconds-per-word test needs whole-chapter word counts, which the
  // browser sends separately (`words`); see rateCheck.
  res.rate = null;
  if (frac < MIN_FOUND_FRAC) return Object.assign(res, { ok: false, why: "Only " + hits.length + " of " + chapters.length + " chapter openings were found." });
  if (med < MIN_MEDIAN_SCORE) return Object.assign(res, { ok: false, why: "The chapter openings match the subtitles only weakly (median " + med.toFixed(2) + ") — a different edition, or a different book." });
  return Object.assign(res, { ok: true });
}

function rateCheck(res, chapters, wordCounts) {
  // With real word counts the abridgement test from place_picks can run.
  if (!Array.isArray(wordCounts) || wordCounts.length !== chapters.length) return res;
  const starts = res.starts.map(h => h ? h.start : null);
  const vend = res.end;
  for (let i = 0; i < starts.length; i++) {
    if (starts[i] !== null) continue;
    let prev = 0, nxt = vend;
    for (let j = i - 1; j >= 0; j--) if (starts[j] !== null) { prev = starts[j]; break; }
    for (let j = i + 1; j < starts.length; j++) if (starts[j] !== null) { nxt = starts[j]; break; }
    starts[i] = prev + (nxt - prev) * 0.5;
  }
  const rates = [];
  for (let i = 0; i < starts.length; i++) {
    const s0 = starts[i], s1 = i + 1 < starts.length ? starts[i + 1] : vend;
    rates.push((s1 - s0) / Math.max(1, +wordCounts[i] || 1));
  }
  const rmed = median(rates);
  res.rate = +rmed.toFixed(3);
  if (res.ok && (rmed < RATE_LO || rmed > RATE_HI)) {
    res.ok = false;
    res.why = "The reading runs at " + rmed.toFixed(2) + " seconds a word, which no narration does — an abridgement, or a discussion of the book rather than the book.";
  }
  return res;
}

// ───────────────────────────────────────────────────────────── handler

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store, private");
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  if (!currentUser(req) && !isPublicSite()) return res.status(401).json({ error: "An account is required." });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  body = body || {};

  if (body.captions) {
    // The subtitles themselves, as timed cues, and nothing else: the browser
    // matches the book against them on the reader's own device.
    const id = String(body.youtube || "").trim();
    if (!/^[\w-]{11}$/.test(id)) return res.status(400).json({ error: "No recording to read." });
    const got = await fetchTranscript(id);
    if (got.error) return res.status(200).json({ ok: false, why: got.error, needTranscript: true });
    const cs = parseCues(got.text).map(c => [Math.round(c[0] * 100) / 100, c[1]]);
    if (!cs.length) return res.status(200).json({ ok: false, why: "No subtitles could be read out of that.", needTranscript: true });
    return res.status(200).json({ ok: true, cues: cs, seconds: got.seconds, auto: got.auto, lang: got.lang });
  }

  const chapters = Array.isArray(body.chapters) ? body.chapters : null;
  if (!chapters || !chapters.length) return res.status(400).json({ error: "No chapters." });
  if (chapters.length > MAX_CHAPTERS) return res.status(400).json({ error: "Too many chapters." });
  const chs = chapters.map(c => (Array.isArray(c) ? c : [String(c || "")]).slice(0, 8).map(p => String(p || "").slice(0, 600)));

  let text = "", seconds = 0, auto = null, lang = "";
  if (typeof body.transcript === "string" && body.transcript.trim()) {
    if (body.transcript.length > MAX_TRANSCRIPT_CHARS) return res.status(400).json({ error: "That transcript is too long." });
    text = body.transcript;
  } else {
    const id = String(body.youtube || "").trim();
    if (!/^[\w-]{11}$/.test(id)) return res.status(400).json({ error: "No recording to read." });
    const got = await fetchTranscript(id);
    if (got.error) return res.status(200).json({ ok: false, why: got.error, needTranscript: true });
    text = got.text; seconds = got.seconds; auto = got.auto; lang = got.lang;
  }

  const cues = parseCues(text);
  text = null;                       // nothing below needs it, and it is gone with the call
  if (!cues.length) return res.status(200).json({ ok: false, why: "No subtitles could be read out of that.", needTranscript: true });
  const toks = tokens(cues);
  if (toks.length < 50) return res.status(200).json({ ok: false, why: "The subtitles are too short to place anything.", needTranscript: true });

  let out = assess(chs, toks, seconds);
  out = rateCheck(out, chs, body.words);
  out.auto = auto; out.lang = lang; out.tokens = toks.length;
  return res.status(200).json(out);
}
