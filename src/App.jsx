// THEME_VERSION=2
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { isCommonWord, dropCommonWords } from "./commonWords.js";

// localStorage-backed storage shim, matching the previous window.storage Promise API.
// Keeps the rest of the app code unchanged (still uses await storage.get/set/delete).
// All spoken Russian (chat 🔊 Listen, book reading) uses the browser's built-in
// speechSynthesis voices — no paid cloud TTS, no server round-trip, no API key.

// Which deployment this build is. vite.config.js inlines __SITE_MODE__ from the
// SITE_MODE environment variable, so the same source tree produces a private
// build (the full library, the music tab) and a public one (opted-in books
// only, its own music file) with no branching at runtime and no way for a
// public build to reach private data by mistake.
var SITE_MODE = (typeof __SITE_MODE__ !== "undefined" ? __SITE_MODE__ : "private");
var IS_PUBLIC_SITE = SITE_MODE === "public";
// Robot narration is off everywhere. The reader streams real recordings
// only; where a book has none, it stays a text. Every speechSynthesis call
// site is guarded by this, so flipping it back to true restores the feature
// rather than needing the code written again.
var TTS_ENABLED = false;
// Separate catalogues: the private music.json holds material that may not be
// republished, so the public site reads its own file and never falls back to
// the other one.
var MUSIC_URL = IS_PUBLIC_SITE ? "/music/music.public.json" : "/music/music.json";
// What this deployment calls itself. The private site is Говорим ("we speak");
// the public one is Самовар. Static files outside the bundle — index.html and
// the web manifest — are rewritten at build time by scripts/brand.mjs instead,
// since vite copies public/ through untouched.
var SITE_NAME = IS_PUBLIC_SITE ? "Самовар" : "Говорим";
var SITE_NAME_LATIN = IS_PUBLIC_SITE ? "Samovar" : "Govorim";
var SITE_TAGLINE = IS_PUBLIC_SITE ? "Russian Reading" : "Russian Practice";

// ---- deploy freshness --------------------------------------------------------
// Every build stamps one id into the bundle (__BUILD_ID__) and writes the same
// id to /version.json beside it. If the two disagree, this tab is running code
// that has since been replaced on the server, and a reload picks up the new
// build. Checked only at navigation moments — opening a book, switching tabs,
// turning to a new chapter or page — never on a timer, so a deploy can't yank
// the page out from under someone who is sitting still and reading. Reading
// position is already saved per book, so a reload lands back where they were.
var BUILD_ID = (typeof __BUILD_ID__ !== "undefined" ? __BUILD_ID__ : "");
var updateChecking = false;
var updateCheckedAt = 0;
// Set from inside the component. A reload would drop the audio element back to
// zero, so while a recording is playing the check is skipped entirely and the
// next navigation after it stops picks the new build up.
var appBusy = { audio: false };
function checkForUpdate() {
  if (!BUILD_ID) return;
  if (appBusy.audio) return;
  if (updateChecking) return;
  var now = Date.now();
  // Navigation can fire several times in a second; one request a minute is
  // plenty to catch a deploy without hammering the origin.
  if (now - updateCheckedAt < 60000) return;
  updateCheckedAt = now;
  updateChecking = true;
  fetch("/version.json", { cache: "no-store" })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(v) {
      if (appBusy.audio) return;   // playback started while the request was in flight
      if (v && typeof v.build === "string" && v.build && v.build !== BUILD_ID) {
        location.reload();
      }
    })
    // Offline, blocked, or a stray HTML response where JSON was expected:
    // running stale code beats reloading into a broken page, so do nothing.
    .catch(function() {})
    .then(function() { updateChecking = false; });
}

// Every book in the library is labelled the same way: Russian title, em dash,
// author. index.json keeps title and author as separate fields (the exercise
// and lit-analysis prompts feed them to the model independently), so the joined
// form lives here and every surface that names a book calls this.
function bookLabel(book) {
  if (!book) return "";
  var title = book.title || book.filename || "";
  var author = book.author || "";
  if (!author || author === title) return title;
  return title + " — " + author;
}

var storage = {
  get: function(key) {
    return Promise.resolve().then(function() {
      var v = localStorage.getItem(key);
      return v === null ? null : { value: v };
    });
  },
  set: function(key, value) {
    return Promise.resolve().then(function() {
      localStorage.setItem(key, value);
      return { value: value };
    });
  },
  delete: function(key) {
    return Promise.resolve().then(function() {
      localStorage.removeItem(key);
    });
  }
};

// CEFR proficiency levels — used to calibrate the chat AI's vocabulary,
// sentence complexity, and question difficulty. Persisted in localStorage as
// "gv_chat_level" so the user doesn't re-pick each session.
const LEVELS = [
  { code: "A1", label: "A1 — Beginner" },
  { code: "A2", label: "A2 — Elementary" },
  { code: "B1", label: "B1 — Intermediate" },
  { code: "B2", label: "B2 — Upper Intermediate" },
  { code: "C1", label: "C1 — Advanced" },
  { code: "C2", label: "C2 — Mastery" },
];

// Generic EPUB cache slots — one book at a time. Loading a new EPUB replaces these.
// Convert a number into its Russian feminine ordinal form, used for chapter
// announcements ("Глава Первая", "Глава Двадцать первая", etc). "Глава" is a
// feminine noun, so ordinals agreeing with it take the -ая ending.
function ruOrdinalFeminine(n) {
  if (!n || n < 1) return "";
  var ones = ["", "Первая", "Вторая", "Третья", "Четвёртая", "Пятая", "Шестая", "Седьмая", "Восьмая", "Девятая"];
  var teens = ["Десятая", "Одиннадцатая", "Двенадцатая", "Тринадцатая", "Четырнадцатая", "Пятнадцатая", "Шестнадцатая", "Семнадцатая", "Восемнадцатая", "Девятнадцатая"];
  var tens = ["", "", "Двадцатая", "Тридцатая", "Сороковая", "Пятидесятая", "Шестидесятая", "Семидесятая", "Восьмидесятая", "Девяностая"];
  // Cardinal-nominative form used as PREFIX in compound ordinals like
  // "Двадцать первая" — only the final element of a compound takes the
  // ordinal ending; everything before it is a regular cardinal.
  var tensCardinal = ["", "", "Двадцать", "Тридцать", "Сорок", "Пятьдесят", "Шестьдесят", "Семьдесят", "Восемьдесят", "Девяносто"];
  if (n < 10) return ones[n];
  if (n < 20) return teens[n - 10];
  if (n < 100) {
    var t = Math.floor(n / 10);
    var o = n % 10;
    if (o === 0) return tens[t];
    return tensCardinal[t] + " " + ones[o].toLowerCase();
  }
  // 100+: fall back to cardinal with "Сотая" / "Двухсотая" not worth the
  // table. Just spell "Глава 105" by passing the number; Azure pronounces
  // it acceptably for these rare cases.
  return String(n);
}

// Detect whether a book is a Bible / scripture — verse numbers should not be
// pronounced in these. Matches the book title against common Russian and
// English forms, including individual book names ("Бытие", "Деяния", etc),
// and accepts an explicit `isBible: true` metadata flag.
function isBibleBook(meta) {
  if (!meta) return false;
  if (meta.isBible === true) return true;
  if (!meta.title) return false;
  var t = meta.title;
  return /библия|bible|евангелие|новый\s+завет|ветхий\s+завет|псалтир[ьи]|псалмы|апокалипсис|книг[аи]\s|деяния|послание|откровение|пророк[ао]?|святое\s+писание|священное\s+писание|синодальн/i.test(t);
}

var EPUB_CACHE = "epub_data_v1";
var EPUB_BM    = "epub_bm_v1";

// Per-book progress: { [bookKey]: { cidx, pidx, lastRead, title, author,
// filename, totalChapters } }. Used to power "Continue reading" on the
// library screen and to auto-restore where the user left off when they
// reopen a book.
var BOOK_PROGRESS = "book_progress_v1";

// Stable identifier for a book — derived from filename + title so the same
// book always gets the same key whether it's a preset or uploaded.
function bookKey(meta) {
  if (!meta) return "";
  return (meta.filename || "") + "::" + (meta.title || "");
}
// Multi-upload tracking — keeps the last MAX_UPLOADS uploaded books browsable
// in the library view. List of metadata stored at UPLOADS_LIST_KEY; each
// book's full parsed content stored at UPLOAD_BOOK_PREFIX + id.
// Question-history storage from the removed AI tutor. The constant survives
// only so stale blobs keep getting cleaned out of users' storage.
var QHIST_KEY  = "epub_qhist_v1";
var UPLOADS_LIST_KEY  = "epub_uploads_v1";
var UPLOAD_BOOK_PREFIX = "epub_upload_";
var MAX_UPLOADS = 5;
// Paginates a chapter for the on-screen reader. A page is at most 5 paragraphs
// AND at most ~1700 characters — whichever limit is hit first. Paragraphs are
// kept intact (never split mid-paragraph) EXCEPT when a chapter is one giant
// paragraph with no paragraph breaks: in that case we fall back to sentence
// boundaries so the user isn't faced with a 10,000-char wall of text.
//
// Options:
//   { singlePage: true } — bypass pagination entirely. Used for song lyrics
//     where the user wants to see all of one song on one screen and use the
//     chapter-nav buttons to advance to the next song.
//
// Returns an array of page descriptors:
//   { startChar, endChar, paraIndices: number[], isSplit: boolean }
// where paraIndices are indices into the filtered (non-empty) paragraph array
// that the renderer produces. isSplit is true only in the giant-paragraph case.
function computePages(chapterText, options) {
  options = options || {};
  var PAGE_MAX_PARAGRAPHS = 5;
  var PAGE_MAX_CHARS = 1700;

  if (!chapterText || !chapterText.trim()) {
    return [{ startChar: 0, endChar: 0, paraIndices: [], isSplit: false }];
  }

  // Single-page override: whole chapter on one screen, no pagination math.
  // The renderer treats paraIndices=null as "all paragraphs in this chapter".
  if (options.singlePage) {
    return [{ startChar: 0, endChar: chapterText.length, paraIndices: null, isSplit: false, isSinglePage: true }];
  }

  // Scan paragraph ranges using the same boundary as the renderer (\n{2,}).
  // Skip whitespace-only paragraphs so our indices match the renderer's
  // post-filter array.
  var paraRanges = [];
  var br = /\n{2,}/g;
  var lastEnd = 0;
  var m;
  while ((m = br.exec(chapterText)) !== null) {
    if (chapterText.slice(lastEnd, m.index).trim().length > 0) {
      paraRanges.push({ start: lastEnd, end: m.index });
    }
    lastEnd = m.index + m[0].length;
  }
  if (lastEnd < chapterText.length && chapterText.slice(lastEnd).trim().length > 0) {
    paraRanges.push({ start: lastEnd, end: chapterText.length });
  }

  if (paraRanges.length === 0) {
    return [{ startChar: 0, endChar: chapterText.length, paraIndices: [], isSplit: false }];
  }

  // GIANT-PARAGRAPH EXCEPTION: one paragraph, but it's larger than the cap.
  // Split it at sentence boundaries near the 1700-char mark.
  if (paraRanges.length === 1 && (paraRanges[0].end - paraRanges[0].start) > PAGE_MAX_CHARS) {
    var pr = paraRanges[0];
    var pt = chapterText.slice(pr.start, pr.end);
    var pages = [];

    // Sentence-end positions: . ! ? … (one or more), optionally followed by
    // closing punctuation, then whitespace. Russian uses these same end marks.
    var sentEnds = [];
    var sre = /[.!?…]+["»)\]]?\s+/g;
    var sm;
    while ((sm = sre.exec(pt)) !== null) {
      sentEnds.push(sm.index + sm[0].length);
    }
    if (sentEnds.length === 0 || sentEnds[sentEnds.length - 1] !== pt.length) {
      sentEnds.push(pt.length);
    }

    var pageStart = 0;
    for (var i = 0; i < sentEnds.length; i++) {
      var sentEnd = sentEnds[i];
      if (sentEnd - pageStart >= PAGE_MAX_CHARS || i === sentEnds.length - 1) {
        pages.push({
          startChar: pr.start + pageStart,
          endChar:   pr.start + sentEnd,
          paraIndices: [0],
          isSplit: true,
        });
        pageStart = sentEnd;
      }
    }
    return pages.length ? pages : [{ startChar: pr.start, endChar: pr.end, paraIndices: [0], isSplit: false }];
  }

  // NORMAL MULTI-PARAGRAPH CASE. Greedy bucketing with look-ahead: add a
  // paragraph to the current page ONLY if doing so won't push us over the
  // limits. The single exception is when the current page is empty — we
  // always include at least one paragraph, even if it's huge (the "finish
  // that paragraph" rule keeps it intact).
  var pagesOut = [];
  var currentIdx = [];
  var currentLen = 0;

  for (var pi = 0; pi < paraRanges.length; pi++) {
    var p = paraRanges[pi];
    var pLen = p.end - p.start;
    // Separator between paragraphs is "\n\n" (2 chars) — count it for accuracy.
    var addedLen = currentIdx.length === 0 ? pLen : pLen + 2;

    var wouldOverflow = currentIdx.length > 0 && (
      currentIdx.length >= PAGE_MAX_PARAGRAPHS ||
      currentLen + addedLen > PAGE_MAX_CHARS
    );

    if (wouldOverflow) {
      pagesOut.push({
        startChar: paraRanges[currentIdx[0]].start,
        endChar:   paraRanges[currentIdx[currentIdx.length - 1]].end,
        paraIndices: currentIdx,
        isSplit: false,
      });
      currentIdx = [];
      currentLen = 0;
      addedLen = pLen;
    }

    currentIdx.push(pi);
    currentLen += addedLen;
  }

  if (currentIdx.length > 0) {
    pagesOut.push({
      startChar: paraRanges[currentIdx[0]].start,
      endChar:   paraRanges[currentIdx[currentIdx.length - 1]].end,
      paraIndices: currentIdx,
      isSplit: false,
    });
  }

  return pagesOut;
}

// Split long TTS input into ~200-char chunks at sentence boundaries. Returns an
// array of {text, start} where `start` is the char offset back into the original
// text (so word-boundary events can be mapped to global positions for the
// reading-along highlight).
//
// Why: Chrome's "Google русский" voice silently fails for utterances above
// roughly 200 characters — no onstart, no onerror, just no sound. Chunking
// and chaining via onend makes the playback reliable across all voices.
// Microsoft local voices don't have this limit, but they get chunked the same
// way for consistency.
function chunkForTTS(text, from, maxLen) {
  if (typeof maxLen !== "number") maxLen = 200;
  var slice = (text || "").slice(from || 0);
  if (!slice) return [];

  // Find sentence-end positions: . ! ? … plus optional closing punctuation,
  // followed by whitespace. Same matcher used by computePages' giant-paragraph
  // path.
  var sentEnds = [];
  var re = /[.!?…]+["»)\]]?\s+/g;
  var m;
  while ((m = re.exec(slice)) !== null) {
    sentEnds.push(m.index + m[0].length);
  }
  if (sentEnds.length === 0 || sentEnds[sentEnds.length - 1] !== slice.length) {
    sentEnds.push(slice.length);
  }

  var chunks = [];
  var chunkStart = 0;
  var lastBoundary = 0;
  for (var i = 0; i < sentEnds.length; i++) {
    var end = sentEnds[i];
    if (end - chunkStart > maxLen && lastBoundary > chunkStart) {
      chunks.push({ text: slice.slice(chunkStart, lastBoundary), start: (from || 0) + chunkStart });
      chunkStart = lastBoundary;
    }
    lastBoundary = end;
  }

  // Whatever's left after the last sentence boundary. If it's still huge
  // (one massive run-on with no sentence breaks — Tolstoy style), split it
  // at word boundaries.
  var remainder = slice.slice(chunkStart);
  var remainderStart = chunkStart;
  while (remainder.length > maxLen * 1.5) {
    var splitAt = remainder.lastIndexOf(" ", maxLen);
    if (splitAt < 30) splitAt = maxLen; // no nearby space — force-split at maxLen
    chunks.push({ text: remainder.slice(0, splitAt), start: (from || 0) + remainderStart });
    remainderStart += splitAt;
    remainder = remainder.slice(splitAt);
  }
  if (remainder.length > 0) {
    chunks.push({ text: remainder, start: (from || 0) + remainderStart });
  }

  return chunks;
}

function tokenise(text) {
  return (text || "").match(/[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+/g) || [];
}

function yoVariants(word) {
  var out = [];
  for (var i = 0; i < word.length; i++) {
    if (word[i] === "е") out.push(word.slice(0,i) + "ё" + word.slice(i+1));
    else if (word[i] === "Е") out.push(word.slice(0,i) + "Ё" + word.slice(i+1));
  }
  return out;
}

// ── EPUB PARSER ──────────────────────────────────────────────────────────────

function readUint32LE(buf, off) {
  return (buf[off] | buf[off+1]<<8 | buf[off+2]<<16 | buf[off+3]<<24) >>> 0;
}
function readUint16LE(buf, off) {
  return (buf[off] | buf[off+1]<<8) >>> 0;
}

function parseZip(buffer) {
  var bytes = new Uint8Array(buffer);
  var files = {};

  // Find End of Central Directory record (signature: PK\x05\x06)
  var eocd = -1;
  var maxScan = Math.max(0, bytes.length - 65557);
  for (var i = bytes.length - 22; i >= maxScan; i--) {
    if (bytes[i]===0x50 && bytes[i+1]===0x4B && bytes[i+2]===0x05 && bytes[i+3]===0x06) {
      eocd = i; break;
    }
  }
  if (eocd === -1) throw new Error("Invalid ZIP: End of Central Directory not found");

  var cdSize   = readUint32LE(bytes, eocd + 12);
  var cdOffset = readUint32LE(bytes, eocd + 16);

  // Walk central directory entries (signature: PK\x01\x02)
  var pos = cdOffset;
  var end = cdOffset + cdSize;
  while (pos < end - 4) {
    if (bytes[pos]!==0x50 || bytes[pos+1]!==0x4B || bytes[pos+2]!==0x01 || bytes[pos+3]!==0x02) break;

    var comp        = readUint16LE(bytes, pos + 10);
    var csize       = readUint32LE(bytes, pos + 20);
    var fnlen       = readUint16LE(bytes, pos + 28);
    var exlen       = readUint16LE(bytes, pos + 30);
    var cmtlen      = readUint16LE(bytes, pos + 32);
    var localOff    = readUint32LE(bytes, pos + 42);
    var fname       = new TextDecoder().decode(bytes.slice(pos + 46, pos + 46 + fnlen));

    // Jump to the local header to find the actual data start
    // (local header has its own filename and extra-field lengths that may differ)
    if (localOff + 30 < bytes.length) {
      var lfnlen    = readUint16LE(bytes, localOff + 26);
      var lexlen    = readUint16LE(bytes, localOff + 28);
      var dataStart = localOff + 30 + lfnlen + lexlen;
      var data      = bytes.slice(dataStart, dataStart + csize);

      if (comp === 0) {
        files[fname] = new TextDecoder("utf-8").decode(data);
      } else if (comp === 8) {
        try {
          var ds = new DecompressionStream("deflate-raw");
          var writer = ds.writable.getWriter();
          writer.write(data); writer.close();
          files[fname] = { stream: ds.readable, name: fname };
        } catch(ex) {}
      }
    }

    pos += 46 + fnlen + exlen + cmtlen;
  }
  return files;
}

async function decompressEntry(entry) {
  if (typeof entry === "string") return entry;
  // Cached text from a previous read — streams can only be consumed once, so we memoize here.
  if (entry && typeof entry._text === "string") return entry._text;
  // If a concurrent decompression is in flight on the same entry, wait for it.
  if (entry && entry._reading) {
    try { await entry._reading; } catch(e) {}
    return entry._text || "";
  }
  if (entry && entry.stream) {
    var run = (async function() {
      var reader = entry.stream.getReader();
      var chunks = [];
      while (true) {
        var r = await reader.read();
        if (r.done) break;
        chunks.push(r.value);
      }
      var total = chunks.reduce(function(a,c){ return a+c.length; }, 0);
      var out = new Uint8Array(total); var pos = 0;
      for (var ci = 0; ci < chunks.length; ci++) { out.set(chunks[ci], pos); pos += chunks[ci].length; }
      return new TextDecoder("utf-8").decode(out);
    })();
    entry._reading = run;
    try {
      entry._text = await run;
    } catch (e) {
      entry._text = "";
    }
    delete entry._reading;
    return entry._text;
  }
  return "";
}

// HTML → plain text. Defensive: handles malformed HTML, weird entity encodings,
// XHTML namespace quirks, and "plain text" files that have HTML markup pasted in.
// Strategy:
//   1. Use DOMParser when possible (correctly handles tag nesting + entities)
//   2. Regex-scrub any tags or entities that slipped through (mismatched braces,
//      processing instructions, namespace prefixes, etc.)
//   3. Normalize whitespace so paragraphs come out as clean text + double newlines
function htmlToText(html) {
  if (!html) return "";
  var input = String(html);

  var out;
  try {
    var parser = new DOMParser();
    var doc = parser.parseFromString(input, "text/html");
    // Remove scripts/styles/comments/processing instructions before walking.
    doc.querySelectorAll("script, style, noscript, head").forEach(function(el){ el.remove(); });
    var result = [];
    var blockTags = {"P":1,"DIV":1,"H1":1,"H2":1,"H3":1,"H4":1,"H5":1,"H6":1,
                     "LI":1,"BR":1,"TR":1,"BLOCKQUOTE":1,"PRE":1,"SECTION":1,"ARTICLE":1,"HR":1};
    function walk(node) {
      if (!node) return;
      if (node.nodeType === 3) {
        var t = node.nodeValue;
        if (t) result.push(t);
      } else if (node.nodeType === 1) {
        var tag = node.tagName.toUpperCase();
        if (tag === "SCRIPT" || tag === "STYLE") return;
        if (blockTags[tag]) result.push("\n\n");
        for (var ci = 0; ci < node.childNodes.length; ci++) walk(node.childNodes[ci]);
        if (blockTags[tag]) result.push("\n\n");
      }
    }
    walk(doc.body || doc.documentElement);
    out = result.join("");
  } catch (e) {
    // DOMParser shouldn't fail in a browser, but fall back to using the raw
    // input rather than throwing — the entity/tag scrub below will still work.
    out = input;
  }

  // Belt-and-suspenders pass: scrub anything that still looks like HTML.
  // This catches:
  //   - tags DOMParser may have left intact (e.g. self-closing with weird attrs)
  //   - entities the parser didn't decode (when input wasn't proper HTML, like a
  //     .txt with literal "<p>" or "&nbsp;" markup pasted in)
  //   - namespace prefixes (<ns:p>) common in OOXML / XHTML exports
  out = out
    .replace(/<!--[\s\S]*?-->/g, "")                      // HTML comments
    .replace(/<\?[\s\S]*?\?>/g, "")                       // processing instructions
    .replace(/<\/?[a-zA-Z][a-zA-Z0-9:_.-]*(?:\s[^>]*)?>/g, "") // any leftover tags incl. namespaced
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&apos;/gi, "'")
    .replace(/&mdash;/gi, "—")
    .replace(/&ndash;/gi, "–")
    .replace(/&hellip;/gi, "…")
    .replace(/&laquo;/gi, "«")
    .replace(/&raquo;/gi, "»")
    .replace(/&bull;/gi, "•")
    .replace(/&middot;/gi, "·")
    .replace(/&#x([0-9a-fA-F]+);/g, function(_, hex){ try { return String.fromCodePoint(parseInt(hex, 16)); } catch(_){ return ""; } })
    .replace(/&#(\d+);/g, function(_, dec){ try { return String.fromCodePoint(parseInt(dec, 10)); } catch(_){ return ""; } })
    .replace(/\u00A0/g, " ")                              // NBSP as a unicode char
    .replace(/[\u200B-\u200D\uFEFF]/g, "")                // zero-width characters
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return out;
}

function isFrontMatter(heading, text) {
  var h = (heading || "").toLowerCase().trim();
  var t = (text || "").slice(0, 300).toLowerCase().trim();
  // Publisher/editorial metadata to skip. Author content (prefaces by the
  // author themselves, dedications, epigraphs) is intentionally NOT in this
  // list — that content matters as part of the work.
  // What IS skipped: copyright pages, ISBN blocks, publisher addresses,
  // translator credits, generic forewords/intros by third parties.
  var skip = [
    /^аннотация\b/, /^оглавление\b/, /^содержание\b/,
    /^обложка\b/, /^титульн/, /^выходные данные\b/,
    /^cover\b/, /^title page\b/, /^contents\b/, /^table of contents\b/,
    /^copyright\b/, /^annotation\b/, /^colophon\b/, /^about the (author|book)\b/,
    /^acknowledg(e?)ments\b/, /^издательств/,
    /^foreword\b/, /^предисловие\b/, /^от издательства\b/, /^от переводчика\b/,
    /^translator['s ]*note\b/, /^translation\b/, /^isbn\b/,
    /^all rights reserved\b/, /^©\b/, /^©\s*\d/, /^\d{4}\s+©/,
    /^напечатано в\b/, /^printed in\b/, /^универсальный десятичный код\b/, /^удк\b/, /^ббк\b/
  ];
  return skip.some(function(p) { return p.test(h) || p.test(t); });
}

// ── TOC parsing ────────────────────────────────────────────────────────────
// Modern EPUBs declare the author's intended chapter list in a table of contents
// file (NCX for EPUB 2, nav.xhtml for EPUB 3). Using that gives us proper chapter
// boundaries and good headings — far better than the spine order alone, which
// treats every front-matter file (cover, title page, copyright) as a "chapter".

// Quick label-only front-matter check used when filtering TOC entries.
// Also matches against the author name and book title from OPF metadata, since
// title pages commonly use the author's name as their TOC label.
function isFrontMatterLabel(label, authorName, bookTitle) {
  var l = (label || "").toLowerCase().trim();
  if (!l) return true;

  // Generic front-matter labels (Russian + English).
  if (/^(cover|обложка|title page|титульн|titul|copyright|авторские права|table of contents|оглавление|содержание|toc|annotation|аннотация|colophon|выходные данные|book information|информация о книге|об авторе|about the author|acknowledg|благодарност|dedication|посвящение)\b/i.test(l)) return true;

  // Title-page labels: author name or book title used as a TOC entry.
  // Russian title pages frequently show "Антон Чехов" or "А. П. Чехов" as the
  // first navPoint pointing at a page that just contains the author + title.
  function tokens(s) {
    return (s || "").toLowerCase().replace(/[.,]/g, " ").split(/\s+/).filter(function(t){ return t.length > 1; });
  }
  var labelToks = tokens(l);
  if (authorName) {
    var aToks = tokens(authorName);
    if (aToks.length > 0) {
      var sharedA = aToks.filter(function(t){ return labelToks.indexOf(t) !== -1; }).length;
      // Whole-author match, or label is just a subset of author name (e.g. "Чехов", "А. П. Чехов")
      if (sharedA >= 2) return true;
      if (sharedA >= 1 && labelToks.length <= 3 && labelToks.every(function(t){ return aToks.indexOf(t) !== -1; })) return true;
    }
  }
  if (bookTitle) {
    var bToks = tokens(bookTitle);
    if (bToks.length > 0 && labelToks.length > 0) {
      var sharedB = bToks.filter(function(t){ return labelToks.indexOf(t) !== -1; }).length;
      if (sharedB === bToks.length || (sharedB >= 2 && sharedB === labelToks.length)) return true;
    }
  }

  return false;
}

// Resolve a relative path against a base directory (handles ../ and ./ correctly).
function resolvePath(baseDir, relPath) {
  var parts = (baseDir + relPath).split("/");
  var stack = [];
  for (var i = 0; i < parts.length; i++) {
    var p = parts[i];
    if (p === "" || p === ".") continue;
    if (p === "..") stack.pop();
    else stack.push(p);
  }
  return stack.join("/");
}

// Parse an NCX file (EPUB 2 TOC). Returns an ordered list of { label, file, fragment }
// where `file` is the resolved zip-path and `fragment` is the anchor id (or "").
// Only leaf navPoints are emitted (so a nested "Part / Chapter" TOC yields only chapters).
async function parseNcxToc(zipFiles, opfDir, ncxPath) {
  var fullPath = resolvePath(opfDir, ncxPath);
  var data = zipFiles[fullPath] || zipFiles[ncxPath];
  if (!data) return [];
  var xml = typeof data === "string" ? data : await decompressEntry(data);
  var ncxDir = fullPath.includes("/") ? fullPath.slice(0, fullPath.lastIndexOf("/") + 1) : "";

  var doc;
  try {
    doc = new DOMParser().parseFromString(xml, "application/xml");
  } catch(e) { return []; }
  var nps = doc.getElementsByTagName("navPoint");
  var entries = [];
  for (var i = 0; i < nps.length; i++) {
    var np = nps[i];
    // Skip non-leaf navPoints — their children give finer-grained chapters.
    if (np.getElementsByTagName("navPoint").length > 0) continue;
    var labelEl   = np.querySelector("navLabel > text") || np.getElementsByTagName("text")[0];
    var contentEl = np.getElementsByTagName("content")[0];
    if (!labelEl || !contentEl) continue;
    var label = (labelEl.textContent || "").trim();
    var src   = contentEl.getAttribute("src") || "";
    if (!src) continue;
    var hashIdx = src.indexOf("#");
    var file = hashIdx >= 0 ? src.slice(0, hashIdx) : src;
    var frag = hashIdx >= 0 ? src.slice(hashIdx + 1) : "";
    try { file = decodeURIComponent(file); } catch(e) {}
    entries.push({ label: label, file: resolvePath(ncxDir, file), fragment: frag });
  }
  return entries;
}

// Parse an EPUB 3 nav.xhtml file. Returns { label, file, fragment } entries.
async function parseNavToc(zipFiles, opfDir, navPath) {
  var fullPath = resolvePath(opfDir, navPath);
  var data = zipFiles[fullPath] || zipFiles[navPath];
  if (!data) return [];
  var html = typeof data === "string" ? data : await decompressEntry(data);
  var navDir = fullPath.includes("/") ? fullPath.slice(0, fullPath.lastIndexOf("/") + 1) : "";

  // Find the <nav> marked as the toc, or any <nav> as a fallback.
  var navHtml = html.match(/<nav\b[^>]*\bepub:type\s*=\s*["'][^"']*\btoc\b[^"']*["'][^>]*>([\s\S]*?)<\/nav>/i)
            || html.match(/<nav\b[^>]*>([\s\S]*?)<\/nav>/i);
  if (!navHtml) return [];

  // Pull <a href> entries. We don't need to preserve list nesting — order suffices.
  var entries = [];
  var linkRe = /<a\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  var m;
  while ((m = linkRe.exec(navHtml[1])) !== null) {
    var href  = m[1];
    var label = m[2].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    if (!href) continue;
    var hashIdx = href.indexOf("#");
    var file = hashIdx >= 0 ? href.slice(0, hashIdx) : href;
    var frag = hashIdx >= 0 ? href.slice(hashIdx + 1) : "";
    try { file = decodeURIComponent(file); } catch(e) {}
    entries.push({ label: label, file: resolvePath(navDir, file), fragment: frag });
  }
  return entries;
}

// Given an HTML string and two anchor ids, return the HTML slice between them.
// Either id may be empty (meaning "start of doc" or "end of doc"). Used to split
// a single file into multiple chapters when the TOC points at fragments.
function htmlSliceByAnchors(html, startId, endId) {
  var startIdx = 0;
  if (startId) {
    var esc = startId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    var re  = new RegExp("<[^>]*\\bid\\s*=\\s*[\"']" + esc + "[\"']", "i");
    var sm  = html.match(re);
    if (sm) startIdx = sm.index;
  }
  var endIdx = html.length;
  if (endId) {
    var esc2 = endId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    var re2  = new RegExp("<[^>]*\\bid\\s*=\\s*[\"']" + esc2 + "[\"']", "i");
    var slice = html.slice(startIdx);
    var em = slice.match(re2);
    if (em) endIdx = startIdx + em.index;
  }
  return html.slice(startIdx, endIdx);
}

// Build the chapter list from filtered TOC entries.
// Consecutive entries pointing at the same file with different fragments split that file.
async function buildChaptersFromToc(entries, zipFiles) {
  var chapters = [];
  for (var i = 0; i < entries.length; i++) {
    var e    = entries[i];
    var next = entries[i + 1];
    var fileData = zipFiles[e.file];
    if (!fileData) continue;
    var html = typeof fileData === "string" ? fileData : await decompressEntry(fileData);

    var chunk;
    var sameFileNext = next && next.file === e.file;
    if (e.fragment || sameFileNext) {
      chunk = htmlSliceByAnchors(html, e.fragment || "", sameFileNext ? (next.fragment || "") : "");
    } else {
      chunk = html;
    }
    var text = htmlToText(chunk);
    var cyr  = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
    if (cyr < 5) continue;
    // Prefer a heading extracted from the chapter HTML over the TOC label —
    // some EPUBs use generic / author / publisher labels in the TOC even though
    // the actual chapter document has a clean <h1> or <h2> with the real title.
    var headingFromHtml = "";
    var hM = chunk.match(/<h[1-6][^>]*>([\s\S]*?)<\/h[1-6]>/i);
    if (hM) headingFromHtml = hM[1].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    var heading = headingFromHtml || e.label || ("Глава " + (chapters.length + 1));
    chapters.push({ heading: heading, text: text });
  }
  return chapters;
}

// ── Text-based chapter marker detection ─────────────────────────────────────
// Authors mark their chapter divisions inside the actual text — usually with
// Roman numerals (I, II, III...), Arabic numbers (1, 2, 3), or "Глава N" /
// "Часть N" / "Chapter N". Detecting these is far more reliable than trusting
// spine items or TOC labels, which often include front matter (cover, copyright,
// title page) as if they were chapters.
function isChapterMarker(line) {
  var l = (line || "").trim();
  if (!l || l.length > 30) return false;
  // Roman numerals up to L (50) — covers virtually every Russian classic.
  if (/^[IVXLivxl]{1,6}\.?$/.test(l)) return true;
  // Arabic numbers up to 999 — handles short story collections, song books, etc.
  if (/^\d{1,3}\.?$/.test(l)) return true;
  // Explicit chapter words with a number
  if (/^(глава|часть|chapter|part)\s+([0-9]+|[ivxl]+)\.?$/i.test(l)) return true;
  // Special section names
  if (/^(пролог|prologue|prolog|эпилог|epilogue|вступление|введение|заключение|послесловие)\.?$/i.test(l)) return true;
  return false;
}

// Concatenate a chapter list, then re-split at in-text chapter markers.
// Each marker line itself becomes the chapter heading; the text between markers
// is the chapter body. Returns null when fewer than 2 markers are found
// (caller should keep the existing chapter structure in that case).
function splitByMarkers(chapters) {
  var fullText = chapters.map(function(c){ return (c.text || ""); }).join("\n\n");
  var lines = fullText.split("\n");
  var markers = [];
  for (var i = 0; i < lines.length; i++) {
    if (isChapterMarker(lines[i])) {
      markers.push({ idx: i, label: lines[i].trim().replace(/\.+$/, "").toUpperCase() });
    }
  }
  if (markers.length < 2) return null;
  var out = [];
  for (var j = 0; j < markers.length; j++) {
    var start = markers[j].idx + 1;
    var end = (j + 1 < markers.length) ? markers[j + 1].idx : lines.length;
    var chunk = lines.slice(start, end).join("\n").trim();
    if (chunk.length < 50) continue; // skip tiny / empty splits
    out.push({ heading: markers[j].label, text: chunk });
  }
  return out.length >= 2 ? out : null;
}


async function parseEpub(buffer) {
  var zipFiles = parseZip(buffer);

  // Detect DRM-protected EPUBs early — Adobe ADEPT, Apple FairPlay, B&N, Kobo all add these files.
  // Parsing won't yield readable text from DRM-locked files; tell the user clearly instead of "no Russian found".
  if (zipFiles["META-INF/encryption.xml"] || zipFiles["META-INF/rights.xml"]) {
    throw new Error("This EPUB is DRM-protected (locked by the seller). Try a DRM-free source: Project Gutenberg, Flibusta, or Litres exports marked « без DRM ».");
  }

  var containerXml = zipFiles["META-INF/container.xml"];
  if (!containerXml) throw new Error("Not a valid EPUB — no container.xml. File may be corrupted or not actually an EPUB.");
  if (typeof containerXml !== "string") containerXml = await decompressEntry(containerXml);

  var opfMatch = containerXml.match(/full-path="([^"]+\.opf)"/i);
  if (!opfMatch) throw new Error("Could not find OPF file in EPUB");
  var opfPath = opfMatch[1];
  var opfDir  = opfPath.includes("/") ? opfPath.slice(0, opfPath.lastIndexOf("/")+1) : "";

  var opfRaw = zipFiles[opfPath];
  if (!opfRaw) throw new Error("OPF file not found: " + opfPath);
  if (typeof opfRaw !== "string") opfRaw = await decompressEntry(opfRaw);

  var manifestItems = {};
  var itemRe = /<item\b([^>]+)>/gi;
  var mm;
  while ((mm = itemRe.exec(opfRaw)) !== null) {
    var attrs = mm[1];
    var idM   = attrs.match(/\bid\s*=\s*["']([^"']+)["']/i);
    var hrefM = attrs.match(/\bhref\s*=\s*["']([^"']+)["']/i);
    if (idM && hrefM) manifestItems[idM[1]] = hrefM[1];
  }

  var spineIds = [];
  var itemrefRe = /<itemref\b([^>]+)>/gi;
  var sm;
  while ((sm = itemrefRe.exec(opfRaw)) !== null) {
    var idrefM = sm[1].match(/\bidref\s*=\s*["']([^"']+)["']/i);
    if (idrefM) spineIds.push(idrefM[1]);
  }

  if (spineIds.length === 0) throw new Error("No spine items found in EPUB");

  // ── First try TOC-based chapter extraction ──
  // Most EPUBs ship a table of contents that lists the AUTHOR'S intended chapters
  // (NCX for EPUB 2, nav.xhtml for EPUB 3). Using it gives us proper headings and
  // skips front matter that the author considered non-chapter content (cover,
  // title page, copyright, etc.) — a single spine item per "chapter" approach
  // happily treats those as Chapter 1, 2, 3 because they're separate files.

  // Find an NCX file. EPUB 2 puts the id on <spine toc="ncx-id">; EPUB 3 puts
  // it in the manifest via media-type. Both forms appear in the wild.
  var ncxPath = null;
  var spineTocM = opfRaw.match(/<spine\b[^>]*\btoc\s*=\s*["']([^"']+)["']/i);
  if (spineTocM && manifestItems[spineTocM[1]]) ncxPath = manifestItems[spineTocM[1]];
  if (!ncxPath) {
    var ncxItemM = opfRaw.match(/<item\b[^>]*media-type\s*=\s*["']application\/x-dtbncx\+xml["'][^>]*\bhref\s*=\s*["']([^"']+)["']/i)
                || opfRaw.match(/<item\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*\bmedia-type\s*=\s*["']application\/x-dtbncx\+xml["']/i);
    if (ncxItemM) ncxPath = ncxItemM[1];
  }
  // EPUB 3 nav doc — flagged via properties="nav" in the manifest.
  var navHref = null;
  var navItemM = opfRaw.match(/<item\b[^>]*\bproperties\s*=\s*["'][^"']*\bnav\b[^"']*["'][^>]*\bhref\s*=\s*["']([^"']+)["']/i)
              || opfRaw.match(/<item\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*\bproperties\s*=\s*["'][^"']*\bnav\b/i);
  if (navItemM) navHref = navItemM[1];

  var tocEntries = [];
  try {
    if (ncxPath)       tocEntries = await parseNcxToc(zipFiles, opfDir, ncxPath);
    else if (navHref)  tocEntries = await parseNavToc(zipFiles, opfDir, navHref);
  } catch(e) { tocEntries = []; }

  // Extract title/author NOW so we can use them to filter title-page entries
  // (very common pattern: TOC entry labeled with author's name pointing at a
  // page that only contains the author + title).
  var titleM_  = opfRaw.match(/<dc:title[^>]*>([^<]+)<\/dc:title>/i);
  var authorM_ = opfRaw.match(/<dc:creator[^>]*>([^<]+)<\/dc:creator>/i);
  var bookTitle  = titleM_  ? titleM_[1].trim()  : "";
  var bookAuthor = authorM_ ? authorM_[1].trim() : "";

  // Filter out front-matter labels AND author/title-page entries.
  var realEntries = tocEntries.filter(function(e){ return !isFrontMatterLabel(e.label, bookAuthor, bookTitle); });

  if (realEntries.length >= 2) {
    var tocChs = await buildChaptersFromToc(realEntries, zipFiles);
    // Drop leading chapters that are dramatically shorter than the rest of the
    // book — almost always front matter (cover, title page, copyright, dedication)
    // that the EPUB packaged as a navigable chapter.
    // Use the median chapter length to adapt to books with naturally short
    // chapters (poetry, song lyrics) where a fixed threshold would over-trim.
    var cyrLens = tocChs.map(function(c){ return ((c.text || "").match(/[а-яёА-ЯЁ]/g) || []).length; });
    var sortedLens = cyrLens.slice().sort(function(a,b){ return a-b; });
    var median = sortedLens.length > 0 ? sortedLens[Math.floor(sortedLens.length / 2)] : 0;
    // Threshold: at least 150 Cyrillic chars, OR 25% of median, whichever is larger.
    var threshold = Math.max(150, Math.floor(median * 0.25));
    var maxDrops = Math.min(5, tocChs.length - 1);  // never drop everything
    while (maxDrops > 0 && tocChs.length > 1) {
      var firstCyr = ((tocChs[0].text || "").match(/[а-яёА-ЯЁ]/g) || []).length;
      if (firstCyr < threshold) {
        tocChs.shift();
        maxDrops--;
        continue;
      }
      break;
    }
    if (tocChs.length >= 2) {
      return {
        chapters: tocChs,
        title:  bookTitle  || "Unknown title",
        author: bookAuthor || "Unknown author"
      };
    }
  }

  var chapters = [];
  for (var k = 0; k < spineIds.length; k++) {
    var id   = spineIds[k];
    var href = manifestItems[id];
    if (!href) continue;
    var clean = href.split("#")[0];
    try { clean = decodeURIComponent(clean); } catch(e) {}
    var fullPath = opfDir + clean;
    var fileData = zipFiles[fullPath] || zipFiles[clean] || zipFiles[href.split("#")[0]];
    if (!fileData) continue;
    var html = typeof fileData === "string" ? fileData : await decompressEntry(fileData);
    var text = htmlToText(html);
    var cyrCount = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
    if (cyrCount < 5) continue;

    var headMatch = html.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
    var heading = headMatch ? headMatch[1].trim() : ("Глава " + (chapters.length+1));
    if (isFrontMatter(heading, text)) continue;
    chapters.push({ heading: heading, text: text });
  }

  if (chapters.length === 0) {
    // Fallback: scan ALL HTML/XHTML files in the zip, not just spine
    var keys = Object.keys(zipFiles);
    for (var ki = 0; ki < keys.length; ki++) {
      var fname = keys[ki];
      if (!/\.(x?html?)$/i.test(fname)) continue;
      var fd = zipFiles[fname];
      var ht = typeof fd === "string" ? fd : await decompressEntry(fd);
      var tx = htmlToText(ht);
      var cy = (tx.match(/[а-яёА-ЯЁ]/g) || []).length;
      if (cy < 5) continue;
      var hm = ht.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
      var hd = hm ? hm[1].trim() : ("Глава " + (chapters.length+1));
      if (isFrontMatter(hd, tx)) continue;
      chapters.push({ heading: hd, text: tx });
    }
  }

  if (chapters.length === 0) {
    // Last resort: take everything that has ANY Russian, regardless of front-matter checks.
    var lastKeys = Object.keys(zipFiles);
    for (var li = 0; li < lastKeys.length; li++) {
      var lf = lastKeys[li];
      if (!/\.(x?html?)$/i.test(lf)) continue;
      var ld = zipFiles[lf];
      var lh = typeof ld === "string" ? ld : await decompressEntry(ld);
      var lt = htmlToText(lh);
      var lcy = (lt.match(/[а-яёА-ЯЁ]/g) || []).length;
      if (lcy < 5) continue;
      var lhm = lh.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
      var lhd = lhm ? lhm[1].trim() : ("Глава " + (chapters.length+1));
      chapters.push({ heading: lhd, text: lt });
    }
  }

  if (chapters.length === 0) {
    throw new Error("Could not extract Russian text. The EPUB may be empty, corrupted, in a different language, or use unusual encoding. If it's a DRM-locked file from a bookstore, it can't be read here — try a DRM-free source.");
  }

  // Trim leading "chapters" that are too short to be real story content (title pages,
  // copyright, etc.) — uses the same adaptive median heuristic as the TOC path.
  var spCyrLens = chapters.map(function(c){ return ((c.text || "").match(/[а-яёА-ЯЁ]/g) || []).length; });
  var spSorted = spCyrLens.slice().sort(function(a,b){ return a-b; });
  var spMedian = spSorted.length > 0 ? spSorted[Math.floor(spSorted.length / 2)] : 0;
  var spThreshold = Math.max(150, Math.floor(spMedian * 0.25));
  var spMaxDrops = Math.min(5, chapters.length - 1);
  while (spMaxDrops > 0 && chapters.length > 1) {
    var firstSpineCyr = ((chapters[0].text || "").match(/[а-яёА-ЯЁ]/g) || []).length;
    if (firstSpineCyr < spThreshold) {
      chapters.shift();
      spMaxDrops--;
      continue;
    }
    break;
  }

  // Extract title/author from OPF metadata
  var titleM  = opfRaw.match(/<dc:title[^>]*>([^<]+)<\/dc:title>/i);
  var authorM = opfRaw.match(/<dc:creator[^>]*>([^<]+)<\/dc:creator>/i);
  var title   = titleM  ? titleM[1].trim()  : "Unknown title";
  var author  = authorM ? authorM[1].trim() : "Unknown author";

  return { chapters: chapters, title: title, author: author };
}

// ── ENCODING / TEXT HELPERS ──────────────────────────────────────────────────
// Russian texts are sometimes saved in cp1251 or KOI8-R rather than UTF-8.
// This tries UTF-8 first, falls back if the result has replacement chars or no Cyrillic.
function decodeBytes(buffer) {
  var bytes = new Uint8Array(buffer);
  var text = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  if (text.indexOf("\uFFFD") > -1 || !/[а-яёА-ЯЁ]/.test(text)) {
    try { text = new TextDecoder("windows-1251").decode(bytes); } catch(e) {}
  }
  return text;
}

// Try to split a long plain-text blob into chapters by common headings.
function splitTextIntoChapters(text) {
  // Look for "Глава N", "Часть N", "Chapter N", roman numerals on their own line, etc.
  var lines = text.split(/\r?\n/);
  var marks = [];
  var headRe = /^\s*(Глава|ГЛАВА|Часть|ЧАСТЬ|Chapter|CHAPTER|Section)\s+[\dIVXLCDM]+/i;
  var romanRe = /^\s*[IVXLCDM]{1,5}\.?\s*$/;
  for (var i = 0; i < lines.length; i++) {
    var l = lines[i].trim();
    if (!l) continue;
    if (headRe.test(l) || romanRe.test(l)) marks.push({ idx: i, heading: l });
  }
  if (marks.length < 2) {
    // No reliable chapter markers — return the whole text as one chapter.
    return [{ heading: "Текст", text: text.trim() }];
  }
  var out = [];
  for (var j = 0; j < marks.length; j++) {
    var startLine = marks[j].idx;
    var endLine   = j + 1 < marks.length ? marks[j+1].idx : lines.length;
    var body = lines.slice(startLine + 1, endLine).join("\n").trim();
    if (body.length < 40) continue;  // skip tiny "chapters"
    out.push({ heading: marks[j].heading, text: body });
  }
  return out.length ? out : [{ heading: "Текст", text: text.trim() }];
}

// ── FB2 (FictionBook) — XML-based, very common for Russian ebooks ───────────

// Cyrillic look-alikes for the Latin letters used in roman numerals. Russian
// FB2s mix them freely — "ХІV" is often Cyrillic Х + Ukrainian І + Latin V —
// and a numeral read literally would not match anything.
var FB2_ROMAN_HOMOGLYPHS = { "Х": "X", "І": "I", "Ѵ": "V", "С": "C", "М": "M", "Д": "D" };
// A chapter marker is a roman numeral, optionally followed by that chapter's
// own name — Anna Karenina has both bare "XX" and "XX СМЕРТЬ".
var FB2_CHAPTER_MARK_RE = /^(?:глава\s+)?([ivxlcdm]+)\.?(?:\s+\S[\s\S]*)?$/i;
// A split is only believable if the pieces are chapter-sized. Verse works
// number their STANZAS with roman numerals exactly the way prose works number
// their chapters, and some sections carry dozens of one-line subtitles that
// aren't chapters at all. Real chapters are far bigger (median 1149 words in
// Anna Karenina, 4172 in Crime and Punishment), so a median below this means
// the markers were numbering something else.
var FB2_MIN_MEDIAN_CHAPTER_WORDS = 150;

// Returns the roman numeral if `txt` opens like a chapter heading, else "".
// Deliberately ROMAN ONLY: many Russian FB2s mark real chapters this way
// inside a part-level section, but they also use <subtitle> for things that
// are NOT chapters — scene breaks ("* * *"), stage directions ("Занавес"), an
// end marker ("Конец."), and, the case that makes arabic numbers unsafe,
// numbered endnotes. Crime and Punishment's ПРИМЕЧАНИЯ section carries 273
// subtitles numbered 1, 2, 3…; treating those as chapters buried the novel's
// 41 real ones under them.
// Kept deliberately identical to _chapter_marker() in Auto-MFA's app/fb2.py —
// the aligner splits the same FB2 into the chapters this reader displays, so
// the two must agree or the audio lines up with the wrong text.
// Endnote sections. FB2 normally puts these in <body name="notes">, which is
// skipped outright, but plenty of files leave them as an ordinary section of
// the main body — Crime and Punishment ships 273 numbered notes that way.
// They're never recorded, so counting one as a chapter shifts every later
// chapter's audio pairing by one.
// Leading/trailing decoration is explicit rather than \W, for two reasons:
// a heading can arrive as "*\u00a0ПРИМЕЧАНИЯ\u00a0*" (Тихий Дон), and JS's \W
// matches Cyrillic letters — so \W* would also swallow "ЛОЖНЫЕ " and call that
// a notes section. Keep this identical to _NOTES_TITLE_RE in Auto-MFA app/fb2.py.
var FB2_NOTES_DECO = '[\\s*_·\u2022—\u2013\\-.,:;!?()"\'\u00ab\u00bb\\[\\]]*';
var FB2_NOTES_TITLE_RE = new RegExp("^" + FB2_NOTES_DECO +
  "(сноски?|примечани[ея]|комментари[ий]|notes?|footnotes?|endnotes?)" + FB2_NOTES_DECO + "$", "i");
function fb2IsNotesTitle(title) {
  return FB2_NOTES_TITLE_RE.test((title || "").trim());
}

function fb2ChapterMarker(txt) {
  var s = (txt || "").trim();
  if (!s) return "";
  s = s.replace(/[ХІѴСМД]/g, function (c) { return FB2_ROMAN_HOMOGLYPHS[c]; });
  var m = FB2_CHAPTER_MARK_RE.exec(s);
  return m ? m[1].toUpperCase() : "";
}

async function parseFb2(buffer, options) {
  options = options || {};
  // FB2 files declare their own encoding in the XML header.
  var text = decodeBytes(buffer);
  var encMatch = /encoding=["']([^"']+)["']/i.exec(text.slice(0, 200));
  if (encMatch && !/utf-?8/i.test(encMatch[1])) {
    try { text = new TextDecoder(encMatch[1]).decode(new Uint8Array(buffer)); } catch(e) {}
  }
  var parser = new DOMParser();
  var doc = parser.parseFromString(text, "application/xml");
  // DOMParser returns a <parsererror> root if it failed.
  if (doc.querySelector("parsererror")) throw new Error("FB2 file is malformed XML");

  // Title and author from <description><title-info>
  var bookTitle = (doc.querySelector("title-info > book-title") || {}).textContent || "";
  var fn = (doc.querySelector("title-info > author > first-name") || {}).textContent || "";
  var ln = (doc.querySelector("title-info > author > last-name")  || {}).textContent || "";
  var nick = (doc.querySelector("title-info > author > nickname") || {}).textContent || "";
  var author = (fn + " " + ln).trim() || nick || "Unknown author";

  // Each top-level <section> is a Part. <subtitle> markers within it delimit
  // individual chapters. Books with no subtitle markers (single-story FB2s)
  // keep the old per-section behavior.
  // Use only the MAIN body for chapters. FB2 stores footnotes/endnotes in a
  // separate <body name="notes"> (and sometimes name="comments"); those must
  // NOT become chapters. Prefer the first unnamed body; fall back to the first
  // body if every body is named.
  var allBodies = Array.prototype.slice.call(doc.querySelectorAll("body"));
  var mainBody = null;
  for (var _bi = 0; _bi < allBodies.length; _bi++) {
    if (!allBodies[_bi].getAttribute("name")) { mainBody = allBodies[_bi]; break; }
  }
  if (!mainBody) mainBody = allBodies[0] || null;
  var sections = mainBody
    ? Array.prototype.slice.call(mainBody.children).filter(function(c){ return c.tagName && c.tagName.toLowerCase() === "section"; })
    : [];
  var chapters = [];
  // Scripture mode: deeply-nested Bibles (… Завет > division > book > Глава N)
  // become one chapter per "Testament — Book — Глава N" so the nav drawer nests
  // Testament > Book > Chapter. Requires a "Завет" top section AND 3+ nesting
  // levels, so ordinary books are untouched. The division tier is skipped.
  var isScripture = Array.from(sections).some(function(s){
    var tt = (s.querySelector(":scope > title") || {}).textContent || "";
    if (!/Завет/i.test(tt)) return false;
    return Array.from(s.children).some(function(c){
      return c.tagName.toLowerCase() === "section" && Array.from(c.children).some(function(x){
        return x.tagName.toLowerCase() === "section";
      });
    });
  });
  if (isScripture) {
    var gatherScripture = function(sec){
      var out = [];
      var dt = sec.querySelector(":scope > title");
      var nodes = sec.querySelectorAll("title, subtitle, p, v");
      for (var qi = 0; qi < nodes.length; qi++) {
        if (nodes[qi] === dt) continue;
        // Skip ALL title/subtitle elements — headings are in chapter.heading,
        // not in chapter.text, so they don't confuse sentence parsing
        var qTag = nodes[qi].tagName.toLowerCase();
        if (qTag === "title" || qTag === "subtitle") continue;
        var t = nodes[qi].textContent.replace(/\s+/g, " ").trim();
        if (t) {
          // Verses bundle multiple-per-<p>; split each verse onto its own
          // paragraph so the reader highlights verse-by-verse regardless of
          // Bible-mode. Verse marker = a number after sentence punctuation,
          // before a capital/quote. Leading number stays visible on screen.
          t = t.replace(/([.!?…»"])\s+(?=\d{1,3}\s+[«"„(\[—–А-ЯЁ])/g, "$1\n\n");
          out.push(t);
        }
      }
      return out.join("\n\n");
    };
    var isChapTitle = function(x){ return /^(глава|псалом|песнь)\s*\d+/i.test(x); };
    var pushScripture = function(parts, text){
      var heading = parts.filter(function(z){ return z; }).join(" — ");
      var cyr = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
      if (cyr >= 5) chapters.push({ heading: heading, text: text });
    };
    var emitScripture = function(sec, testament, book){
      var te = sec.querySelector(":scope > title");
      var title = te ? te.textContent.replace(/\s+/g, " ").trim() : "";
      var childSecs = Array.from(sec.children).filter(function(c){ return c.tagName.toLowerCase() === "section"; });
      if (isChapTitle(title)) {
        pushScripture([testament, book, title], gatherScripture(sec));
        return;
      }
      if (childSecs.length) {
        var anyChap = childSecs.some(function(c){
          var ct = ((c.querySelector(":scope > title") || {}).textContent || "").replace(/\s+/g, " ").trim();
          return isChapTitle(ct);
        });
        if (anyChap) {
          childSecs.forEach(function(c){ emitScripture(c, testament, title); });
        } else {
          var deeper = childSecs.some(function(c){
            return Array.from(c.children).some(function(x){ return x.tagName.toLowerCase() === "section"; });
          });
          if (deeper) {
            if (!testament) {
              childSecs.forEach(function(c){ emitScripture(c, title, ""); });
            } else {
              childSecs.forEach(function(c){ emitScripture(c, testament, book); });
            }
          } else {
            pushScripture([testament, (book || title), "Глава 1"], gatherScripture(sec));
          }
        }
      } else {
        pushScripture([testament, (book || title), "Глава 1"], gatherScripture(sec));
      }
    };
    Array.from(sections).forEach(function(s){ emitScripture(s, "", ""); });
  }
  if (!isScripture) {
  // Paragraph text of a section. ownOnly=true stops at nested <section>
  // children (used for a part's preamble — an epigraph before its first
  // chapter — which would otherwise be swallowed or duplicated).
  var paragraphsOf = function(sec, ownOnly) {
    var out = [];
    // Indices of paragraphs that came out of an <epigraph>. Pushkin gives every
    // chapter a verse epigraph whose lines are separate <p>s, so at full
    // paragraph spacing the chapter opens with five stranded lines. Recorded
    // here (never in `text`, so char offsets and chapter splitting are
    // untouched) and rendered tight. Deliberately NOT extended to <poem>:
    // Горе от ума wraps every speech in one, and those want normal spacing.
    out.tightIdx = [];
    var walk = function(el, inVerse) {
      for (var wi = 0; wi < el.children.length; wi++) {
        var c = el.children[wi];
        var tag = c.tagName.toLowerCase();
        if (tag === "section") { if (!ownOnly) walk(c, inVerse); continue; }
        if (tag === "title") continue;   // headings live in chapter.heading
        if (tag === "p" || tag === "v" || tag === "subtitle") {
          var t = c.textContent.replace(/\s+/g, " ").trim();
          if (!t) continue;
          // Verse splitting: one <p> can hold several numbered verses
          // ("1 В начале… 2 Земля же…"); give each its own paragraph so the
          // reader highlights verse by verse.
          if (/^\d+\s/.test(t)) {
            var verseParts = t.split(/(?<=[.!?»а-яёА-ЯЁa-zA-Z])\s+(\d+)\s+(?=[А-ЯЁ«—])/);
            if (verseParts.length > 1) {
              if (inVerse) out.tightIdx.push(out.length);
              out.push(verseParts[0].trim());
              for (var vi = 1; vi < verseParts.length - 1; vi += 2) {
                if (inVerse) out.tightIdx.push(out.length);
                out.push((verseParts[vi] + " " + verseParts[vi + 1]).trim());
              }
              continue;
            }
          }
          if (inVerse) out.tightIdx.push(out.length);
          out.push(t);
          continue;
        }
        walk(c, inVerse || tag === "epigraph");   // wrapper containers: epigraph, poem, cite, …
      }
    };
    walk(sec, false);
    return out;
  };

  var wordsIn = function(ch) { return (ch.text.match(/\S+/g) || []).length; };
  var medianWords = function(list) {
    var sizes = list.map(wordsIn).sort(function(a, b) { return a - b; });
    return sizes.length ? sizes[Math.floor(sizes.length / 2)] : 0;
  };
  var pushChapter = function(out, heading, paras) {
    var body = paras.join("\n\n");
    if ((body.match(/[а-яёА-ЯЁ]/g) || []).length < 5) return;   // no Russian text
    out.push({ heading: heading || ("Глава " + (out.length + 1)), text: body,
               tightIdx: (paras && paras.tightIdx) || [] });
  };

  // Depth-first: one chapter per LEAF <section>, in document order. FB2s vary
  // in how deep they nest — some carry one chapter per top-level section,
  // many "raw" library downloads wrap each chapter's section inside a Part
  // section. Only reading top-level sections turns The Brothers Karamazov's
  // 97 chapters into 5 giant blobs that can't be paired against one audio
  // file per chapter. This mirrors _walk_sections() in Auto-MFA's
  // app/fb2.py: the aligner and this reader must cut the same FB2 into the
  // same chapters, or the audio plays against the wrong text.
  // soleSection: this is the body's only top-level section, so it is the whole
  // book. The short-scrap rule below must not fire on it — see there.
  var walkSection = function(sec, out, soleSection) {
    var nested = Array.prototype.filter.call(sec.children, function(c) {
      return c.tagName && c.tagName.toLowerCase() === "section";
    });
    var titleEl = sec.querySelector(":scope > title");
    var partTitle = titleEl ? titleEl.textContent.replace(/\s+/g, " ").trim() : "";
    if (fb2IsNotesTitle(partTitle)) return;   // endnotes left in the main body

    // Nesting only counts as chapter structure when the subsections are
    // chapters in their own right, which in practice means they're titled.
    // Where a large share of them aren't, the nesting is internal division:
    // "Моя любимая страна" builds each of its 14 essays from an untitled
    // first-person opening plus the titled reportage piece it introduces,
    // and splitting there gives 28 half-chapters against 14 audio files. A
    // stray untitled section among many titled ones is just an untitled
    // chapter (Тихий Дон has three among 248), hence a share rather than a
    // flat "every one of them".
    //
    // The test only applies where the subsections are leaves. A subsection
    // holding subsections of its own is structural whatever its title says —
    // Тихий Дон's "КНИГА ТРЕТЬЯ" wraps two untitled parts holding 63
    // chapters between them, and judging it by this rule would swallow all 63.
    var titleOf = function(s2) {
      var t = s2.querySelector(":scope > title");
      return t ? t.textContent.replace(/\s+/g, " ").trim() : "";
    };
    var hasGrandchildSections = nested.some(function(c) {
      return Array.prototype.some.call(c.children, function(g) {
        return g.tagName && g.tagName.toLowerCase() === "section";
      });
    });
    if (nested.length && !hasGrandchildSections) {
      var untitled = nested.filter(function(c) { return !titleOf(c); }).length;
      if (untitled * 3 > nested.length) nested = [];
    }
    // A <subtitle> only marks a chapter break if it carries a roman-numeral
    // chapter marker (see fb2ChapterMarker). Everything else a book puts in a
    // <subtitle> — decorative scene-breaks like "* * *", stage directions,
    // numbered endnotes — stays in-chapter content and must NOT split.
    // Requiring at least two DISTINCT numerals stops a lone "Занавес", or a
    // run of lines that merely begin with a roman-numeral letter (the Russian
    // preposition "С ", which transliterates to a valid "C"), from
    // fragmenting a section that was already correct.
    var markerSubs = Array.prototype.filter.call(
      sec.querySelectorAll(":scope > subtitle"),
      function(el) { return !!fb2ChapterMarker(el.textContent || ""); }
    );
    var distinctMarkers = {};
    for (var mi = 0; mi < markerSubs.length; mi++) {
      distinctMarkers[fb2ChapterMarker(markerSubs[mi].textContent || "")] = true;
    }

    var split = null;
    if (!nested.length && Object.keys(distinctMarkers).length >= 2) {
      split = [];
      var markerSet = new Set(markerSubs);
      var directChildren = Array.from(sec.children);
      var currentSubtitle = null;
      var currentParas = [];
      var flush = function() {
        if (currentSubtitle === null) return;
        var body = currentParas.join("\n\n");
        var cyrCount = (body.match(/[а-яёА-ЯЁ]/g) || []).length;
        if (cyrCount >= 5) {
          split.push({
            heading: (partTitle ? partTitle + " — " : "") + currentSubtitle,
            text: body,
          });
        }
      };
      for (var ci = 0; ci < directChildren.length; ci++) {
        var child = directChildren[ci];
        var tag = child.tagName.toLowerCase();
        if (tag === "title") continue;   // the part name, captured separately
        var childTxt = child.textContent.replace(/\s+/g, " ").trim();
        if (tag === "subtitle" && markerSet.has(child)) {
          // The marker names the chapter; it isn't part of what's read aloud,
          // so it becomes the heading rather than the first line of the text.
          flush();
          currentSubtitle = childTxt;
          currentParas = [];
          continue;
        }
        if (childTxt && currentSubtitle !== null) currentParas.push(childTxt);
      }
      flush();

      // Size guard — see FB2_MIN_MEDIAN_CHAPTER_WORDS.
      var sizes = split
        .map(function(c) { return (c.text.match(/\S+/g) || []).length; })
        .sort(function(a, b) { return a - b; });
      if (split.length < 2 || sizes[Math.floor(sizes.length / 2)] < FB2_MIN_MEDIAN_CHAPTER_WORDS) {
        split = null;   // stanzas, endnotes or similar — not chapters
      }
    }

    if (split) {
      for (var pi = 0; pi < split.length; pi++) out.push(split[pi]);
      return;
    }
    if (!nested.length) {
      var leafParas = paragraphsOf(sec, false);
      // An untitled scrap this short is front matter — a dedication, an
      // epigraph, a colophon — not a chapter anyone recorded. But only when
      // there is a book around it: «Я вас любил» is one untitled 43-word
      // section and nothing else, so dropping it left no chapters at all and
      // the fallback below rendered the <body><title> on its own — the reader
      // showed the poem's name and not one line of the poem. A short lyric is
      // a legitimate whole work.
      if (!partTitle && !soleSection &&
          (leafParas.join(" ").match(/\S+/g) || []).length < FB2_MIN_MEDIAN_CHAPTER_WORDS) {
        return;
      }
      pushChapter(out, partTitle, leafParas);
      return;
    }

    // Walk the subsections into a scratch list first, so their combined size
    // can be sanity-checked before they're accepted as chapters.
    var sub = [];
    pushChapter(sub, partTitle, paragraphsOf(sec, true));   // the part's preamble
    for (var ni = 0; ni < nested.length; ni++) walkSection(nested[ni], sub);

    // Same size guard as the subtitle split, for the same reason: nesting a
    // <section> per unit is how one book marks its chapters and how another
    // marks something much smaller. Eugene Onegin wraps each of its 357
    // STANZAS in its own section inside the eight "Глава" sections, so
    // recursing to leaves would turn an 8-chapter book into 357 fragments
    // with a median of 60 words. When the pieces come out that small the
    // nesting wasn't chapter structure, so the section is kept whole.
    if (sub.length && medianWords(sub) < FB2_MIN_MEDIAN_CHAPTER_WORDS) {
      pushChapter(out, partTitle, paragraphsOf(sec, false));
      return;
    }
    for (var si = 0; si < sub.length; si++) out.push(sub[si]);
  };

  for (var i = 0; i < sections.length; i++) {
    walkSection(sections[i], chapters, sections.length === 1);
  }
  } // end if (!isScripture)

  // Fallback: if no <section>s, treat entire body as one chapter
  if (chapters.length === 0) {
    var bodyEl = doc.querySelector("body");
    if (bodyEl) {
      var ps2 = bodyEl.querySelectorAll("p");
      var paras2 = [];
      for (var k = 0; k < ps2.length; k++) {
        var tt = ps2[k].textContent.replace(/\s+/g, " ").trim();
        if (tt) paras2.push(tt);
      }
      if (paras2.length) chapters.push({ heading: bookTitle || "Текст", text: paras2.join("\n\n") });
    }
  }

  if (chapters.length === 0) throw new Error("FB2 file has no readable Russian text.");

  // Anna Karenina's biblical epigraph (Romans 12:19) is read aloud at the
  // start of every audiobook recording but is missing from most FB2 sources.
  // Inject it as the first paragraph of chapter 1 so the displayed text
  // matches what listeners hear.
  if (/Каренин/i.test(bookTitle) && chapters.length > 0) {
    var ded = "«Мне отмщение и Аз воздам»";
    if (chapters[0].text.indexOf(ded) === -1) {
      chapters[0].text = ded + "\n\n" + chapters[0].text;
    }
  }
  // War and Peace: the narrator opens chapter 1 with a spoken announcement —
  // "Лев Николаевич Толстой. Война и мир. Том первый. Часть первая. Глава
  // первая." — that has no counterpart anywhere in the FB2 body (the <title>
  // element carrying "ТОМ ПЕРВЫЙ — ЧАСТЬ ПЕРВАЯ — I" is stripped out above).
  // Without it, the word-level aligner has to bridge ~8 unmatched transcript
  // words before it even reaches the chapter's real text — and because the
  // very next words are a heavily-abbreviated French quote, the small local
  // resync window latches onto a coincidental common word ("и") instead of
  // the real re-sync point, swallowing "Ну, князь, Генуя" into the skipped
  // stretch and breaking highlighting right at the start. Injecting the
  // announcement as visible chapter-1 text (same pattern as the Anna
  // Karenina epigraph above) gives the aligner a real word-for-word match
  // from position zero, so it never needs to guess.
  if (/Война и мир/i.test(bookTitle) && chapters.length > 0) {
    var vimIntro = "Лев Николаевич Толстой. Война и мир. Том первый. Часть первая. Глава первая.";
    if (chapters[0].text.indexOf(vimIntro) === -1) {
      chapters[0].text = vimIntro + "\n\n" + chapters[0].text;
    }
  }
  // Highlighting for Война и мир intentionally starts at offset 0 — the top of
  // the injected announcement above — NOT at "Ну, князь". Two reasons:
  //   1. The narrator SPEAKS the "Лев Николаевич Толстой… Глава первая."
  //      announcement, so it belongs inside the highlightable region and must
  //      light up in sync with the audio (the title/chapter info the reader
  //      expects to follow along).
  //   2. That announcement matches the transcript word-for-word from position
  //      zero, giving the aligner a rock-solid anchor chain before it ever
  //      reaches the tricky French line. An earlier attempt set the start at
  //      "Ну, князь" to dodge the French sentence's stray Russian words
  //      (поместья, мой, верный, раб) — but that discarded the position-zero
  //      anchor, so the cold aligner false-latched onto the common word "и"
  //      (Война И мир ↔ Генуя И Лукка) and highlighting never landed on
  //      "Ну, князь". Starting from the announcement, the aligner is already
  //      synced by the time it reaches the French line, so those stray words
  //      are simply skipped mid-stream instead of derailing the start.
  // => leave highlightStartOffset unset (defaults to 0 at the call site).
  // Anna Karenina's FB2 source has a spurious chapter break in the middle
  // of Part 4 Chapter 5 (the lawyer office scene). The narrator reads it as
  // one continuous chapter; the book actually has 239 chapters, not 240.
  // Merge the truncated short chapter into the next one so the chapter
  // count matches the audiobook manifest.
  if (/Каренин/i.test(bookTitle) && chapters.length === 240) {
    for (var ci = 0; ci < chapters.length - 1; ci++) {
      if (chapters[ci].text.length < 1000) {
        chapters[ci].text = chapters[ci].text + "\n\n" + chapters[ci+1].text;
        chapters.splice(ci + 1, 1);
        break;
      }
    }
  }

  return { chapters: chapters, title: bookTitle || "Unknown title", author: author };
}

// ── FB2 inside a ZIP — common .fb2.zip distribution ─────────────────────────
async function parseFb2Zip(buffer) {
  var zipFiles = parseZip(buffer);
  var keys = Object.keys(zipFiles);
  var fb2Key = keys.find(function(k){ return /\.fb2$/i.test(k); });
  if (!fb2Key) throw new Error("Zip does not contain an .fb2 file.");
  var raw = zipFiles[fb2Key];
  var fb2Text = typeof raw === "string" ? raw : await decompressEntry(raw);
  // Re-encode the decoded text back to bytes so parseFb2 can re-read encoding header.
  var bytes = new TextEncoder().encode(fb2Text);
  return await parseFb2(bytes.buffer);
}

// ── Plain TXT ───────────────────────────────────────────────────────────────
function parseTxt(buffer, fname) {
  var text = decodeBytes(buffer);
  // Defensive: some sources save copy-pasted webpage content as .txt with the
  // HTML tags still present. If we see tags or entities, run it through the
  // HTML stripper before splitting into chapters.
  if (/<\/?[a-zA-Z][a-zA-Z0-9:_-]*[\s>]/.test(text) || /&[a-zA-Z]{2,8};|&#\d+;/.test(text)) {
    text = htmlToText(text);
  }
  if (!/[а-яёА-ЯЁ]/.test(text)) throw new Error("No Russian text found in this file.");
  var chapters = splitTextIntoChapters(text);
  var stem = (fname || "Текст").replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");
  return { chapters: chapters, title: stem, author: "" };
}

// ── HTML (single web page) ──────────────────────────────────────────────────
function parseHtml(buffer, fname) {
  var html = decodeBytes(buffer);
  var titleM = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  var title = titleM ? titleM[1].trim() : (fname || "Текст").replace(/\.[^.]+$/, "");
  var text = htmlToText(html);
  if (!/[а-яёА-ЯЁ]/.test(text)) throw new Error("No Russian text found in this HTML.");
  var chapters = splitTextIntoChapters(text);
  return { chapters: chapters, title: title, author: "" };
}

// ── Master dispatcher — detects format and routes to the right parser ───────
// PDF parsing via pdfjs-dist. Lazy-loaded — only when the user actually opens
// a .pdf file, so we don't bloat the initial bundle for users who only read
// EPUB/FB2/TXT. Worker is loaded from a CDN since Vite's worker bundling for
// pdfjs-dist requires fiddly config; the CDN approach is bulletproof.
async function parsePdf(buffer, fname) {
  var pdfjs;
  try {
    pdfjs = await import('pdfjs-dist');
  } catch (e) {
    throw new Error("Text Cannot Be Parsed. PDF parser failed to load.");
  }
  if (!pdfjs.GlobalWorkerOptions.workerSrc) {
    var version = pdfjs.version || '4.10.38';
    pdfjs.GlobalWorkerOptions.workerSrc =
      'https://cdn.jsdelivr.net/npm/pdfjs-dist@' + version + '/build/pdf.worker.min.mjs';
  }
  try {
    var pdf = await pdfjs.getDocument({ data: new Uint8Array(buffer) }).promise;
    var allText = '';
    for (var i = 1; i <= pdf.numPages; i++) {
      var page = await pdf.getPage(i);
      var content = await page.getTextContent();
      // pdf.js returns text items with x/y coords. Use Y changes to detect line
      // breaks so we preserve some structure (paragraphs, blank lines) rather
      // than producing a single giant blob.
      var pageText = '';
      var lastY = null;
      for (var j = 0; j < content.items.length; j++) {
        var item = content.items[j];
        if (typeof item.str !== 'string') continue;
        var currentY = item.transform ? item.transform[5] : null;
        if (lastY !== null && currentY !== null && Math.abs(currentY - lastY) > 2) {
          pageText += '\n';
        }
        pageText += item.str + ' ';
        lastY = currentY;
      }
      allText += pageText.trim() + '\n\n';
    }
    if (!/[а-яёА-ЯЁ]/.test(allText)) {
      throw new Error('No Russian text found in this PDF.');
    }
    var chapters = splitTextIntoChapters(allText);
    var stem = (fname || 'PDF').replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ');
    var author = '';
    try {
      var meta = await pdf.getMetadata();
      if (meta && meta.info) {
        if (meta.info.Title) stem = String(meta.info.Title).trim() || stem;
        if (meta.info.Author) author = String(meta.info.Author).trim();
      }
    } catch(e) {}
    return { chapters: chapters, title: stem, author: author };
  } catch(e) {
    if (e.message && e.message.indexOf('No Russian') !== -1) throw e;
    throw new Error('Text Cannot Be Parsed. PDF parsing failed: ' + (e.message || 'unknown error'));
  }
}

async function parseBook(buffer, fname) {
  var lower = (fname || "").toLowerCase();
  var bytes = new Uint8Array(buffer);

  // Magic numbers
  var isZip  = bytes.length >= 4 && bytes[0] === 0x50 && bytes[1] === 0x4B; // PK\x03\x04 or PK\x05\x06
  var isXml  = bytes.length >= 5 && bytes[0] === 0x3C && bytes[1] === 0x3F && bytes[2] === 0x78; // "<?x"
  var isPdf  = bytes.length >= 5 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46;
  var isMobi = bytes.length >= 68 && new TextDecoder().decode(bytes.slice(60, 68)) === "BOOKMOBI";

  if (isPdf || lower.endsWith(".pdf")) {
    return await parsePdf(buffer, fname);
  }
  if (isMobi || /\.(mobi|azw3?)$/i.test(lower)) {
    throw new Error("Text Cannot Be Parsed. MOBI / AZW files are typically DRM-locked. Convert to EPUB or FB2 using Calibre (free, calibre-ebook.com) and try again.");
  }

  if (lower.endsWith(".fb2")) return await parseFb2(buffer);
  if (lower.endsWith(".fb2.zip")) return await parseFb2Zip(buffer);
  if (lower.endsWith(".txt")) return parseTxt(buffer, fname);
  if (/\.(html?|xhtml)$/.test(lower)) return parseHtml(buffer, fname);
  if (lower.endsWith(".epub")) return await parseEpub(buffer);

  // No extension match — fall back to magic-number detection.
  if (isZip) {
    // Could be EPUB or FB2-in-zip — try EPUB first (has container.xml), else FB2.
    try { return await parseEpub(buffer); }
    catch(e) {
      try { return await parseFb2Zip(buffer); }
      catch(e2) { throw new Error("Text Cannot Be Parsed. The ZIP file is neither an EPUB nor an FB2 archive."); }
    }
  }
  if (isXml) {
    try { return await parseFb2(buffer); }
    catch(e) { throw new Error("Text Cannot Be Parsed. The XML file is not a valid FB2 document."); }
  }
  // Last resort: try treating as plain text. If that fails (no Russian content
  // / unreadable bytes), surface the canonical "Text Cannot Be Parsed" message.
  try {
    return parseTxt(buffer, fname);
  } catch(e) {
    if (e.message && e.message.indexOf('No Russian') !== -1) throw e;
    throw new Error("Text Cannot Be Parsed. Unrecognized file format. Supported formats: EPUB, FB2 (.fb2 or .fb2.zip), TXT, HTML, PDF.");
  }
}

// PUSHKIN_PNG: white-on-transparent silhouette of Alexander Pushkin (right-facing profile).
// Rendered via CSS mask so the silhouette picks up `currentColor` from its container,
// blending with the rest of the warm-tone palette.
var PUSHKIN_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG4AAACWCAYAAAA/mr2PAAACvUlEQVR42u3dW1LDMBBEUaTK/rccfqCKDyCQ6DEtn14A2Lq6o5HiOG9vIiIiZ6Zd4Sbv9/v94UC01oArCufPgxIAsV0dUirABlQmvBtQmpNjoVS07gZWZm6AZaYbgswJ2NiWue4x7oWJuXNyAhcKsI2+iauVxq/3vLJ8NsBeX8s+7z8G3BXa/apHXg2wTHiak4AOcgi4K5+GVLr3DlomPKUyFF5nW2YYF2odcIxjHXAC3KnW9eolAbwnwYEWWCpBq2tdBy0TXgctE56uMhQecKc0J8qkDbhyCZwAB5z8ltlPhgHHONkKLu19H7pKiYIH3ElrnHJZ3zrGhcID7qRS6aC5vnWMC4XnY51QeIwLhQdcKDzgQuEBFwrPIXMoPMaFwnNWGQrvR+PAqw3v11IJXt3cDMGevCqF5sQGXFYGuFDrgAuFB9yppdKWoGhXurobkjFiKJW6SgFOxoPTrOxf3xgXCu1pcKzbC+0l48DbO269wkXIhjWufcRQLjZ3xh91ulJ4jWPhwRtwAEPBKZuh4EALNk4K7uPYti+eqxxozaPJOrJRa4xbX+bKlkrQNCegAXcONODs485N1fXapwOhJRS4UIhK5aCJunqyNrZlGsi4UAOBC+1IgQuF11JmmLWPcUfYB1wovF5xNoHHuGMD3JXBKZPrx4xxVzWObYHgQNs36ZVKXaUAJ8AB9018aZFxOkvgGKdcKpVSEhzrGCerwbEu2Djw1m0JlMpC8Ib8fhzrats37SVsEMyFN61UgjcXnjUudN2b/tpDwz/HvunGgTdnDPuufyyFNuDgrRu3vvoiAAwzjn1jx6lXvCh5PD4lBs8T0f+f1D3lQkEraBz7/j+By8507wMLBXclgM8sFTFri/c8h4I7CeKIZiy+m0uCGPG7AyDO3eocvX/aAXLVnvSSG99RQB0ciIiIjM87TzG8n8xH9rsAAAAASUVORK5CYII=";
var PUSHKIN_ASPECT = 150 / 110;  // height / width of the source image

function Pushkin({ size }) {
  var s = size || 56;
  var maskStyle = {
    display: "inline-block",
    width: s,
    height: Math.round(s * PUSHKIN_ASPECT),
    backgroundColor: "currentColor",
    WebkitMaskImage: "url(" + PUSHKIN_PNG + ")",
    WebkitMaskRepeat: "no-repeat",
    WebkitMaskSize: "contain",
    WebkitMaskPosition: "center",
    maskImage: "url(" + PUSHKIN_PNG + ")",
    maskRepeat: "no-repeat",
    maskSize: "contain",
    maskPosition: "center",
    verticalAlign: "middle",
  };
  return <span style={maskStyle} aria-label="Pushkin"/>;
}


function FileBtn({ label, onLoad }) {
  var ref = useRef(null);
  var [busy, setBusy] = useState(false);
  var [err, setErr] = useState("");
  var go = async function(e) {
    var f = e.target.files && e.target.files[0];
    if (!f) return;
    setBusy(true); setErr("");
    try {
      var buf = await f.arrayBuffer();
      if (buf.byteLength < 100) throw new Error("File too small");
      onLoad(buf, f.name);
    } catch(ex) { setErr(ex.message); }
    setBusy(false); e.target.value = "";
  };
  return (
    <div style={{display:"flex",flexDirection:"column",gap:6,width:"100%"}}>
      <input ref={ref} type="file" accept=".epub,.fb2,.zip,.txt,.html,.htm,.xhtml,.pdf" style={{display:"none"}} onChange={go}/>
      <button className="btn-p" onClick={function(){ ref.current && ref.current.click(); }} disabled={busy}>
        {busy ? "Loading…" : "📂 " + label}
      </button>
      {err && <p style={{color:"#9d4630",fontSize:13}}>{err}</p>}
    </div>
  );
}

// Strict Chrome detection: actual Google Chrome only — NOT Edge, Brave, Opera,
// Yandex, Vivaldi, Samsung Internet. Cached after the first call since this
// can never change during a session. Note: Arc browser is indistinguishable
// from Chrome here (it inherits Chromium's UA and vendor unchanged), so Arc
// users will be treated as Chrome users.
var _isChromeCached = null;
function isStrictChrome() {
  if (_isChromeCached !== null) return _isChromeCached;
  if (typeof navigator === "undefined") return (_isChromeCached = false);
  var ua = navigator.userAgent || "";
  // Brave exposes navigator.brave even when masking its UA — most reliable signal
  if (navigator.brave) return (_isChromeCached = false);
  if (/Edg\//.test(ua))           return (_isChromeCached = false); // Edge
  if (/OPR\//.test(ua))           return (_isChromeCached = false); // Opera
  if (/SamsungBrowser/.test(ua))  return (_isChromeCached = false);
  if (/YaBrowser/.test(ua))       return (_isChromeCached = false); // Yandex
  if (/Vivaldi/.test(ua))         return (_isChromeCached = false);
  // Must have Chrome/ in UA AND vendor must be Google Inc.
  _isChromeCached = /Chrome\//.test(ua) && (navigator.vendor || "") === "Google Inc.";
  return _isChromeCached;
}

// Local (Windows SAPI) Microsoft voices like "Microsoft Pavel - Russian (Russia)".
// Distinct from the network "Microsoft ... Online (Natural)" voices: those have
// localService === false, so the && check excludes them.
function isLocalMsVoice(v) {
  return /^microsoft\b/i.test(v.name) && v.localService === true;
}

// ── Frequency word bank ("🗂️ Vocab" drill) — DISABLED ────────────────────
// Turned off and removed from the main menu. The implementation below is
// left intact: flip this to true and the card, its screen, its saved
// progress and its data loading all come back exactly as they were.
//
// While false, nothing about it runs — in particular the three
// /vocab/blocks/*.json fetches that used to fire on every page load are
// skipped, so a disabled feature costs nothing.
var WORDBANK_ENABLED = false;

export default function App() {
  // ── Account (optional) ────────────────────────────────────────────────────
  // The site is public: everything readable works signed out. An account only
  // adds cross-device vocabulary/tips/progress, and admin rights for the
  // ADMIN_EMAIL account. The session is an HttpOnly cookie set by
  // /api/auth/login, so there is no token for this code to hold or refresh --
  // same-origin fetches carry it automatically.
  var [me, setMe]             = useState(null);   // { id, email, isAdmin } | null
  var [curate, setCurate]     = useState(null);   // admin: glossary entry being written
  var [sayState, setSayState] = useState("");     // popup audio: "" | "playing" | "none"
  var sayAudioRef             = useRef(null);
  var [authReady, setAuthReady] = useState(false); // false until /api/auth/me answers
  var [authOpen, setAuthOpen] = useState(false);  // sign-in panel visible
  var [authMode, setAuthMode] = useState("signup"); // "login" | "signup" — the gate leads with registration
  var [authEmail, setAuthEmail]       = useState("");
  var [authPassword, setAuthPassword] = useState("");
  var [authBusy, setAuthBusy] = useState(false);
  var [authErr, setAuthErr]   = useState("");
  var [authNotice, setAuthNotice] = useState("");   // "waiting for approval" and similar

  // credentials:"same-origin" is the default for same-origin requests, but it
  // is stated here because every call that needs the session goes through
  // this wrapper and the intent should be obvious at the call site.
  var authFetch = function(url, options) {
    options = options || {};
    return fetch(url, Object.assign({}, options, { credentials: "same-origin" }));
  };

  useEffect(function() {
    var cancelled = false;
    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function(r) { return r.ok ? r.json() : { user: null }; })
      .then(function(d) { if (!cancelled) setMe(d && d.user ? d.user : null); })
      .catch(function() { if (!cancelled) setMe(null); })
      .finally(function() { if (!cancelled) setAuthReady(true); });
    return function() { cancelled = true; };
  }, []);

  var submitAuth = async function(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (authBusy) return;
    setAuthBusy(true); setAuthErr(""); setAuthNotice("");
    try {
      var r = await fetch("/api/auth/" + authMode, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail.trim(), password: authPassword }),
      });
      var d = await r.json().catch(function() { return {}; });
      if (!r.ok) throw new Error(d.error || "Sign-in failed");
      // A new account is created but not signed in: it waits for approval.
      if (d.pending || !d.user) {
        setAuthNotice(d.message || "Your account has been created and is waiting for approval. You'll be able to sign in once it's approved.");
        setAuthPassword("");
        setAuthMode("login");
        return;
      }
      setMe(d.user || null);
      setAuthOpen(false);
      setAuthPassword("");
    } catch (err) {
      setAuthErr(err.message || "Sign-in failed");
    } finally {
      setAuthBusy(false);
    }
  };

  var signOut = async function() {
    try { await fetch("/api/auth/logout", { credentials: "same-origin" }); } catch(_) {}
    setMe(null);
    setShowAdmin(false);
  };

  // Admin panel state — opened from the header. Only shown for the admin
  // account; ADMIN_EMAIL now lives only on the server (lib/auth.js), so the
  // client learns about it from /api/auth/me rather than from a build-time var.
  var [showAdmin, setShowAdmin]   = useState(false);
  var [adminUsers, setAdminUsers] = useState([]);
  var [adminLoad, setAdminLoad]   = useState(false);
  var [adminErr, setAdminErr]     = useState("");
  // Upload-song panel state — admin-only, accessed via "📤 Upload" trigger.
  // Pasted song goes to a per-artist .txt in public/books/lyrics/ via the
  // /api/admin/upload-song endpoint (commits to GitHub → Vercel redeploys).
  // The same modal also handles full-book uploads via a Song/Book tab toggle.
  var [showUpload, setShowUpload]   = useState(false);
  var [upMode, setUpMode]           = useState("book");  // "song" | "book"
  var [upArtist, setUpArtist]       = useState("");
  var [upTitle, setUpTitle]         = useState("");
  var [upLyrics, setUpLyrics]       = useState("");
  var [upBusy, setUpBusy]           = useState(false);
  var [upMsg, setUpMsg]             = useState("");
  var [upErr, setUpErr]             = useState("");
  // Book-upload-specific fields (only used when upMode === "book")
  var [upBookFile, setUpBookFile]     = useState(null);
  var [upBookAuthor, setUpBookAuthor] = useState("");
  var [upBookCategory, setUpBookCategory] = useState("Works");
  // Song-picker state — opened when the user picks a Song Lyrics artist from
  // the library dropdown. Lists the artist's individual songs so the user can
  // jump straight to one instead of starting at song 1.
  var [songPickerBook, setSongPickerBook] = useState(null);
  // Ref to the song picker panel — used to scroll the picker into view
  // automatically when it appears (so the user isn't left wondering where
  // "pick a song" went after selecting an artist from the dropdown).
  var songPickerRef = useRef(null);
  var [songPickerList, setSongPickerList] = useState([]);  // [{ title, index }]
  var [songPickerLoad, setSongPickerLoad] = useState(false);
  var [songPickerErr, setSongPickerErr]   = useState("");
  // When the song picker appears, smooth-scroll it into view so the user
  // doesn't lose track of where it landed (could be far below the dropdown,
  // depending on how many books are in the library).
  useEffect(function() {
    if (songPickerBook && songPickerRef.current) {
      // Defer one frame so the picker has actually rendered before scrolling.
      requestAnimationFrame(function() {
        if (songPickerRef.current) {
          songPickerRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    }
  }, [songPickerBook]);
  // Admin is decided by the server (ADMIN_EMAIL, checked in lib/auth.js);
  // this flag only decides what the UI offers. Every admin route re-checks.
  var isAdmin = !!(me && me.isAdmin);

  // ── Where a book's files live ─────────────────────────────────────────────
  // Ordinary books are static assets under /books/. Restricted ones are not
  // published at all: /api/catalogue returns them (to the admin only) with
  // fileUrl / audiobook.chapterUrls pointing at /api/media, which checks the
  // session before returning anything. Everything below goes through these
  // two helpers so a restricted book never falls back to a public path.
  var bookFileUrl = function(book) {
    if (book && book.fileUrl) return book.fileUrl;
    return "/books/" + (book && book.filename);
  };
  var chapterJsonUrl = function(audiobook, index) {
    if (audiobook && Array.isArray(audiobook.chapterUrls) && audiobook.chapterUrls[index]) {
      return audiobook.chapterUrls[index];
    }
    var path = audiobook && Array.isArray(audiobook.chapters) ? audiobook.chapters[index] : null;
    if (!path) return null;
    return path.indexOf("/") === 0 ? path : ("/books/" + path);
  };
  // A restricted book's audio lives in a private bucket, so its JSON carries
  // a key rather than a public URL; /api/media signs a short-lived URL for it.
  var audioSrcFor = function(json, restricted) {
    if (!json || !json.audio_url) return null;
    if (!restricted) return json.audio_url;
    var key = json.audio_url;
    try { key = new URL(json.audio_url, window.location.href).pathname; } catch (e) {}
    return "/api/media?audio=" + encodeURIComponent(String(key).replace(/^\/+/, ""));
  };

  var [msgs, setMsgs]         = useState([]);
  var [input, setInput]       = useState("");
  // How much text one dropdown row can hold. A native <select> hands its open
  // list to the OS on phones, which ignores CSS on <option> entirely — so a row
  // is made to fit by shortening the STRING, not by styling it. The budget is
  // derived from the viewport so it adapts instead of guessing at one phone.
  var [optChars, setOptChars] = useState(999);
  useEffect(function() {
    var measure = function() {
      var w = typeof window !== "undefined" ? window.innerWidth : 1200;
      // Below ~700px the picker is full-width and modal; above it, rows are
      // roomy enough that truncating would only lose information.
      setOptChars(w >= 700 ? 999 : Math.max(16, Math.floor((w - 56) / 8.2)));
    };
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("orientationchange", measure);
    return function() {
      window.removeEventListener("resize", measure);
      window.removeEventListener("orientationchange", measure);
    };
  }, []);

  var [loading, setLoading]   = useState(false);
  // CEFR level for chat conversations. Persisted in localStorage so the user
  // doesn't have to re-pick each session. Defaults to B1 (the prior hard-coded
  // value, so behavior for existing users is unchanged on first load).
  var [level, setLevel]       = useState(function(){
    try { return localStorage.getItem("gv_chat_level") || "B1"; }
    catch(e) { return "B1"; }
  });
  useEffect(function() {
    try { localStorage.setItem("gv_chat_level", level); } catch(e) {}
  }, [level]);
  var [vocab, setVocab]       = useState([]);
  var [tips, setTips]         = useState([]);
  // savedTopics: array of curriculum topic IDs the user has bookmarked from
  // the grammar reference. Stored as just IDs (e.g. "a2-accusative") so saved
  // entries stay in sync if curriculum.json gets edited later. Mirrors the
  // vocab/tips persistence pattern below.
  var [savedTopics, setSavedTopics] = useState([]);
  var [tab, setTabRaw]        = useState("chat");
  // Switching tabs is a navigation moment: check whether a newer build
  // has been deployed before rendering the next screen.
  var setTab = function(t) { checkForUpdate(); setTabRaw(t); };
  var [started, setStarted]   = useState(false);
  var [mode, setMode]         = useState("read"); // chat removed; default to reading
  var [noAIMode, setNoAIMode] = useState(false);  // define uses AI; chat-specific UI gated separately below
  // Clear any leftover "no_ai_mode_v1" flag from older versions so users who previously
  // bypassed login don't get stuck in a partially-broken state.
  useEffect(function() {
    try { localStorage.removeItem("no_ai_mode_v1"); } catch(e) {}
  }, []);
  var [bookMeta, setBookMeta] = useState({title:"", author:""});

  var [showTopic, setShowTopic] = useState(false);
  var [showWord,  setShowWord]  = useState(false);
  var [showTip,   setShowTip]   = useState(false);
  var [nRu, setNRu] = useState("");
  var [nEn, setNEn] = useState("");
  var [nTip, setNTip] = useState("");

  // ── Vocab quiz state ──────────────────────────────────────────────────────
  // Active when the user clicks "Review vocab" on the vocab tab. We generate
  // multiple-choice questions where the correct answer is the English meaning
  // of the Russian word, and the 3 distractors are English meanings from OTHER
  // words OF THE SAME PART OF SPEECH (verbs quiz against verbs only, nouns
  // against nouns, etc.).
  var [quizMode, setQuizMode]         = useState(false);
  var [quizMenu, setQuizMenu]         = useState(false);  // shows the 2-choice "Quiz vs Chat" menu
  var [quizQuestions, setQuizQuestions] = useState([]);
  var [quizIdx, setQuizIdx]           = useState(0);
  var [quizSelected, setQuizSelected] = useState(null);
  var [quizScore, setQuizScore]       = useState(0);
  var [quizSkipNote, setQuizSkipNote] = useState("");

  // ── Exercises (grammar/reading drills tied to the current chapter) ─────────
  // exData: the loaded exercise set for the current chapter (or null).
  // exCat: which category the user picked ("menu" | "grammar" | "reading").
  // The grammar quiz reuses the same MC pattern as the vocab quiz.
  var [exData, setExData]         = useState(null);
  var [exCat, setExCat]           = useState("menu");
  var [exQuestions, setExQuestions] = useState([]);
  var [exIdx, setExIdx]           = useState(0);
  var [exSelected, setExSelected] = useState(null);
  var [exScore, setExScore]       = useState(0);
            // Exercise audio clips: play the snippet of the recording for a question's
  // sentence, located in the current chapter's word_timings. exPlaying = the id
  // of the clip currently playing (drives the ▶/⏸ button state).
  var [exPlaying, setExPlaying]   = useState(null);
  var exClipAudioRef              = useRef(null);
  var exClipRafRef                = useRef(null);

  // ── Frequency Vocab Bank ("🗂️ Vocab" mode) ──────────────────────────────
  // A static, AI-free vocabulary trainer built from public/vocab/blocks/*.json
  // (a global word-frequency list, imperfective/perfective verb pairs already
  // merged into single cards at data-build time — see /home/claude/vocab on
  // the build machine, not shipped). No live AI calls at runtime.
  // wbIndex: blocks/index.json (block list + rank ranges), loaded once.
  // wbDistractors: blocks/distractors.json, pos -> pool of English glosses
  //   (pooled across the WHOLE bank, not just one block, so every block has
  //   enough same-part-of-speech distractors for a 4-option question).
  // wbProgress: persisted map cardId -> {streak, mastered}. A card needs 10
  //   CONSECUTIVE correct answers to be mastered (a miss resets the streak to
  //   0); "I already know this word" masters it instantly. wbBlockNum is the
  //   1-based block the user is currently working through; the next block
  //   unlocks once every card in the current one is mastered.
  var [wbIndex, setWbIndex]             = useState(null);
  var [wbDistractors, setWbDistractors] = useState(null);
  var [wbBlockNum, setWbBlockNum]       = useState(1);
  var [wbCards, setWbCards]             = useState(null);
  var [wbProgress, setWbProgress]       = useState({});
  var [wbScreen, setWbScreen]           = useState("landing"); // "landing" | "quiz"

  // ── Forum (book requests / bugs / general) ──────────────────────────────
  // Backed by /api/forum/* rewrites into user-data.js — see that file.
  var FORUM_CATS = [
    { id: "requests", label: "📚 Book requests" },
    { id: "bugs",     label: "🐞 Bugs" },
    { id: "general",  label: "💬 General" },
  ];
  var [forumCat, setForumCat]         = useState("requests");
  var [forumPosts, setForumPosts]     = useState(null);   // null = loading
  var [forumThread, setForumThread]   = useState(null);   // open post, or null = list view
  var [forumErr, setForumErr]         = useState("");
  var [forumBusy, setForumBusy]       = useState(false);
  var [forumCompose, setForumCompose] = useState(false);
  var [forumTitle, setForumTitle]     = useState("");
  var [forumBody, setForumBody]       = useState("");
  var [forumReply, setForumReply]     = useState("");

  // ── Music tab: artists → songs → lyrics with definable words + video ──
  var [musicData, setMusicData]     = useState(null);
  var [musicArtist, setMusicArtist] = useState(null);   // index into musicData
  var [musicSong, setMusicSong]     = useState(null);   // index into artist.songs
  useEffect(function() {
    if (tab !== "music" || musicData) return;
    var cancelled = false;
    fetch(MUSIC_URL)
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){ if (!cancelled && j) setMusicData(j); })
      .catch(function(){});
    return function(){ cancelled = true; };
  }, [tab, musicData]);
  // Lyrics rendering: every Russian word clickable for a definition, line
  // breaks preserved, stanzas separated by wider gaps.
  var renderLyrics = function(text) {
    return String(text||"").split("\n").map(function(line, li) {
      if (!line.trim()) return <div key={li} style={{height:14}}/>;
      var parts = line.match(/[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+/g) || [];
      return (
        <div key={li} style={{lineHeight:1.75}}>
          {parts.map(function(pt, wi) {
            if (/[а-яёА-ЯЁ]/.test(pt[0])) {
              return <span key={wi} className="rw" onClick={function(e){ defWord(pt, e); }}>{pt}</span>;
            }
            return <span key={wi}>{pt}</span>;
          })}
        </div>
      );
    });
  };

  var forumApi = async function(action, opts) {
    opts = opts || {};
    var r = await authFetch("/api/forum/" + action + (opts.qs || ""), opts.post ? {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts.post),
    } : undefined);
    var d = await r.json().catch(function(){ return {}; });
    if (!r.ok) throw new Error(d.error || ("HTTP " + r.status));
    return d;
  };
  var loadForumBoard = async function(cat) {
    setForumErr(""); setForumPosts(null); setForumThread(null);
    try {
      var d = await forumApi("board", { qs: "?cat=" + cat });
      setForumPosts(d.posts || []);
    } catch (e) { setForumErr(e.message || "Could not load the forum"); setForumPosts([]); }
  };
  var openForumThread = async function(id) {
    setForumErr(""); setForumBusy(true);
    try {
      var d = await forumApi("thread", { qs: "?cat=" + forumCat + "&id=" + encodeURIComponent(id) });
      setForumThread(d);
    } catch (e) { setForumErr(e.message || "Could not open the post"); }
    setForumBusy(false);
  };
  var submitForumPost = async function() {
    if (forumBusy) return;
    setForumErr(""); setForumBusy(true);
    try {
      await forumApi("new", { post: { cat: forumCat, title: forumTitle, body: forumBody } });
      setForumTitle(""); setForumBody(""); setForumCompose(false);
      await loadForumBoard(forumCat);
    } catch (e) { setForumErr(e.message || "Could not post"); }
    setForumBusy(false);
  };
  var submitForumReply = async function() {
    if (forumBusy || !forumThread) return;
    setForumErr(""); setForumBusy(true);
    var tid = forumThread.id;
    try {
      await forumApi("reply", { post: { cat: forumCat, id: tid, body: forumReply } });
      setForumReply("");
      var d = await forumApi("thread", { qs: "?cat=" + forumCat + "&id=" + encodeURIComponent(tid) });
      setForumThread(d);
    } catch (e) { setForumErr(e.message || "Could not reply"); }
    setForumBusy(false);
  };
  var toggleForumVote = async function(id) {
    try {
      var d = await forumApi("vote", { post: { cat: forumCat, id: id } });
      setForumThread(function(t){ return (t && t.id === id) ? Object.assign({}, t, { voteCount: d.voteCount, youVoted: d.youVoted }) : t; });
      setForumPosts(function(list){
        if (!list) return list;
        return list.map(function(pp){ return pp.id === id ? Object.assign({}, pp, { voteCount: d.voteCount }) : pp; });
      });
    } catch (e) { setForumErr(e.message || "Vote failed"); }
  };
  var forumMod = async function(op) {
    if (!forumThread) return;
    var tid = forumThread.id;
    setForumErr("");
    try {
      await forumApi("mod", { post: { cat: forumCat, id: tid, op: op } });
      if (op === "delete") { await loadForumBoard(forumCat); return; }
      var d = await forumApi("thread", { qs: "?cat=" + forumCat + "&id=" + encodeURIComponent(tid) });
      setForumThread(d);
    } catch (e) { setForumErr(e.message || "Action failed"); }
  };
  var forumWhen = function(ts) {
    if (!ts) return "";
    var d = new Date(ts);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };
  useEffect(function() {
    if (tab === "forum" && me) loadForumBoard(forumCat);
  }, [tab, forumCat, me && me.id]);
  var [wbCur, setWbCur]                 = useState(null);      // {card, correct, options}
  var [wbSel, setWbSel]                 = useState(null);
  var [wbJustMastered, setWbJustMastered] = useState(null);    // card id, brief toast
  var [wbLoading, setWbLoading]         = useState(false);

  var [popup, setPopup]   = useState(null);
  var [popXY, setPopXY]   = useState({top:100,left:16});
  var popRef = useRef(null);
  // Two-choice bubble shown when a Russian word is clicked: define it, or
  // start the audio from that word. Clicking a word used to go straight to
  // the definition, which left no way to move around inside a recording
  // except the player's skip buttons — and those jumped by *sentence*, which
  // is why they kept knocking the word-level highlighter back into
  // sentence mode. Seeking from the word itself replaces them.
  // After the popup renders, clamp it so it never extends below the viewport.
  // The initial position is an estimate; this corrects it using actual height.
  useEffect(function() {
    if (!popup || !popRef.current) return;
    var el = popRef.current;
    var r = el.getBoundingClientRect();
    var vh = window.innerHeight;
    var pad = 12;
    if (r.bottom > vh - pad) {
      var overflow = r.bottom - (vh - pad);
      var newTop = Math.max(pad, popXY.top - overflow);
      if (newTop !== popXY.top) setPopXY(function(prev){ return {top: newTop, left: prev.left}; });
    }
  }, [popup]);

  // First-visit landing screen: remembered in localStorage so users only see it once per device.
  var [seenLanding, setSeenLanding] = useState(function() {
    try { return localStorage.getItem("landing_seen_v1") === "1"; } catch(e) { return false; }
  });
  var dismissLanding = function() {
    try { localStorage.setItem("landing_seen_v1", "1"); } catch(e) {}
    setSeenLanding(true);
  };

  var [chapters, setChapters]   = useState([]);
  // Pre-loaded library: books shipped in /public/books/. Fetched once on mount from /books/index.json.
  var [presetBooks, setPresetBooks] = useState([]);
  var srcJumpChapterRef = useRef(null);
  var srcJumpOffsetRef = useRef(null);  // vocab source-link: char offset of the saved word, to highlight its sentence on arrival
  var [vocabCollapsed, setVocabCollapsed] = useState({});
  // Tracks recent uploads (last MAX_UPLOADS) so the library view can show them
  // alongside the preset books. Each entry is metadata; full content lives at
  // storage[UPLOAD_BOOK_PREFIX + id].
  var [uploadedBooks, setUploadedBooks] = useState([]);
  // Per-book progress map. Loaded from storage on mount and after every save.
  // Drives the "Continue reading" section on the library screen.
  var [progressMap, setProgressMap] = useState({});
  useEffect(function() {
    (async function() {
      try {
        var r = await storage.get(BOOK_PROGRESS);
        if (r) setProgressMap(JSON.parse(r.value) || {});
      } catch(e) {}
    })();
  }, []);

  // Save a book's reading progress. Debounced via the deps so it only fires
  // when the page/chapter actually changes — not on every render.
  var saveBookProgress = async function(meta, ci, pi, totalChapters) {
    var key = bookKey(meta);
    if (!key || !meta.title) return;
    try {
      var r = await storage.get(BOOK_PROGRESS);
      var all = r ? (JSON.parse(r.value) || {}) : {};
      all[key] = {
        cidx: ci, pidx: pi,
        lastRead: Date.now(),
        title: meta.title,
        author: meta.author || "",
        filename: meta.filename || "",
        category: meta.category || "",
        splitByNumberedSections: !!meta.splitByNumberedSections,
        totalChapters: totalChapters || 0,
      };
      await storage.set(BOOK_PROGRESS, JSON.stringify(all));
      setProgressMap(all);
    } catch(e) {}
  };
  // Search filter for the library view — filters both preset + uploaded.
  var [bookSearch, setBookSearch] = useState("");
  // Tracks which book is currently being loaded (after click). Shows a spinner
  // overlay on the card and disables further clicks during the fetch+parse cycle
  // so the user gets clear feedback that the click registered.
  var [bookLoading, setBookLoading] = useState(null);  // null or filename/id
  // Grammar curriculum (📚 Grammar mode). Loaded once from /grammar/curriculum.json.
  // gramLevel = currently-selected CEFR level (e.g. "A2"); "" before user picks.
  // gramTopicId = currently-viewed topic's id; "" means "still on the picker screen".
  // gramSearch = search query; when non-empty, replaces the picker dropdowns with
  //   a cross-level result list.
  var [curriculum, setCurriculum] = useState(null);
  var [gramLevel, setGramLevel]   = useState("");
  var [gramTopicId, setGramTopicId] = useState("");
  var [gramErr, setGramErr]       = useState("");
  var [gramSearch, setGramSearch] = useState("");
  var [cidx, setCidx]           = useState(0);
  var [expandedPart, setExpandedPart] = useState(null);
  var [expandedNav, setExpandedNav] = useState({});
  var [pidx, setPidx]           = useState(0);  // Current page within the current chapter
  // Dual-language pane. The English column lives one horizontal scroll to the
  // right of the Russian one. That reads well on a phone, but on desktop the
  // only affordance was the container's own scrollbar — which sits at the
  // BOTTOM of a full chapter, so a reader had to scroll to the end of the page
  // to find the control that reveals the translation. Hence a floating toggle.
  var [dualPane, setDualPane]   = useState(0);  // 0 = Russian, 1 = English
  var dualRef                   = useRef(null);
  var [cbm,  setCbm]            = useState(0);
  var [lview, setLview]         = useState("read");
  var [lsearch, setLsearch]     = useState("");
  var [lres, setLres]           = useState([]);
  var [fErr, setFErr]           = useState("");

  var [voice, setVoice]         = useState(null); // native browser TTS (Azure removed)
  // Mirror of `voice` in a ref so async callbacks always read the latest value.
  var voiceRef = useRef(null); // native browser TTS (Azure removed)
  useEffect(function() { voiceRef.current = voice; }, [voice]);
  var [allVoices, setAllVoices] = useState([]);
  // Tracks whether the user has explicitly picked a voice from the picker.
  // Chrome on PC fires `onvoiceschanged` multiple times as Google network voices
  // load asynchronously — without this guard, each fire re-runs the auto-selector
  // and stomps the user's manual pick. Ref (not state) so we can read the
  // up-to-date value from inside useEffect closures.
  var userPickedRef = useRef(false);
  // Bumped from v1 → v2 to wipe out stale Milena/Google saves from before the
  // cloud-first default became active. Old keys are intentionally orphaned.
  var GVT_VOICE_KEY = "gv_voice_v2";  // localStorage: persist voice pick across sessions
  // ── Floating audio bar state (reading mode) ─────────────────────────────
  // Sentence-by-sentence playback via the browser's native speechSynthesis.
  // Parses the current page into sentences and speaks them sequentially.
  //
  // Gapless playback: while one sentence plays, we prefetch the next sentence
  // in the background. When the current audio ends, the next sentence's blob
  // is already cached and starts playing within ~100ms instead of after a
  // full fetch round-trip (~500-1000ms). Cache keyed by sentence index, reset
  // on page/chapter change. Generation counter (audioGenRef) prevents stale
  // fetches from playing after the user has skipped or paused/resumed.
  var [audioSentences, setAudioSentences] = useState([]);
  var [audioIdx, setAudioIdx] = useState(0);
  var [audioPlaying, setAudioPlaying] = useState(false);
  var [audioFetching, setAudioFetching] = useState(false);
  var audioElemRef = useRef(null);
  var audioCacheRef = useRef({});  // idx → Promise<Blob>
  var audioGenRef = useRef(0);     // incremented when a playback intent is superseded
  // Playback rate in Azure-percent. -25 = noticeably slower (good for tough
  // passages), -8 = the previous default (slightly slow for learners),
  // 0 = natural, +15 = slightly fast (good for familiar text).
  var SPEED_OPTIONS = [{ label: "Slow", rate: -25 }, { label: "Normal", rate: -8 }, { label: "Fast", rate: 15 }];
  var [audioSpeedIdx, setAudioSpeedIdx] = useState(1);  // default = Normal (-8)
  var audioSpeedRef = useRef(-8);
  useEffect(function() {
    audioSpeedRef.current = SPEED_OPTIONS[audioSpeedIdx].rate;
    // Speed change invalidates cached audio (was rendered at the old rate).
    // Cache wipe is safe — next prefetch will rebuild at the new rate.
    audioCacheRef.current = {};
  }, [audioSpeedIdx]);
  var sentenceOverrideRef = useRef(null);

  // ── Sentence-level reading highlight ───────────────────────────────────────
  // As Azure plays a sentence, we tint every word in that sentence's character
  // range. This sidesteps the word-timing heuristic entirely (which lagged or
  // ran ahead depending on Dmitry's tempo): we already know exactly which
  // sentence is playing, because we're driving each fetch ourselves. No RAF
  // loop, no per-millisecond calculation — toggle a class once per sentence.
  var highlightedElementsRef = useRef([]);  // DOM nodes currently lit up
  // Live mirror of `currentPage`, read by the vocab source-link jump, which runs
  // audiobook RAF loop, which captures its closure once at play time and is NOT
  // restarted on a within-chapter page flip. Reading currentPage directly would
  // therefore use the page that was current when playback started, so after a
  // flip chapterStart/chapterEnd point at the old page's char range and nothing
  // matches — the highlight silently disappears. Reading from this ref keeps the
  // highlight anchored to whatever page is actually on screen. (Synced below,
  // once currentPage is defined.)
  var currentPageRef = useRef(null);

  // ── Audiobook mode (real human narration with pre-aligned timestamps) ─────
  // When a book entry in index.json carries an `audiobook.chapters[cidx]`
  // path, we fetch that chapter's alignment JSON at chapter-load time. It
  // contains the streaming audio URL plus per-sentence {begin, end} pairs.
  // Playback is then a single persistent HTMLAudioElement streaming from
  // archive.org (or wherever), with a RAF loop that maps audio.currentTime
  // to one of the parsed sentences and applies the same .rw-reading
  // highlight that TTS mode uses.
  var [audiobookData, setAudiobookData] = useState(null);    // {audio_url, fragments[], narrator?, year?}
  var [audiobookMode, setAudiobookMode] = useState(false);   // user-toggleable; defaults true when audiobookData arrives
  var audiobookAudioRef = useRef(null);                      // persistent <audio> streaming the recording
  var [abCur, setAbCur] = useState(0);                       // audiobook playhead position (s), for the counter/scrubber
  var [abDur, setAbDur] = useState(0);                       // audiobook total duration (s)
  var fmtClock = function(s){ s = Math.max(0, Math.floor(s || 0)); var mm = Math.floor(s / 60), ss = s % 60; return mm + ":" + (ss < 10 ? "0" : "") + ss; };
  // Dual-language Bible: English (WEB, public domain) shown under each Russian
  // verse. Keyed {verseNumber: englishText} for the CURRENT chapter only.
  var [bibleEn, setBibleEn] = useState(null);
  // Dual-language prose (bookMeta.parallelEn): chapter's paragraph-index → English map.
  var [proseEn, setProseEn] = useState(null);
  // Bible section-heading translations ({russianHeading: englishHeading}), one
  // global file shared by every chapter. Loaded lazily on first Bible chapter.
  var [bibleHeadings, setBibleHeadings] = useState(null);
  var audiobookDataRef = useRef(null);
  useEffect(function() { audiobookDataRef.current = audiobookData; }, [audiobookData]);
  var audiobookModeRef = useRef(false);
  useEffect(function() { audiobookModeRef.current = audiobookMode; }, [audiobookMode]);

  var audioIdxRef = useRef(0);
  useEffect(function() { audioIdxRef.current = audioIdx; }, [audioIdx]);
  var audioPlayingRef = useRef(false);
  useEffect(function() { audioPlayingRef.current = audioPlaying; appBusy.audio = audioPlaying; }, [audioPlaying]);
  // Need sentences accessible from prefetchSentence (called via async chains).
  var audioSentencesRef = useRef([]);
  useEffect(function() { audioSentencesRef.current = audioSentences; }, [audioSentences]);

  // Parse a page of text into sentence-like fragments. Each fragment becomes
  // one speechSynthesis utterance. Rules for what counts as a sentence boundary:
  //   1. End of line is always a boundary.
  //   2. A terminator (. ! ? …) is a boundary ONLY when followed by whitespace
  //      AND the next non-whitespace character is uppercase or an opening
  //      quote/bracket. Lowercase that follows means it's an abbreviation
  //      ("т.е. это", "г. произошло") — keep accumulating.
  //   3. If the "word" immediately before the period is a single capital
  //      letter, it's an initial (А.С. Пушкин) — not a boundary, even though
  //      the next letter is uppercase.
  //   4. Consecutive terminators ("?!", "…") count as a single terminator.
  // The result is an array of {text, start, end} where start/end are
  // character positions within the input text, used later to map a clicked
  // word back to a sentence index.
  // Russian abbreviations that end in a period but DON'T end a sentence, even
  // when followed by a capitalized word. The classic example is "г." — short
  // for "господин" / "город" / "год" — which constantly appears next to a
  // proper noun in Gogol, Tolstoy, and most 19th-century prose ("г. Подточина",
  // "г. Петербург", "в 1842 г."). Without this set, every such occurrence
  // becomes a false sentence break, causing the audio to pause and re-fetch.
  // Lookup is case-insensitive (the lookup converts the captured word to lower).
  var RU_NON_TERMINAL_ABBR = new Set([
    // Single-letter abbreviations (very common)
    "г", "т", "д", "п", "е", "ч", "с", "н",
    // Two-letter abbreviations and plurals
    "тт", "вв", "гг", "сс", "пр", "ст", "до",
    // Longer common abbreviations
    "стр", "рис", "табл", "напр", "тов", "акад", "проф", "имп", "ген",
    "пол", "св", "ул", "пл", "пер", "просп", "обл", "млн", "млрд",
    "тыс", "руб", "коп", "сек", "мин", "см", "мм", "км", "кг", "вып",
    "изд", "гл", "им", "век", "напис", "опубл", "род", "ум",
    // English (sometimes appears in mixed-language texts)
    "mr", "mrs", "ms", "dr", "vs", "etc"
  ]);

  var parseSentences = function(text, opts) {
    opts = opts || {};
    if (!text) return [];

    // Auto-detect verse-numbered text. If the title-based check didn't flag this
    // as Bible, look at the text itself: if many verses appear with their
    // leading number marker (start-of-line or after a sentence terminator),
    // treat the whole text as Bible-like. Catches scriptures whose titles
    // don't match the heuristic (e.g. "Бытие", "Псалом 22").
    var isBible = !!opts.isBible;
    if (!isBible) {
      var sample = text.slice(0, 4000);
      var verseMarkers = sample.match(/(?:^|\n|[.!?…»"]\s)\s*\d+(?::\d+)?[.:]?\s+[А-ЯЁA-Z]/g) || [];
      // Threshold: 6 verse-pattern matches in the first ~4KB strongly suggests
      // scripture. Regular prose with a few dates won't hit this.
      if (verseMarkers.length >= 6) isBible = true;
    }

    var sentences = [];
    var lines = text.split(/\n+/);
    for (var li = 0; li < lines.length; li++) {
      var line = lines[li].trim();
      if (!line) continue;
      var sentStart = 0;
      var pos = 0;
      while (pos < line.length) {
        var ch = line[pos];
        if (ch === "." || ch === "!" || ch === "?" || ch === "…") {
          // Eat any consecutive terminators ("?!", "...", "…")
          var endTerm = pos;
          while (endTerm + 1 < line.length && /[.!?…]/.test(line[endTerm + 1])) endTerm++;
          // What follows?
          var nextIdx = endTerm + 1;
          var isBoundary = false;
          if (nextIdx >= line.length) {
            isBoundary = true;  // end of line
          } else if (!/\s/.test(line[nextIdx])) {
            isBoundary = false; // no whitespace = abbreviation (т.е., decimals)
          } else {
            // Skip whitespace, peek at next real char
            var k = nextIdx;
            while (k < line.length && /\s/.test(line[k])) k++;
            if (k >= line.length) {
              isBoundary = true;
            } else if (/[А-ЯЁA-Z«"„(\[—–]/.test(line[k]) || (isBible && /\d/.test(line[k]))) {
              // Looks like a new sentence — BUT verify the period isn't part
              // of an initial (single capital letter + period before a name).
              // In Bible mode, a digit after a terminator is treated as a new
              // verse marker → sentence boundary (otherwise the whole verse
              // run would stay as one TTS chunk and only the FIRST number
              // would get stripped, leaving the rest pronounced).
              var wEnd = endTerm;
              while (wEnd > 0 && /[.!?…]/.test(line[wEnd - 1])) wEnd--;
              var wStart = wEnd - 1;
              while (wStart >= 0 && /[а-яёА-ЯЁa-zA-Z]/.test(line[wStart])) wStart--;
              wStart++;
              var wordBefore = line.slice(wStart, wEnd);
              var isInitial = wordBefore.length === 1 && /[А-ЯЁA-Z]/.test(wordBefore);
              var isAbbrev = wordBefore.length > 0 && wordBefore.toLowerCase() !== "пол" && RU_NON_TERMINAL_ABBR.has(wordBefore.toLowerCase());
              if (line[endTerm] === "." && (isInitial || isAbbrev)) {
                // Initial ("А.", "С.") or known abbreviation ("г.", "стр.", "т.") — not a sentence end.
                isBoundary = false;
              } else {
                isBoundary = true;
              }
            } else {
              // Lowercase next — abbreviation
              isBoundary = false;
            }
          }
          if (isBoundary) {
            var sentText = line.slice(sentStart, endTerm + 1).trim();
            if (sentText) sentences.push(sentText);
            var sw = endTerm + 1;
            while (sw < line.length && /\s/.test(line[sw])) sw++;
            sentStart = sw;
            pos = sw;
          } else {
            pos = endTerm + 1;
          }
        } else {
          pos++;
        }
      }
      if (sentStart < line.length) {
        var lastSent = line.slice(sentStart).trim();
        if (lastSent) sentences.push(lastSent);
      }
    }
    // Locate each sentence in the original text to track character ranges.
    var result = [];
    var searchFrom = 0;
    for (var k = 0; k < sentences.length; k++) {
      var idx = text.indexOf(sentences[k], searchFrom);
      if (idx === -1) idx = searchFrom;
      result.push({ text: sentences[k], start: idx, end: idx + sentences[k].length });
      searchFrom = idx + sentences[k].length;
    }

    // ── Post-processing ────────────────────────────────────────────────────
    // Bible (explicit or auto-detected): strip leading verse markers from
    // every sentence's TTS text, and drop sentences that became ONLY a
    // number (e.g. parser produced "1." as its own sentence). Display text
    // is unchanged — only the audio skips the numbers.
    if (isBible) {
      result = result.map(function(s) {
        var orig = s.text;
        // First strip the leading verse marker if any; capture how many chars came off so
        // we can shift sentence.start to point at the new first word rather than at the
        // (no-longer-spoken) verse number — keeps word-click and highlight positions aligned.
        var stripped = orig.replace(/^\s*\d+(?::\d+)?[.:]?\s+/, "");
        var shift = orig.length - stripped.length;
        // Then drop sentences that are JUST a number (e.g. "1.") — they'd be empty after.
        stripped = stripped.replace(/^\s*\d+(?::\d+)?[.:]?\s*$/, "").trim();
        return Object.assign({}, s, { text: stripped, start: s.start + shift });
      }).filter(function(s) { return s.text.length > 0; });
    }

    // Chapter announcement: prepend a synthetic "Глава [ordinal]." sentence at
    // the start of every chapter's first page. If the original first sentence
    // already announces the chapter ("Глава 5" / "Часть 3"), drop it first so
    // the announcement isn't duplicated. Synthetic sentence has start/end = -1
    // so position-based word-click mapping ignores it.
    if (opts.isFirstPage && opts.chapterNumber > 0) {
      if (result.length > 0 && /^\s*(глава|часть)\s+(\d+|[ivxlcdm]+\b)/i.test(result[0].text)) {
        result.shift();
      }
      var announce = "Глава " + ruOrdinalFeminine(opts.chapterNumber) + ".";
      result.unshift({ text: announce, start: -1, end: -1 });
    }

    return result;
  };

  // Find which sentence index contains the given character position (page-relative).
  // Returns -1 if not found.
  var findSentenceIdxForPageOffset = function(pageOffset) {
    var sents = audioSentencesRef.current;
    for (var i = 0; i < sents.length; i++) {
      if (pageOffset >= sents[i].start && pageOffset < sents[i].end) return i;
    }
    // Fallback: find closest sentence whose start is <= pageOffset
    var best = -1;
    for (var j = 0; j < sents.length; j++) {
      if (sents[j].start <= pageOffset) best = j;
    }
    return best;
  };

  // NOTE: prefetchSentence (Azure /api/tts blob fetcher) was removed — it was
  // already dead code, unused since playAudioSentence switched to native
  // browser speechSynthesis. audioCacheRef is kept (harmlessly reset
  // elsewhere) in case a future feature wants a blob cache again.

  // ── Sentence-highlight helpers ─────────────────────────────────────────────
  // Apply the .rw-reading class to every word in the playing sentence's range.
  // If an override is passed (clicked a word mid-sentence), highlight only
  // from that word onward to match what's actually being read aloud.
  var clearSentenceHighlight = function() {
    highlightedElementsRef.current.forEach(function(el) {
      try { el.classList.remove("rw-reading"); } catch(e) {}
    });
    highlightedElementsRef.current = [];
  };

  // Start audiobook playback. Reuses a single Audio element so user-activation
  // sticks across pause/resume cycles, just like the TTS path.
  var playAudiobookFromSentence = function(startIdx) {
    var data = audiobookDataRef.current;
    if (!data || !data.audio_url) return false;

    // Kill any TTS playback in flight; the two modes share the audio bar UI
    // but not the actual element.
    if (audioElemRef.current) {
      try {
        audioElemRef.current.pause();
        audioElemRef.current.onplay = audioElemRef.current.onended = audioElemRef.current.onerror = null;
      } catch(e) {}
    }
    clearSentenceHighlight();

    var audio = audiobookAudioRef.current;
    if (!audio) {
      audio = new Audio();
      audio.preload = "auto";
      // No crossOrigin. Setting it turns every load into a CORS request, and
      // nothing here needs one: the app never reads the audio's samples (no
      // AudioContext, no createMediaElementSource, no canvas capture), it just
      // plays the file. The attribute was harmless while every recording came
      // from a host that sends Access-Control-Allow-Origin — archive.org and
      // the public r2.dev domain both do — but a presigned URL on R2's S3
      // endpoint does not, so a gated book failed with ERR_FAILED before a
      // byte was fetched. Plain media loads have never needed CORS.
      audiobookAudioRef.current = audio;
      // Drive the on-screen time counter / scrubber.
      audio.addEventListener("timeupdate", function(){ setAbCur(audio.currentTime || 0); });
      audio.addEventListener("seeked", function(){ setAbCur(audio.currentTime || 0); });
      audio.addEventListener("durationchange", function(){ setAbDur(isFinite(audio.duration) ? audio.duration : 0); });
      audio.addEventListener("loadedmetadata", function(){ setAbDur(isFinite(audio.duration) ? audio.duration : 0); setAbCur(audio.currentTime || 0); });
    }

    // (Re)point at the chapter's audio URL if needed (chapter change). Changing
    // src resets the element to readyState 0, so any currentTime we set now is
    // discarded once the new media loads — we must defer the seek (below) until
    // metadata is available, or playback starts from 0 (the spoken preamble).
    var srcChanged = false;
    if (audio.src !== data.audio_url) {
      audio.src = data.audio_url;
      srcChanged = true;
    }

    // Every chapter now has its own file, so playback starts at the top of it.
    // The one exception worth keeping: where a recording opens with a spoken
    // preamble and we happen to know when the text actually starts, skip to it.
    var seekTo = 0;
    if (data.word_timings && data.word_timings.length) {
      seekTo = data.word_timings[0].begin;
    }
    // Apply the seek now AND once the media is ready — a fresh src won't accept
    // currentTime until it has loaded metadata, so the deferred one is what
    // actually lands the playhead on the first spoken word of the text.
    var doSeek = function() { try { audio.currentTime = seekTo; } catch(e) {} };
    if (srcChanged || audio.readyState < 1) {
      var onMeta = function() { audio.removeEventListener("loadedmetadata", onMeta); doSeek(); };
      audio.addEventListener("loadedmetadata", onMeta);
    }
    doSeek();

    audio.onended = function() {
      setAudioPlaying(false); audioPlayingRef.current = false;
    };
    audio.onerror = function() {
      clearSentenceHighlight();
      setAudioPlaying(false); audioPlayingRef.current = false;
      setTtsErr("Audiobook stream error — the audio URL may be unreachable.");
    };

    setAudioPlaying(true); audioPlayingRef.current = true;
    var p = audio.play();
    if (p && typeof p.catch === "function") {
      p.catch(function(e) {
        clearSentenceHighlight();
        setAudioPlaying(false); audioPlayingRef.current = false;
        var msg = e && e.message ? e.message : String(e);
        setTtsErr("Audiobook blocked: " + msg);
      });
    }
    return true;
  };

  var pauseAudiobook = function() {
    if (audiobookAudioRef.current) {
      try { audiobookAudioRef.current.pause(); } catch(e) {}
    }
    setAudioPlaying(false); audioPlayingRef.current = false;
  };

  var stopAudiobookTotal = function() {
    pauseAudiobook();
    clearSentenceHighlight();
    if (audiobookAudioRef.current) {
      try {
        audiobookAudioRef.current.onplay = null;
        audiobookAudioRef.current.onpause = null;
        audiobookAudioRef.current.onended = null;
        audiobookAudioRef.current.onerror = null;
        audiobookAudioRef.current.src = "";
      } catch(e) {}
      audiobookAudioRef.current = null;
    }
  };

  var resetAudioBar = function() {
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch(e) {}
    if (audioElemRef.current) {
      try { audioElemRef.current.pause(); audioElemRef.current.src = ""; } catch(e) {}
      audioElemRef.current = null;
    }
    stopAudiobookTotal();
    clearSentenceHighlight();
    setAudioPlaying(false); audioPlayingRef.current = false;
  };

  // Play the sentence at `idx`. Kicks off prefetch for `idx+1` in parallel so
  // the next sentence is already in memory when this one ends.
  //
  // IMPORTANT: we REUSE a single Audio element across sentences instead of
  // creating a new one each time. Chrome's autoplay policy keeps user-gesture
  // authorization attached to a specific element — so the .play() call on a
  // freshly-created element from inside an onended handler gets blocked
  // because the original ▶ click was on a *different* element. Reusing the
  // same element preserves the trust chain. We only null the element out on
  // a true teardown (page change, resetAudioBar).
  // Pick the best available native Russian voice: the user's saved pick (if a
  // real local voice), else Katya, else any ru-* voice, else null (system default).
  var pickRussianVoice = function() {
    try {
      var cur = voiceRef.current;
      if (cur && !cur._cloud && cur.lang) return cur;
      var vs = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
      var ru = vs.filter(function(v){ return v.lang && v.lang.toLowerCase().indexOf("ru")===0; });
      if (!ru.length) return null;
      // Prefer Katya, then any LOCAL voice (localService=true, e.g. Microsoft
      // Irina/Pavel — reliable), then anything. Google's network voice is
      // last resort: it throws spurious errors and needs connectivity.
      var katya = ru.filter(function(v){ return /katya/i.test(v.name); })[0];
      if (katya) return katya;
      var local = ru.filter(function(v){ return v.localService; })[0];
      return local || ru[0];
    } catch(e){ return null; }
  };

  var playAudioSentence = function(idx) {
    var sentences = audioSentencesRef.current;
    if (idx < 0 || idx >= sentences.length) {
      setAudioPlaying(false); audioPlayingRef.current = false;
      setAudioFetching(false);
      return;
    }
    audioGenRef.current++;
    var myGen = audioGenRef.current;

    // Detach old handlers on the existing element BEFORE touching its state,
    // so any 'pause' / 'emptied' / 'error' events fired by src changes don't
    // accidentally invoke a previous-sentence callback.
    if (audioElemRef.current) {
      audioElemRef.current.onplay = null;
      audioElemRef.current.onended = null;
      audioElemRef.current.onerror = null;
      try { audioElemRef.current.pause(); } catch(e) {}
    }
    // Tear down the previous sentence's highlight before drawing the new one.
    clearSentenceHighlight();

    // Consume the one-shot override if set. Subsequent playback of this same
    // sentence will use the full sentence text (override is gone after this).
    var override = sentenceOverrideRef.current;  // either {text, wordOffsetInSentence} or null
    if (override) sentenceOverrideRef.current = null;

    // ---- NATIVE TTS (browser speechSynthesis). Azure cloud TTS removed. ----
    if (!TTS_ENABLED) { setAudioPlaying(false); audioPlayingRef.current = false; return; }
    var sentObj = audioSentencesRef.current[idx];
    var sentText = sentObj && sentObj.text;
    if (!sentText) { setAudioPlaying(false); audioPlayingRef.current = false; return; }
    var speakText = (override && typeof override.text === "string" && override.text) ? override.text : sentText;
    if (!window.speechSynthesis) {
      setTtsErr("This browser has no speech synthesis. Try Chrome or Edge.");
      setAudioPlaying(false); audioPlayingRef.current = false; return;
    }
    setAudioFetching(false);
    // Only cancel if something is actually queued/speaking — a bare cancel()
    // right before speak() makes Chrome drop the new utterance.
    try { if (window.speechSynthesis.speaking || window.speechSynthesis.pending) window.speechSynthesis.cancel(); } catch(e) {}
    var u = new SpeechSynthesisUtterance(speakText);
    u.lang = "ru-RU";
    var pct = (typeof audioSpeedRef !== "undefined" && audioSpeedRef.current) ? audioSpeedRef.current : 0;
    var rate = 1 + (pct/100); if (rate<0.5) rate=0.5; if (rate>1.5) rate=1.5;
    u.rate = rate;
    var rv = pickRussianVoice(); if (rv) u.voice = rv;
    u.onstart = function(){ /* read-along tint removed */ };
    u.onend = function(){
      if (audioGenRef.current!==myGen) return;
      clearSentenceHighlight();
      if (audioPlayingRef.current && audioGenRef.current===myGen) {
        var nextIdx = audioIdxRef.current + 1;
        if (nextIdx < audioSentencesRef.current.length) { setAudioIdx(nextIdx); audioIdxRef.current=nextIdx; playAudioSentence(nextIdx); }
        else { setAudioPlaying(false); audioPlayingRef.current=false; }
      }
    };
    u.onerror = function(ev){
      if (audioGenRef.current!==myGen) return;
      // Chrome fires 'interrupted'/'canceled' on normal cancel()/page change —
      // those are benign, not real failures. Ignore them.
      var reason = ev && ev.error ? ev.error : "";
      if (reason === "interrupted" || reason === "canceled") return;
      clearSentenceHighlight();
      setAudioPlaying(false); audioPlayingRef.current=false;
      setTtsErr("Speech error (" + (reason||"unknown") + "). Try Edge if it persists.");
    };
    try { window.speechSynthesis.speak(u); }
    catch(e){ clearSentenceHighlight(); setAudioPlaying(false); audioPlayingRef.current=false; setTtsErr("Speech error: "+(e.message||e)); }
  };

  var audioPlayPause = function() {
    if (audioSentencesRef.current.length === 0) return;
    // Audiobook branch — single streaming element, no per-sentence fetch chain.
    if (audiobookModeRef.current && audiobookDataRef.current) {
      if (audioPlaying) {
        pauseAudiobook();
      } else {
        // If the audio element exists and is just paused mid-stream, resume.
        // Otherwise start fresh from the current sentence's begin time.
        var existing = audiobookAudioRef.current;
        if (existing && existing.src && existing.paused && existing.currentTime > 0) {
          setAudioPlaying(true); audioPlayingRef.current = true;
          existing.play().catch(function(){});
        } else {
          // Fresh playback always starts from the top of the current page,
          // not from a stale audioIdx that may belong to a different page.
          playAudiobookFromSentence(0);
        }
      }
      return;
    }
    // TTS branch (existing behaviour).
    if (audioPlaying) {
      try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch(e) {}
      if (audioElemRef.current) audioElemRef.current.pause();
      setAudioPlaying(false); audioPlayingRef.current = false;
    } else {
      setAudioPlaying(true); audioPlayingRef.current = true;
      if (audioElemRef.current && audioElemRef.current.src && audioElemRef.current.paused && audioElemRef.current.currentTime > 0) {
        var p = audioElemRef.current.play();
        if (p && typeof p.catch === "function") p.catch(function(){});
      } else {
        playAudioSentence(audioIdxRef.current);
      }
    }
  };
  var [playing, setPlaying]     = useState(false);
  var [showVP, setShowVP]       = useState(false);
  var [spkIdx, setSpkIdx]       = useState(null);
  var [ttsErr, setTtsErr]       = useState("");
  var [diagLogs, setDiagLogs]   = useState([]);
  var [spokenChar, setSpokenChar] = useState(-1);
  var charPos  = useRef(0);
  var paraText = useRef("");
  var keepAlive = useRef(null);
  // Queue of remaining TTS chunks (used by playText to chain Google-voice-friendly
  // short utterances). Each entry is {text, start}. Cleared by stopTTS/pauseTTS.
  var ttsQueue = useRef([]);
    var inputRef = useRef(null);
  var msgsRef = useRef(null);

  var isLit = mode === "read";

  // Auto-save reading progress whenever the user moves to a new page or chapter.
  // Skipped when no book is loaded, when title is missing (transient state), or
  // when we're at chapter 0 / page 0 with no story actually started.
  useEffect(function() {
    if (!started || !isLit) return;
    if (!bookMeta || !bookMeta.title) return;
    if (!chapters || chapters.length === 0) return;
    saveBookProgress(bookMeta, cidx, pidx, chapters.length);
  }, [cidx, pidx, started, isLit, bookMeta.title, chapters.length]);
  var pct  = chapters.length > 0 ? Math.round((cidx / chapters.length) * 100) : 0;
  var curChapter = (function(){
    var ch = chapters[cidx] || { heading: "", text: "" };
    // The chapter text ALWAYS comes from the book. Chapter JSONs built by
    // an earlier Whisper-transcription pass carry `transcript: true`, and
    // this used to render their fragment texts as the chapter instead of
    // the FB2 -- which showed the reader whatever the recording happened to
    // say: the narrator's spoken title card glued into sentence one
    // ("Фёдор Михайлович Достоевский Идиот Роман в четырёх частях Часть
    // первая В конце ноября..."), the transcriber's mishearings, and no
    // paragraph breaks at all, since fragments concatenate into one block.
    // The flag is now ignored: every book renders its own text, and the
    // alignment JSON supplies timings and nothing else. (The radio
    // spectacles lost nothing by this -- their FB2s are already proper play
    // scripts, with speaker names and stage directions the transcript
    // rendering had to reconstruct.)

    // Bible: split on verse numbers so each verse is its own paragraph
    if (bookMeta && bookMeta.filename && bookMeta.filename.indexOf("Библии") !== -1) {
      var bibleText = (ch.text || "")
        // Insert double newline before verse numbers (digit(s) at word boundary)
        .replace(/\s+(\d+)\s+(?=[А-ЯЁA-Z«"])/g, function(m, num) {
          return "\n\n" + num + " ";
        });
      return Object.assign({}, ch, { text: bibleText });
    }
    return ch;
  })();
  // Paginate the current chapter. Single-page mode (whole-chapter-as-one-page)
  // applies to any book in the "Song Lyrics" category, so users see a full song
  // per screen and use chapter-nav arrows to advance. The legacy
  // `splitByNumberedSections` flag also enables this for backward compatibility
  // with books that were configured before the category-based rule existed.
  var singlePageMode = bookMeta.category === "Song Lyrics" || !!bookMeta.splitByNumberedSections;
  // Always one page: a chapter is displayed in its entirety and the reader
  // scrolls. Pagination was only ever there to give the highlighter a bounded
  // region to paint.
  var pages = useMemo(function() {
    return computePages(curChapter.text || "", { singlePage: true });
  }, [curChapter.text, singlePageMode]);
  var totalPages = pages.length;
  var lastCidxRef = useRef(-1);
  var currentPage = pages[Math.min(pidx, totalPages - 1)] || pages[0];
  // Keep the page ref in lockstep with the rendered page,
  // so the audiobook RAF loop highlights the right page after a flip.
  useEffect(function() { currentPageRef.current = currentPage; }, [currentPage]);

  // Re-parse sentences when page or chapter changes. Halts any in-flight audio,
  // wipes the prefetch cache, and bumps the generation counter so any pending
  // fetches from the previous page abort instead of playing on the new page.
  useEffect(function() {
    var chapterChanged = lastCidxRef.current !== cidx;
    lastCidxRef.current = cidx;
    // TTS per-sentence-fetch state is always cleaned: stale fetches must not
    // play on a different page.
    if (audioElemRef.current) {
      try { audioElemRef.current.pause(); audioElemRef.current.src = ""; } catch(e) {}
      audioElemRef.current = null;
    }
    audioCacheRef.current = {};
    audioGenRef.current++;
    sentenceOverrideRef.current = null;
    setAudioFetching(false);
    // A chapter is one page, so this only ever fires on a real chapter change:
    // stop the previous chapter's recording rather than letting it run under
    // the new text.
    if (chapterChanged || !audiobookModeRef.current) {
      if (audiobookAudioRef.current) {
        try { audiobookAudioRef.current.pause(); } catch(e) {}
      }
      clearSentenceHighlight();
      setAudioPlaying(false); audioPlayingRef.current = false;
      setAudioIdx(0); audioIdxRef.current = 0;
    }
    if (mode === "read" && currentPage && curChapter && curChapter.text) {
      var pageText = curChapter.text.slice(currentPage.startChar, currentPage.endChar);
      var parsed = parseSentences(pageText, {
        isFirstPage: pidx === 0,
        chapterNumber: cidx + 1,
        isBible: isBibleBook(bookMeta),
      });
      setAudioSentences(parsed);
      // Vocab source-link: if we jumped here to show a saved word, highlight the
      // sentence that contains it and scroll it into view. Offset is chapter-
      // relative; convert to page-relative. Runs once, then clears the ref.
      if (srcJumpOffsetRef.current != null) {
        var wantOffset = srcJumpOffsetRef.current;
        var pageRel = wantOffset - currentPage.startChar;
        if (pageRel >= 0 && pageRel <= pageText.length) {
          srcJumpOffsetRef.current = null;
          audioSentencesRef.current = parsed;
          // Retry a few times: other effects (audiobook loader, page-change
          // handlers) call clearSentenceHighlight() right after a jump, so a
          // single timed highlight gets wiped. Re-assert it over ~2s and stop
          // once it sticks (the word nodes are present and stay highlighted).
          var attempts = 0;
          var applyHL = function(){
            attempts++;
            try {
              var sIdx = findSentenceIdxForPageOffset(pageRel);
              if (sIdx >= 0) {
                var sent = (audioSentencesRef.current || parsed)[sIdx];
                if (sent) {
                  // Highlight directly by the sentence's page-relative range,
                  // matched against data-rw-start (which are page-relative here
                  // because startChar offsetting already happened upstream).
                  // Painted directly rather than via any shared helper.
                  clearSentenceHighlight();
                  var cs = currentPage.startChar || 0;
                  var lo = cs + sent.start, hi = cs + sent.end;
                  var nodes = document.querySelectorAll(".lit-body [data-rw-start]");
                  var hits = [];
                  for (var ni = 0; ni < nodes.length; ni++) {
                    var pp = parseInt(nodes[ni].dataset.rwStart, 10);
                    if (!isNaN(pp) && pp >= lo && pp < hi) { nodes[ni].classList.add("rw-reading"); hits.push(nodes[ni]); }
                  }
                  highlightedElementsRef.current = hits;
                  if (hits.length && hits[0].scrollIntoView) hits[0].scrollIntoView({ behavior: "smooth", block: "center" });
                }
              }
            } catch(e) {}
            if (attempts < 2) setTimeout(applyHL, 400);
          };
          setTimeout(applyHL, 200);
        }
      }
    } else {
      setAudioSentences([]);
    }
  }, [cidx, pidx, mode, curChapter && curChapter.text, currentPage && currentPage.startChar, currentPage && currentPage.endChar, bookMeta.title]);

  // ── Audiobook alignment loader ─────────────────────────────────────────────
  // When the current book has an audiobook entry for the current chapter,
  // fetch its alignment JSON. The alignment carries the streaming audio URL
  // and per-sentence timestamps. If no audiobook is configured for this
  // chapter, audiobookData stays null and the UI falls back to TTS.
  useEffect(function() {
    setAudiobookData(null);
    var audiobook = bookMeta && bookMeta.audiobook;
    if (!audiobook) return;
    var url = chapterJsonUrl(audiobook, cidx);
    if (!url) return;
    var restricted = !!(bookMeta && bookMeta.restricted);
    var cancelled = false;
    fetch(url, { credentials: "same-origin" })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(json) {
        if (cancelled || !json) return;
        // Only audio_url is required. A plain chapter JSON with no fragments
        // is a complete, valid audiobook chapter now.
        if (!json.audio_url) return;
        var src = audioSrcFor(json, restricted);
        if (src !== json.audio_url) json = Object.assign({}, json, { audio_url: src });
        setAudiobookData(json);
        // Default to audiobook mode when one becomes available. User can
        // still flip to TTS via the toggle in the audio bar.
        setAudiobookMode(true);
      })
      .catch(function() {});
    return function() { cancelled = true; };
  }, [bookMeta && bookMeta.audiobook, cidx]);

  // Dual-language Bible: load the English (WEB) verses for the current chapter,
  // keyed by the same book-chapter as the audio so they line up 1:1 with the
  // displayed Russian verses. Non-Bible books clear it.
  useEffect(function() {
    setBibleEn(null);
    // Fire for any chapter whose audio is a bible-nrp file (avoids the shared
    // isBibleBook() detector, which misses this book's "Библии" title).
    var chs = bookMeta && bookMeta.audiobook && bookMeta.audiobook.chapters;
    var key = chs && chs[cidx] && (String(chs[cidx]).match(/bible-nrp\/(\d+-\d+)\.json/) || [])[1];
    if (!key) return;
    var cancelled = false;
    fetch("/books/bible-en/" + key + ".json")
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(j) { if (!cancelled && j) setBibleEn(j); })
      .catch(function() {});
    return function() { cancelled = true; };
  }, [bookMeta && bookMeta.filename, cidx]);

  // Dual-language prose (Москва–Петушки): the catalogue entry names a folder
  // in parallelEn; each chapter file maps paragraph index → English paragraph.
  // Built offline from the printed translation, aligned per paragraph; gaps
  // (OCR losses) simply show no English line. Display-only, like the Bible.
  useEffect(function() {
    setProseEn(null);
    var dir = bookMeta && bookMeta.parallelEn;
    if (!dir) return;
    var cancelled = false;
    var nn = String(cidx + 1); if (nn.length < 2) nn = "0" + nn;
    fetch("/books/" + dir + "/" + nn + ".json")
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(j) { if (!cancelled && j) setProseEn(j); })
      .catch(function() {});
    return function() { cancelled = true; };
  }, [bookMeta && bookMeta.parallelEn, cidx]);

  // Load the Bible section-heading translations once (same map for every
  // chapter). Fetched the first time a Bible chapter is opened, then reused.
  useEffect(function() {
    if (bibleHeadings) return;
    var chs = bookMeta && bookMeta.audiobook && bookMeta.audiobook.chapters;
    var key = chs && chs[cidx] && (String(chs[cidx]).match(/bible-nrp\/(\d+-\d+)\.json/) || [])[1];
    if (!key) return;
    var cancelled = false;
    fetch("/books/bible-headings-en.json")
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(j) { if (!cancelled && j) setBibleHeadings(j); })
      .catch(function() {});
    return function() { cancelled = true; };
  }, [bookMeta && bookMeta.filename, cidx, bibleHeadings]);

  // Exercises: load the drill set for the current chapter (if one exists),
  // keyed by the same book-chapter as the audio (e.g. "01-01" = Genesis 1).
  // Resets the exercise view whenever the chapter changes.
  useEffect(function() {
    setExData(null); setExCat("menu"); setExSelected(null); setExIdx(0); setExScore(0);
    stopExClip();
    // Exercises are keyed to the READING chapter (from the FB2), not the audio —
    // audio is only for listening. PREFERRED key: "<bookslug>__ch<cidx>" derived
    // from the book file + reading-chapter index. FALLBACK (older sets): the
    // audio-path key (Bible "NN-NN", else folder__basename).
    var fn = (bookMeta && bookMeta.filename) || "";
    var slug = fn.split("/").pop().replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_-]/g, "_");
    var rkey = slug ? (slug + "__ch" + cidx) : "";
    var chs = bookMeta && bookMeta.audiobook && bookMeta.audiobook.chapters;
    var cp = chs && chs[cidx] ? String(chs[cidx]) : "";
    var akey = "";
    var bm = cp.match(/bible-nrp\/(\d+-\d+)\.json/);
    if (bm) { akey = bm[1]; }
    else if (cp) {
      var s = cp.split("?")[0];
      if (s.indexOf("audio/") !== -1) s = s.split("audio/").pop();
      akey = s.replace(/\.json$/, "").replace(/\//g, "__");
    }
    var keys = [];
    if (rkey) keys.push(rkey);
    if (akey && akey !== rkey) keys.push(akey);
    if (!keys.length) return;
    var cancelled = false;
    var tryLoad = function(i) {
      if (cancelled || i >= keys.length) return;
      fetch("/books/exercises/" + keys[i] + ".json")
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(j) {
          if (cancelled) return;
          if (j) setExData(j); else tryLoad(i + 1);
        })
        .catch(function() { if (!cancelled) tryLoad(i + 1); });
    };
    tryLoad(0);
    return function() { cancelled = true; };
  }, [bookMeta && bookMeta.filename, cidx]);

  // If the current chapter has no exercises but the Exercises tab is somehow
  // still selected (e.g. after navigating), fall back to the reading view.
  useEffect(function() {
    if (lview === "exercises" && !(exData && (exData.cases || []).length)) setLview("read");
  }, [exData, lview]);

  // Start (or restart) the grammar case quiz: shuffle questions & options.
  var startCaseQuiz = function() {
    if (!exData || !exData.cases || !exData.cases.length) return;
    var exShuffle = function(arr) {
      var a = arr.slice();
      for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
      }
      return a;
    };
    var qs = exShuffle(exData.cases).map(function(q) {
      return Object.assign({}, q, { options: exShuffle(q.options || []) });
    });
    setExQuestions(qs); setExIdx(0); setExSelected(null); setExScore(0); setExCat("grammar");
  };

  // Start (or restart) the reading-comprehension quiz (English questions).
  // DISABLED 2026-08 — no UI path reaches this; kept so that re-enabling is a
  // one-line edit in the category menu above.
  var startReadingQuiz = function() {
    if (!exData || !exData.reading || !exData.reading.length) return;
    var exShuffle = function(arr) {
      var a = arr.slice();
      for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
      }
      return a;
    };
    var qs = exShuffle(exData.reading).map(function(q) {
      return Object.assign({}, q, { options: exShuffle(q.options || []) });
    });
    setExQuestions(qs); setExIdx(0); setExSelected(null); setExScore(0); setExCat("reading");
  };

  // ── Frequency Vocab Bank quiz logic ─────────────────────────────────────
  var wbShuffle = function(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  };

  // 3 distractor English glosses come from the whole-bank pool for this part
  // of speech (not just the current block), so even a small last block or a
  // rare pos (e.g. interjection) always has enough options.
  var wbBuildQuestion = function(card) {
    var pool = (wbDistractors && wbDistractors[card.pos]) || [];
    var correct = card.en.split(";")[0].trim();
    var others = pool.filter(function(g){ return g.toLowerCase() !== correct.toLowerCase(); });
    var distractors = wbShuffle(others).slice(0, 3);
    return { card: card, correct: correct, options: wbShuffle(distractors.concat([correct])) };
  };

  var wbPickNext = function(cards, progress, excludeId) {
    var remaining = (cards || []).filter(function(c){
      var st = progress[c.id];
      return !(st && st.mastered);
    });
    if (!remaining.length) return null;
    var pickFrom = remaining.length > 1 ? remaining.filter(function(c){ return c.id !== excludeId; }) : remaining;
    var pick = pickFrom[Math.floor(Math.random() * pickFrom.length)];
    return wbBuildQuestion(pick);
  };

  var wbBlockStats = function() {
    if (!wbCards) return { done: 0, total: 0 };
    var done = wbCards.filter(function(c){ var st = wbProgress[c.id]; return st && st.mastered; }).length;
    return { done: done, total: wbCards.length };
  };

  var wbStart = function() {
    if (!wbCards || !wbCards.length) return;
    setWbSel(null);
    setWbJustMastered(null);
    setWbCur(wbPickNext(wbCards, wbProgress, null));
    setWbScreen("quiz");
  };

  // A wrong answer resets the streak to 0; a card needs 10 CONSECUTIVE right
  // answers to be mastered and drop out of rotation (Dave's rule, confirmed).
  var wbAnswer = function(opt) {
    if (!wbCur || wbSel) return;
    setWbSel(opt);
    var card = wbCur.card;
    var right = opt === wbCur.correct;
    var st = wbProgress[card.id] || { streak: 0, mastered: false };
    var streak = right ? st.streak + 1 : 0;
    var mastered = streak >= 10;
    var newProgress = Object.assign({}, wbProgress);
    newProgress[card.id] = { streak: streak, mastered: mastered };
    setWbProgress(newProgress);
    if (mastered) setWbJustMastered(card.id);
    setTimeout(function() {
      setWbSel(null);
      setWbJustMastered(null);
      var next = wbPickNext(wbCards, newProgress, card.id);
      setWbCur(next);
      if (!next) setWbScreen("landing"); // block finished
    }, right ? 900 : 1600);
  };

  // "I already know this word" — instant mastery, skips the 10-in-a-row grind.
  var wbKnowIt = function() {
    if (!wbCur) return;
    var card = wbCur.card;
    var newProgress = Object.assign({}, wbProgress);
    newProgress[card.id] = { streak: 10, mastered: true };
    setWbProgress(newProgress);
    setWbSel(null);
    setWbJustMastered(null);
    var next = wbPickNext(wbCards, newProgress, card.id);
    setWbCur(next);
    if (!next) setWbScreen("landing");
  };

  var wbNextBlock = function() {
    if (!wbIndex) return;
    setWbBlockNum(function(n){ return Math.min(n + 1, wbIndex.blocks.length); });
    setWbCur(null); setWbSel(null); setWbScreen("landing");
  };

  var wbPrevBlock = function() {
    setWbBlockNum(function(n){ return Math.max(1, n - 1); });
    setWbCur(null); setWbSel(null); setWbScreen("landing");
  };

          // Normalise a word for matching book text against a recording's word_timings.
  // The only surviving consumer is the exercise-clip finder below.
  var normWordForAlign = function(s) {
    return String(s || "").toLowerCase().replace(/ё/g, "е").replace(/[^а-яa-z0-9]/g, "");
  };

  // ── Exercise audio clips ───────────────────────────────────────────────────
  // Locate a question's sentence inside the current chapter's recording (via the
  // word_timings) and play just that snippet, so the learner hears the exact
  // line the question is about — no synthesis, the real narrator.
  var exClipWords = useMemo(function() {
    var wt = audiobookData && audiobookData.word_timings;
    if (!wt || !wt.length || !audiobookData.audio_url) return null;
    return { wt: wt, norm: wt.map(function(w){ return normWordForAlign(w.word); }), url: audiobookData.audio_url };
  }, [audiobookData]);
  var exFindClip = function(sentence) {
    if (!exClipWords) return null;
    var target = String(sentence || "").replace(/\*\*/g, " ").split(/\s+/).map(normWordForAlign).filter(Boolean);
    if (target.length < 2) return null;
    var norm = exClipWords.norm, wt = exClipWords.wt;
    var head = target.slice(0, Math.min(6, target.length));
    var best = { score: -1, idx: -1 };
    for (var i = 0; i < norm.length; i++) {
      var k = 0, j = i, lim = Math.min(norm.length, i + head.length + 6);
      while (j < lim && k < head.length) { if (norm[j] === head[k]) k++; j++; }
      if (k > best.score) { best = { score: k, idx: i }; if (k === head.length) break; }
    }
    if (best.idx < 0 || best.score < Math.min(3, head.length)) return null;
    var start = best.idx;
    var endIdx = Math.min(wt.length - 1, start + target.length - 1);
    return { url: exClipWords.url, b: wt[start].begin, e: wt[endIdx].end };
  };
  var stopExClip = function() {
    if (exClipRafRef.current) { cancelAnimationFrame(exClipRafRef.current); exClipRafRef.current = null; }
    var a = exClipAudioRef.current;
    if (a) { try { a.pause(); } catch(e) {} }
    setExPlaying(null);
  };
  var playExClip = function(id, sentence) {
    if (exPlaying === id) { stopExClip(); return; }
    var clip = exFindClip(sentence);
    if (!clip) return;
    // Don't fight the main audiobook player.
    try { if (audiobookAudioRef.current) audiobookAudioRef.current.pause(); } catch(e) {}
    if (exClipRafRef.current) { cancelAnimationFrame(exClipRafRef.current); exClipRafRef.current = null; }
    var a = exClipAudioRef.current;
    if (!a) { a = new Audio(); a.preload = "auto"; exClipAudioRef.current = a; }
    var run = function() {
      try { a.currentTime = clip.b; } catch(e) {}
      var p = a.play();
      if (p && p.then) p.catch(function(){ setExPlaying(null); });
      setExPlaying(id);
      var tick = function() {
        var au = exClipAudioRef.current;
        if (!au || au.paused) { setExPlaying(null); return; }
        if (au.currentTime >= clip.e) { try { au.pause(); } catch(e) {} setExPlaying(null); return; }
        exClipRafRef.current = requestAnimationFrame(tick);
      };
      exClipRafRef.current = requestAnimationFrame(tick);
    };
    a.onended = function() { setExPlaying(null); };
    if (a.src !== clip.url) {
      a.src = clip.url;
      var onMeta = function() { a.removeEventListener("loadedmetadata", onMeta); run(); };
      a.addEventListener("loadedmetadata", onMeta);
      try { a.load(); } catch(e) {}
    } else if (a.readyState < 1) {
      var onMeta2 = function() { a.removeEventListener("loadedmetadata", onMeta2); run(); };
      a.addEventListener("loadedmetadata", onMeta2);
    } else {
      run();
    }
  };
  // A small round speaker button; renders only when the current chapter's audio
  // is loaded and the sentence can be located in it.
  var exClipBtn = function(id, sentence) {
    if (!exClipWords) return null;
    if (!exFindClip(sentence)) return null;   // only show when the line is findable in the recording
    var playing = exPlaying === id;
    return (
      <button onClick={function(e){ e.stopPropagation(); playExClip(id, sentence); }}
        title="Play this line from the recording"
        style={{background: playing ? "rgba(196,149,90,.25)" : "rgba(42,31,20,.06)", border:"1px solid rgba(42,31,20,.18)",
          color:"#2a1f14", width:30, height:30, minWidth:30, borderRadius:"50%", cursor:"pointer", fontSize:13,
          display:"inline-flex", alignItems:"center", justifyContent:"center", verticalAlign:"middle", flexShrink:0, padding:0, lineHeight:1}}>
        {playing ? "⏸" : "🔊"}
      </button>
    );
  };

  // When the loaded chapter changes, re-point the audio element at the new
  // chapter's file. Without this, switching chapters leaves the previous
  // chapter's audio playing under the new chapter's text and highlight.
  useEffect(function() {
    var data = audiobookData;
    var audio = audiobookAudioRef.current;
    if (!data || !data.audio_url || !audio) return;
    var want = data.audio_url;
    try { want = new URL(data.audio_url, window.location.href).href; } catch(e) {}
    if (audio.src !== want) {
      var wasPlaying = audioPlayingRef.current;
      try { audio.pause(); } catch(e) {}
      audio.src = data.audio_url;
      try { audio.load(); } catch(e) {}
      if (wasPlaying) {
        var t = setTimeout(function(){ playAudiobookFromSentence(0); }, 150);
        return function(){ clearTimeout(t); };
      }
    }
  }, [audiobookData]);

  useEffect(function() {
    (async function() {
      try { var v = await storage.get("vocab"); var g = await storage.get("grammar"); var st = await storage.get("grammar-topics");
        if (v) setVocab(JSON.parse(v.value)); if (g) setTips(JSON.parse(g.value));
        if (st) setSavedTopics(JSON.parse(st.value));
      } catch(e) {}
    })();
  }, []);
  useEffect(function() { storage && storage.set("vocab", JSON.stringify(vocab)).catch(function(){}); }, [vocab]);
  useEffect(function() { storage && storage.set("grammar", JSON.stringify(tips)).catch(function(){}); }, [tips]);
  useEffect(function() { storage && storage.set("grammar-topics", JSON.stringify(savedTopics)).catch(function(){}); }, [savedTopics]);

  // ── Frequency Vocab Bank persistence ────────────────────────────────────
  // All four effects below no-op while WORDBANK_ENABLED is false: no stored
  // progress is read or written (so existing progress is preserved untouched
  // for whenever it comes back), and none of the /vocab/blocks JSON is
  // fetched.
  var wbLoadedRef = useRef(false);
  useEffect(function() {
    if (!WORDBANK_ENABLED) return;
    (async function() {
      try {
        var wp = await storage.get("wordbank-progress");
        if (wp) {
          var d = JSON.parse(wp.value);
          if (d.progress) setWbProgress(d.progress);
          if (d.block) setWbBlockNum(d.block);
        }
      } catch(e) {}
      wbLoadedRef.current = true;
    })();
  }, []);
  useEffect(function() {
    if (!WORDBANK_ENABLED) return;
    if (!wbLoadedRef.current) return; // don't stomp saved progress with the initial empty state
    storage && storage.set("wordbank-progress", JSON.stringify({ progress: wbProgress, block: wbBlockNum })).catch(function(){});
  }, [wbProgress, wbBlockNum]);
  useEffect(function() {
    if (!WORDBANK_ENABLED) return;
    fetch("/vocab/blocks/index.json")
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){ if (j) setWbIndex(j); })
      .catch(function(){});
    fetch("/vocab/blocks/distractors.json")
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){ if (j) setWbDistractors(j); })
      .catch(function(){});
  }, []);
  useEffect(function() {
    if (!WORDBANK_ENABLED) return;
    if (!wbIndex) return;
    var meta = wbIndex.blocks[wbBlockNum - 1];
    if (!meta) { setWbCards([]); return; }
    var cancelled = false;
    setWbLoading(true);
    fetch("/vocab/blocks/" + meta.file)
      .then(function(r){ return r.ok ? r.json() : []; })
      .then(function(j){ if (!cancelled) { setWbCards(j); setWbLoading(false); } })
      .catch(function(){ if (!cancelled) { setWbCards([]); setWbLoading(false); } });
    return function(){ cancelled = true; };
  }, [wbIndex, wbBlockNum]);

  // ── speechSynthesis warmup ─────────────────────────────────────────────────
  // Chrome (and sometimes Edge) silently drops the FIRST speak() call after a
  // fresh page load — symptom is "click ▶ → silence → click ⏹ → click ▶ → it
  // works". The fix has two parts:
  //   1. cancel() on mount — clears any stuck state inherited from a previous
  //      page load (some engines persist this across reloads).
  //   2. A one-shot global click/touch listener — the moment the user FIRST
  //      interacts anywhere on the page (the book picker, a menu, anywhere),
  //      we issue a silent priming utterance. This gives Chrome the
  //      user-gesture-bound speak() it needs to fully wake up the audio engine,
  //      well before the user reaches the reading view and clicks ▶.
  useEffect(function() {
    if (!TTS_ENABLED) return;
    if (!window.speechSynthesis) return;
    try { window.speechSynthesis.cancel(); } catch(e) {}
    var warmedUp = false;
    var warmup = function() {
      if (warmedUp) return;
      warmedUp = true;
      try {
        var u = new SpeechSynthesisUtterance(" ");
        u.volume = 0.01;  // some engines skip volume=0 entirely
        u.rate = 10;       // play through as fast as possible
        window.speechSynthesis.speak(u);
      } catch(e) {}
    };
    document.addEventListener("click", warmup, { once: true });
    document.addEventListener("touchstart", warmup, { once: true });
    document.addEventListener("keydown", warmup, { once: true });
    return function() {
      document.removeEventListener("click", warmup);
      document.removeEventListener("touchstart", warmup);
      document.removeEventListener("keydown", warmup);
    };
  }, []);

  // Snap the reading view back to the top whenever the page or chapter changes.
  // We defer to the next animation frame so the new paragraphs have laid out, then
  // scroll BOTH the .lit-left container (desktop scroll) and the window/body
  // (mobile, where the document itself can be the scrolling element).
  useEffect(function() {
    requestAnimationFrame(function() {
      var el = document.querySelector(".lit-left");
      if (el) el.scrollTop = 0;
      if (typeof window !== "undefined" && window.scrollTo) window.scrollTo(0, 0);
      if (document.documentElement) document.documentElement.scrollTop = 0;
      if (document.body) document.body.scrollTop = 0;
    });
  }, [pidx, cidx]);

  // Auto-advance the page when TTS reads past the end of the visible page.
  // The reader stays in sync with the spoken word so you don't have to flip pages by hand.
  useEffect(function() {
    if (!playing || spokenChar < 0) return;
    if (pidx >= totalPages - 1) return;
    if (!currentPage) return;
    if (spokenChar > currentPage.endChar) {
      // Auto-advance during continuous TTS — just flip the page silently.
      // Comprehension questions are no longer auto-generated; user clicks the
      // "Test your comprehension" button when they're ready.
      setPidx(pidx + 1);
    }
  }, [spokenChar, pidx, playing]);

  // ── CROSS-DEVICE SYNC via /api/user-data (R2) ─────────────────────────────
  // On sign-in, fetch the server copy. If server has data, replace local state.
  // If server is empty but local has data, upload local as initial state.
  // After this initial sync, debounce any further changes and POST them.
  var [syncedFromServer, setSyncedFromServer] = useState(false);
  var [syncErr, setSyncErr] = useState("");  // Shown as a banner when sync fails

  useEffect(function() {
    // Only sync for signed-in users. Signed out, vocabulary still saves —
    // it just stays in this browser.
    if (!me || syncedFromServer) return;
    (async function() {
      try {
        var r = await authFetch("/api/user-data");
        if (!r.ok) return;
        var data = await r.json();
        var serverVocab = Array.isArray(data.vocab) ? data.vocab : [];
        // The server stores `created` but strips `id`. Use a stable per-entry
        // key (`_key`) derived from created (or backfilled) so single-item
        // removal targets exactly one word. Guaranteed unique even on collisions.
        var _seen = {};
        serverVocab = serverVocab.map(function(v, i){
          v = Object.assign({}, v);
          var k = (v.created != null ? String(v.created) : (v.id != null ? String(v.id) : "row"));
          k = k + "_" + i;            // index guarantees uniqueness
          v._key = k;
          return v;
        });
        var serverTips  = Array.isArray(data.tips)  ? data.tips  : [];

        if (serverVocab.length > 0 || serverTips.length > 0) {
          setVocab(serverVocab);
          setTips(serverTips);
        } else if (vocab.length > 0 || tips.length > 0) {
          await authFetch("/api/user-data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ vocab: vocab, tips: tips }),
          });
        }
        setSyncedFromServer(true);
      } catch(e) {}
    })();
  }, [me]);

  // After initial sync, push subsequent changes (debounced 1.5s).
  useEffect(function() {
    if (!me || !syncedFromServer) return;
    var t = setTimeout(async function() {
      try {
        // SAFETY: never let an empty vocab+tips state overwrite the server.
        // An empty client list almost always means "not loaded yet" or a bug,
        // not a real "user deleted everything" — refuse to POST it.
        if ((!vocab || vocab.length === 0) && (!tips || tips.length === 0)) return;
        var r = await authFetch("/api/user-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ vocab: vocab, tips: tips }),
        });
        if (r.status === 413) {
          // Payload rejected as too large. R2 has no size limit of its own, so
          // this now means the request body exceeded the function's own cap.
          setSyncErr("Vocabulary list too large to sync in one go.");
        } else if (r.ok) {
          // Save succeeded — clear any previous error (user removed entries to get under the limit).
          if (syncErr) setSyncErr("");
        }
      } catch(e) {}
    }, 1500);
    return function(){ clearTimeout(t); };
  }, [vocab, tips, me, syncedFromServer]);

  useEffect(function() {
    var h = function(e) {
      if (popRef.current && !popRef.current.contains(e.target)) setPopup(null);
    };
    document.addEventListener("mousedown", h);
    return function() { document.removeEventListener("mousedown", h); };
  }, []);

  // (Voice auto-selector removed — the useEffect that previously scanned
  // getVoices() and called setVoice was the source of bugs where
  // browser-native voices kept overriding the user's pick on Chrome PC.
  // Without it, `voice` starts null and pickRussianVoice() resolves a
  // sensible native default on demand.)

  // Launch screen always shows a fresh "no book loaded" state. We deliberately
  // do NOT auto-restore the previous book from EPUB_CACHE on mode entry —
  // surfacing a half-remembered "Resume at chapter X" state on every visit was
  // confusing. The cache is still written during loadFile (so the same file
  // could be restored manually later), it just isn't read back on entry.
  // Bookmark (cbm) restoration is also disabled because it has nothing to
  // bookmark against when chapters is empty.

  // But we DO load the multi-upload metadata list so the library view can show
  // the user's recent uploads alongside the preset books.
  useEffect(function() {
    if (mode !== "read") return;
    (async function() {
      try {
        var r = await storage.get(UPLOADS_LIST_KEY);
        if (r && r.value) {
          var list = JSON.parse(r.value);
          if (Array.isArray(list)) setUploadedBooks(list);
        }
      } catch(e) { console.log("Failed to load uploads list:", e); }
    })();
  }, [mode]);

  // Persist bookmark whenever it changes (only meaningful with a loaded book).
  useEffect(function() {
    if (chapters.length > 0) storage && storage.set(EPUB_BM, String(cbm)).catch(function(){});
  }, [cbm]);

  useEffect(function() {
    if (!lsearch.trim() || !chapters.length) { setLres([]); return; }
    var q = lsearch.toLowerCase();
    var r = [];
    for (var i = 0; i < chapters.length && r.length < 50; i++) {
      if (chapters[i].text.toLowerCase().includes(q) || chapters[i].heading.toLowerCase().includes(q)) r.push(i);
    }
    setLres(r);
  }, [lsearch, chapters]);

  // Auto-scroll the currently-spoken word into view, but only when it's near
  // the edge of the reading pane (avoids jittery scroll on every word).
  useEffect(function() {
    if (spokenChar < 0) return;
    var el = document.querySelector(".rwhl");
    if (!el) return;
    var container = el.closest(".lit-left");
    if (!container) return;
    var er = el.getBoundingClientRect();
    var cr = container.getBoundingClientRect();
    var margin = 80;
    if (er.top < cr.top + margin || er.bottom > cr.bottom - margin) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [spokenChar]);

  // Auto-scroll the chat / lit-msgs to bottom when a new message arrives
  // or the typing indicator appears/disappears, so the latest content stays visible.
  useEffect(function() {
    if (msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
    }
  }, [msgs.length, loading]);

    // Admin actions — list accounts. Only meaningful when isAdmin, and the
  // route re-checks the session regardless of what the UI decided to show.
  var loadAdminUsers = async function() {
    setAdminLoad(true); setAdminErr("");
    try {
      var r = await authFetch("/api/admin/users");
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to load users");
      setAdminUsers(d.users || []);
    } catch(e) {
      setAdminErr(e.message || "Failed to load users");
    } finally { setAdminLoad(false); }
  };

  // Approve or revoke one account. The server returns the refreshed list so the
  // modal never shows a stale row after the write.
  var setUserApproval = async function(email, approved) {
    setAdminLoad(true); setAdminErr("");
    try {
      var r = await authFetch("/api/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, approved: approved }),
      });
      var d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to update user");
      setAdminUsers(d.users || []);
    } catch(e) {
      setAdminErr(e.message || "Failed to update user");
    } finally { setAdminLoad(false); }
  };

  // Auto-load users when admin panel opens.
  useEffect(function() { if (showAdmin && isAdmin) loadAdminUsers(); }, [showAdmin, isAdmin]);

  // Upload a song to the library. Hits /api/admin/upload-song which commits
  // to GitHub → Vercel redeploys → song appears in picker after deploy.
  var uploadSong = async function() {
    if (upBusy) return;
    setUpErr("");
    setUpMsg("");
    var artist = upArtist.trim();
    var title  = upTitle.trim();
    var lyrics = upLyrics.trim();
    if (!artist) { setUpErr("Artist required"); return; }
    if (!title)  { setUpErr("Song title required"); return; }
    if (lyrics.length < 20) { setUpErr("Lyrics too short"); return; }
    setUpBusy(true);
    try {
      var r = await authFetch("/api/admin/upload-song", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artist: artist, title: title, lyrics: lyrics }),
      });
      var d = await r.json().catch(function(){ return {}; });
      if (!r.ok) throw new Error(d.error || ("HTTP " + r.status));
      setUpMsg(
        d.isNewArtist
          ? "✓ Created new artist file \"" + d.artist + "\" with song #1: \"" + title + "\". Vercel will redeploy in ~1-2 min."
          : "✓ Appended song #" + d.songNumber + " (\"" + title + "\") to existing artist \"" + d.artist + "\". Vercel will redeploy in ~1-2 min."
      );
      // Clear title + lyrics so the admin can immediately add another song
      // from the same artist; preserve artist for convenience.
      setUpTitle("");
      setUpLyrics("");
    } catch(err) {
      setUpErr(err.message || "Upload failed");
    } finally {
      setUpBusy(false);
    }
  };

  // Upload a full book (EPUB/FB2/TXT/HTML). Reads the file as base64, sends to
  // /api/admin/upload-book which commits to public/books/<category-folder>/ on
  // GitHub.
  var uploadBook = async function() {
    if (upBusy) return;
    setUpErr("");
    setUpMsg("");
    var title  = upTitle.trim();
    var author = upBookAuthor.trim();
    var cat    = upBookCategory;
    var file   = upBookFile;
    if (!file) { setUpErr("Pick a file first"); return; }
    if (!title) { setUpErr("Title required"); return; }
    if (!cat)   { setUpErr("Category required"); return; }
    // 20 MB cap matches the backend limit; warn earlier so we don't waste a round-trip.
    if (file.size > 20 * 1024 * 1024) { setUpErr("File too large (max 20MB)"); return; }
    setUpBusy(true);
    try {
      // Read the file as base64. Use FileReader since File.arrayBuffer + Buffer
      // isn't available in the browser; readAsDataURL gives us "data:...;base64,XXX".
      var fileBase64 = await new Promise(function(resolve, reject) {
        var fr = new FileReader();
        fr.onload  = function(){
          var s = String(fr.result || "");
          var idx = s.indexOf(",");
          resolve(idx >= 0 ? s.slice(idx + 1) : s);
        };
        fr.onerror = function(){ reject(new Error("Could not read file")); };
        fr.readAsDataURL(file);
      });
      var r = await authFetch("/api/admin/upload-book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename:   file.name,
          title:      title,
          author:     author,
          category:   cat,
          fileBase64: fileBase64,
        }),
      });
      var d = await r.json().catch(function(){ return {}; });
      if (!r.ok) throw new Error(d.error || ("HTTP " + r.status));
      setUpMsg(d.message || ("Book \"" + title + "\" uploaded — deploy in progress."));
      // Clear after success so admin can add another
      setUpBookFile(null);
      setUpTitle("");
      setUpBookAuthor("");
    } catch(err) {
      setUpErr(err.message || "Upload failed");
    } finally {
      setUpBusy(false);
    }
  };

  // Open the inline song-picker for a Song Lyrics artist. Reads song titles
  // from the book's `songs` array in index.json (populated by uploads). If
  // titles aren't pre-populated (e.g. older artist entries), fetch the .txt
  // and parse it to extract chapter headings.
  var openSongPicker = async function(book) {
    setSongPickerBook(book);
    setSongPickerErr("");
    setSongPickerList([]);
    // Fast path: pre-baked song titles in the manifest entry
    if (Array.isArray(book.songs) && book.songs.length > 0) {
      var titlesFromManifest = book.songs.map(function(s, i){
        var title = "";
        if (s && typeof s === "object" && typeof s.title === "string") title = s.title;
        return { title: title || ("Song " + (i + 1)), index: i };
      });
      if (titlesFromManifest.some(function(t){ return t.title && t.title.indexOf("Song ") !== 0; })) {
        setSongPickerList(titlesFromManifest);
        return;
      }
    }
    // Slow path: fetch + parse the file to extract titles
    setSongPickerLoad(true);
    try {
      var r = await fetch(bookFileUrl(book), { credentials: "same-origin" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      var buf = await r.arrayBuffer();
      var result = await parseBook(buf, book.filename);
      var chs = result.chapters || [];
      // Apply the same splitting logic loadFile uses (heuristic, then legacy
      // numbered fallback if explicitly opted in). Skip the AI fallback here —
      // costs a token and the picker doesn't need perfection.
      if (book.category === "Song Lyrics" || book.splitByNumberedSections) {
        // Same priority as loadFile: trust the explicit flag first, then heuristic.
        var didSplit = false;
        if (book.splitByNumberedSections) {
          var byNum = resplitByNumberedSections(chs);
          if (byNum && byNum.length >= 1) { chs = byNum; didSplit = true; }
        }
        if (!didSplit || chs.length <= 1) {
          var smart = splitSongsHeuristic(chs, { minSongs: 2 });
          if (smart && smart.length >= 2) chs = smart;
        }
      }
      setSongPickerList(chs.map(function(ch, i){
        return { title: (ch.heading || "").trim() || ("Song " + (i + 1)), index: i };
      }));
    } catch(err) {
      setSongPickerErr(err.message || "Could not load song list");
    } finally {
      setSongPickerLoad(false);
    }
  };

  // User picked a specific song from the inline picker — load the book then
  // jump to that song's chapter index.
  var jumpToSong = async function(songIndex) {
    var book = songPickerBook;
    if (!book) return;
    setSongPickerBook(null);
    setSongPickerList([]);
    await loadPresetBook(book);
    // loadFile resets cidx via setCbm(0) but cidx itself stays. Force the jump.
    setCidx(songIndex);
    setPidx(0);
  };

  var startKeepalive = function() {
    if (keepAlive.current) clearInterval(keepAlive.current);
    // Chrome cuts off speechSynthesis after ~15 seconds. Pause+resume keeps it alive.
    keepAlive.current = setInterval(function() {
      if (!window.speechSynthesis || !window.speechSynthesis.speaking) {
        if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
        return;
      }
      window.speechSynthesis.pause();
      window.speechSynthesis.resume();
    }, 10000);
  };

  var stopKeepalive = function() {
    if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
  };

  // For cloud TTS: the currently-playing <audio> element. We keep a ref so
  // stopTTS() can halt cloud playback, and so a second 🔊 Listen click on the
  // same message stops it (matches the speechSynthesis behavior).
  var cloudAudioRef = useRef(null);

  var stopTTS = useCallback(function() {
    stopKeepalive();
    ttsQueue.current = [];  // halt the chunk chain
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    // Halt cloud audio if any is playing.
    if (cloudAudioRef.current) {
      try { cloudAudioRef.current.pause(); cloudAudioRef.current.src = ""; } catch(e) {}
      cloudAudioRef.current = null;
    }
    setPlaying(false); setSpkIdx(null); setSpokenChar(-1);
  }, []);

  var checkTTSAvailable = function() {
    if (!TTS_ENABLED) { setTtsErr(""); return false; }
    if (!window.speechSynthesis) {
      setTtsErr("This browser does not support speechSynthesis.");
      return false;
    }
    var vs = window.speechSynthesis.getVoices();
    if (!vs.length) {
      setTtsErr("No voices available. Try clicking 🎙 Voice — if list is empty, your browser/OS has no installed voices.");
      return false;
    }
    return true;
  };

  var playText = useCallback(function(text, from) {
    if (from === undefined) from = 0;
    setTtsErr("");
    if (!checkTTSAvailable()) return;
    stopKeepalive();
    window.speechSynthesis.cancel();
    paraText.current = text;
    var slice = text.slice(from);
    if (!slice.trim()) return;

    // Split into ~200-char chunks at sentence boundaries. Google русский silently
    // fails on long utterances; even local voices benefit from shorter chunks
    // (less chance of the Chrome 15-sec-cutoff bug). Each chunk knows its global
    // char offset so word-boundary events map back to absolute positions.
    var chunks = chunkForTTS(text, from, 200);
    if (chunks.length === 0) return;
    ttsQueue.current = chunks.slice(); // copy so .shift() doesn't mutate caller's reference

    // playChunk pulls the next chunk from the queue and speaks it. When that
    // chunk ends naturally, it calls itself again to keep the chain going.
    var ssn = window.speechSynthesis;
    var playNext = function() {
      if (ttsQueue.current.length === 0) {
        stopKeepalive();
        setPlaying(false);
        charPos.current = 0;
        setSpokenChar(-1);
        return;
      }
      var chunk = ttsQueue.current.shift();
      var u = new SpeechSynthesisUtterance(chunk.text);
      u.lang = "ru-RU"; u.rate = 0.84;
      if (voice) u.voice = voice;
      u.onstart = function() { startKeepalive(); };
      u.onboundary = function(e) {
        if (e.name === "word") {
          var pos = chunk.start + e.charIndex;
          charPos.current = pos;
          setSpokenChar(pos);
        }
      };
      u.onend = function() {
        // Small inter-chunk delay smooths over the cancel/speak Chrome quirk
        // and gives the engine a beat to reset state between chunks.
        setTimeout(playNext, 30);
      };
      u.onerror = function(e) {
        var err = (e && e.error) || "unknown";
        if (err === "interrupted" || err === "canceled") return; // expected on stop
        ttsQueue.current = [];
        stopKeepalive();
        setSpokenChar(-1);
        setTtsErr("Speech error: " + err + ". Try clicking 🎙 Voice to pick a different voice.");
        setPlaying(false);
      };
      try {
        if (ssn.paused) ssn.resume();
        ssn.speak(u);
      } catch (ex) {
        ttsQueue.current = [];
        setTtsErr("speak() threw: " + (ex.message || ex));
        setPlaying(false);
      }
    };

    // Chrome quirk: speak() immediately after cancel() often fails silently —
    // wait a beat after the cancel before starting the chain.
    setTimeout(function() {
      setPlaying(true); charPos.current = from;
      playNext();
    }, 250);
  }, [voice]);

  var pauseTTS = useCallback(function() {
    stopKeepalive();
    ttsQueue.current = [];  // pause halts the chain; resuming would need a fresh playText call
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setPlaying(false);
  }, []);

  var speakMsg = useCallback(function(text, idx) {
    // Read voice from the ref so we always see the most recent pick — never a
    // value captured by useCallback at an earlier render.
    var currentVoice = voiceRef.current;
    setTtsErr("");
    stopKeepalive();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (spkIdx === idx) { setSpkIdx(null); return; }

    var ru = text.split("\n")
      .filter(function(l) { var t=l.trim(); return t && !/^\*{1,2}[^*]+\*{1,2}$/.test(t) && !/^📝/.test(t); })
      .join(" ")
      .replace(/\*\*[^*]+\*\*/g, function(m){ return m.replace(/\*\*/g,""); })
      .replace(/\[[^\]]+\]/g,"").replace(/\*[^*]+\*/g,"")
      .replace(/[a-zA-Z()/[\]{}|]/g,"").replace(/\s+/g," ").trim();
    if (!ru) return;
    setSpkIdx(idx);

    // Browser speechSynthesis — free, no server call. Azure cloud TTS removed.
    if (!checkTTSAvailable()) { setSpkIdx(null); return; }
    setTimeout(function() {
      var u = new SpeechSynthesisUtterance(ru);
      u.lang="ru-RU"; u.rate=0.84;
      var _rv = currentVoice || pickRussianVoice();
      if (_rv) u.voice=_rv;
      u.onstart = function(){ startKeepalive(); };
      u.onend = function(){ stopKeepalive(); setSpkIdx(null); };
      u.onerror = function(e){
        stopKeepalive();
        var err = (e && e.error) || "unknown";
        if (err !== "interrupted" && err !== "canceled") {
          setTtsErr("Speech error: " + err + ".");
        }
        setSpkIdx(null);
      };
      try {
        if (window.speechSynthesis.paused) window.speechSynthesis.resume();
        window.speechSynthesis.speak(u);
      }
      catch(ex) { setTtsErr("speak() threw: " + (ex.message || ex)); setSpkIdx(null); }
    }, 250);
  }, [spkIdx]);

  var runDiagnostics = function() {
    // A speech-engine test bench is meaningless with speech turned off.
    if (!TTS_ENABLED) return;
    var logs = [];
    var addLog = function(line) {
      logs.push(line);
      setDiagLogs(logs.slice());
    };

    addLog("=== TTS DIAGNOSTIC ===");
    addLog("UA: " + navigator.userAgent);
    addLog("speechSynthesis available: " + (window.speechSynthesis ? "YES" : "NO"));
    if (!window.speechSynthesis) return;

    var ss = window.speechSynthesis;
    addLog("Voices count: " + ss.getVoices().length);
    addLog("State before tests — speaking:" + ss.speaking + " pending:" + ss.pending + " paused:" + ss.paused);

    // In sandboxed iframes, the browser sometimes silently drops audio output.
    // Three tests narrow down the cause:
    //   T1 = baseline (English, default voice) — does any TTS work at all?
    //   T2 = Russian language without voice override — does ru-RU work generically?
    //   T3 = Russian with the user's chosen voice — does that specific voice work?

    ss.cancel();

    var runTest = function(name, text, lang, useVoice, delay) {
      setTimeout(function() {
        addLog("--- " + name + ": speak('" + text + "', lang=" + lang + (useVoice && voice ? ", voice=" + voice.name : ", default voice") + ") ---");
        var t0 = Date.now();
        var u = new SpeechSynthesisUtterance(text);
        u.lang = lang; u.rate = 1.0;
        if (useVoice && voice && !voice._cloud) u.voice = voice;

        u.onstart = function() { addLog(name + " onstart @ +" + (Date.now()-t0) + "ms"); };
        u.onend   = function() { addLog(name + " onend   @ +" + (Date.now()-t0) + "ms"); };
        u.onerror = function(e) { addLog(name + " onerror @ +" + (Date.now()-t0) + "ms — error: " + ((e && e.error) || "unknown")); };

        try { ss.speak(u); addLog(name + " speak() returned cleanly"); }
        catch(ex) { addLog(name + " speak() THREW: " + (ex.message || ex)); }

        setTimeout(function() { addLog(name + " +100ms — speaking:" + ss.speaking + " pending:" + ss.pending); }, 100);
        setTimeout(function() { addLog(name + " +500ms — speaking:" + ss.speaking + " pending:" + ss.pending); }, 500);
      }, delay);
    };

    runTest("T1 (English default)", "Hello, this is a test.",  "en-US", false, 200);
    runTest("T2 (Russian default)", "Привет, это тест.",       "ru-RU", false, 4000);
    runTest("T3 (Russian + voice)", "Привет, это тест.",       "ru-RU", true,  8000);

    setTimeout(function() { addLog("=== DIAGNOSTIC COMPLETE === Copy this log and share it."); }, 12000);
  };

  var copyDiagLogs = function() {
    var text = diagLogs.join("\n");
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(function(){});
  };

  // Definitions are cached in localStorage forever. A word's dictionary entry
  // does not change, and the free Gemini tier is a daily budget — re-looking-up
  // "который" for the hundredth time should not spend any of it.
  var DEF_CACHE_PREFIX = "def:";
  var readDefCache = function(key) {
    try {
      var hit = localStorage.getItem(DEF_CACHE_PREFIX + key);
      if (!hit) return null;
      var parsed = JSON.parse(hit);
      return (parsed && parsed.translation) ? parsed : null;
    } catch (_) { return null; }
  };
  var writeDefCache = function(key, data) {
    try { localStorage.setItem(DEF_CACHE_PREFIX + key, JSON.stringify(data)); }
    catch (_) {}   // quota full — the cache is an optimisation, not a requirement
  };

  // Definitions come from dictionaries and nothing else — there is no AI
  // fallback. /api/define tries Yandex first and, server-side, falls through
  // to English Wiktionary for the rare and literary forms Yandex lacks. A word
  // neither of them has (usually a proper name) reports as absent.
  var fetchDef = async function(word) {
    // Yandex Dictionary first: instant, deterministic, free (10k/day), and
    // MORPHO search resolves inflected forms to the lemma server-side. The
    // AI define survives only as a fallback for words the dictionary lacks.
    var clean = (word || "").trim();
    if (!clean) throw new Error("Empty word");

    var cacheKey = clean.toLowerCase();
    var cached = readDefCache(cacheKey);
    if (cached) return cached;

    // -- 1. /api/define: glossary, Yandex, Wiktionary, ru.wiktionary --
    var yandexDown = null;
    var defTrace = null;
    try {
      var r = await authFetch("/api/define?word=" + encodeURIComponent(clean));
      if (r.ok) {
        var data = await r.json();
        if (data && data.translation) {
          writeDefCache(cacheKey, data);
          if (typeof window !== "undefined" && window.DEF_DEBUG) console.log("[def:yandex]", clean, "\u2192", data);
          return data;
        }
      } else {
        var errBody = await r.json().catch(function(){ return {}; });
        if (r.status === 404) {
          // Every tier missed. The server says which ones ran and why each
          // gave up — surface it so a broken tier looks broken, not empty.
          defTrace = errBody.trace || null;
          if (defTrace) console.info("[def:miss]", clean, defTrace.join(" | "), (errBody.ms || "?") + "ms");
        } else {
          yandexDown = errBody.error || ("HTTP " + r.status);
          console.warn("[def] lookup failed:", r.status, yandexDown);
        }
      }
    } catch (netErr) {
      yandexDown = (netErr && netErr.message) || "network error";
      console.warn("[def] Yandex lookup unreachable:", yandexDown);
    }

    // Tagged so the popup can tell "not in the dictionary" apart from a
    // genuinely broken lookup.
    var miss = new Error(yandexDown || ('No dictionary entry for "' + clean + '"'));
    miss.noEntry = !yandexDown;
    miss.serviceDown = yandexDown || null;
    miss.trace = defTrace;
    throw miss;
  };

  // Clicking a Russian word can jump TTS to that word and read onward.
  var jumpTTS = function(charPosition) {
    var txt = (curChapter && curChapter.text) || "";
    if (!txt) return;
    playText(txt, charPosition);
  };

  // Open the two-choice bubble over a clicked word. Positioned the same way
  // as the definition popup, but much shorter, so it can usually sit right
  // under the word.
  var defWord = async function(word, e, charPosition) {
    e.stopPropagation();
    if (noAIMode) return;  // No API calls in read-without-AI mode.
    var clean = word.replace(/[^а-яёА-ЯЁ]/g,"");
    if (!clean || clean.length < 2) return;

    // Stop any in-flight audio and park the player at the sentence that
    // contains this word. User must press ▶ to resume from this point —
    // we deliberately don't auto-play so the click feels like a "pause and
    // look up", not an interruption.
    if (audioElemRef.current) {
      try { audioElemRef.current.pause(); audioElemRef.current.src = ""; } catch(err) {}
      audioElemRef.current = null;
    }
    audioGenRef.current++;  // invalidate any pending fetches
    setAudioPlaying(false); audioPlayingRef.current = false;
    if (typeof charPosition === "number" && currentPage) {
      // charPosition is into the FULL chapter text. Convert to page-relative.
      var pageOffset = charPosition - currentPage.startChar;
      var sIdx = findSentenceIdxForPageOffset(pageOffset);
      if (sIdx >= 0) {
        var sent = audioSentencesRef.current[sIdx];
        // Slice the sentence text from the clicked word onward, so ▶ starts
        // playback at that exact word rather than restarting the sentence.
        var wordOffsetInSentence = pageOffset - sent.start;
        if (wordOffsetInSentence > 0 && wordOffsetInSentence < sent.text.length) {
          var partial = sent.text.slice(wordOffsetInSentence).replace(/^\s+/, "");
          // Store as object so the highlight code can map word indices in the
          // partial text back to character positions in the page.
          sentenceOverrideRef.current = partial ? { text: partial, wordOffsetInSentence: wordOffsetInSentence } : null;
        } else {
          // Word is at the start of the sentence — no override needed; play full sentence.
          sentenceOverrideRef.current = null;
        }
        setAudioIdx(sIdx); audioIdxRef.current = sIdx;
      }
    }

    var rect = e.currentTarget.getBoundingClientRect();
    var pw = Math.min(280, window.innerWidth-32);
    var left = rect.left;
    if (left+pw > window.innerWidth-16) left = window.innerWidth-pw-16;
    if (left < 16) left = 16;
    // Vertical positioning: try below the word first. If the popup would extend
    // past the viewport bottom, try above. If neither side has enough room,
    // position at the top of the viewport — the CSS `max-height: calc(100vh-32px)`
    // and `overflow-y: auto` on `.pop` guarantee the content scrolls internally
    // instead of getting clipped. Estimate is conservative (340px) because
    // popups can be tall: verbs with aspect+conjugations, long examples + tips.
    var POPUP_EST = 340;
    var spaceBelow = window.innerHeight - rect.bottom;
    var spaceAbove = rect.top;
    var top;
    if (spaceBelow >= POPUP_EST + 16) {
      top = rect.bottom + 8;
    } else if (spaceAbove >= POPUP_EST + 16) {
      top = rect.top - POPUP_EST - 8;
    } else {
      // Tight viewport — anchor to top with safe padding; CSS handles overflow.
      top = 16;
    }
    setPopXY({top:Math.max(8,top),left:left});
    setSayState("");
    try { if (sayAudioRef.current) sayAudioRef.current.pause(); } catch(e) {}
    setPopup({word:clean,data:null,loading:true,error:null,yo:null,srcOffset:(typeof charPosition==="number"?charPosition:null)});
    try {
      var data = await fetchDef(clean);
      setPopup(function(p){ return p ? Object.assign({},p,{data:data,loading:false}) : null; });
    } catch(err) {
      var rawMsg = (err && err.message) || "Unknown error";
      var likelyRateLimit = /Too many|rate.?limit|429|quota|exhaust/i.test(rawMsg);
      // The ё-variant offer only makes sense when the WORD was the problem.
      // It used to fire on any failure for any word containing "е", which hid
      // real API errors behind a spelling suggestion — the reason a broken
      // backend looked like a dictionary miss.
      if (err && err.noEntry) {
        // No tier had it. For the admin this is the moment to curate it.
        setPopup(function(p){ return p ? Object.assign({},p,{loading:false,noEntry:clean,trace:err.trace||null}) : null; });
        return;
      }
      var wordMightBeWrong = /not.?found|no entry|unknown word|missing/i.test(rawMsg);
      var vars = wordMightBeWrong ? yoVariants(clean) : [];
      if (vars.length) {
        setPopup(function(p){ return p ? Object.assign({},p,{loading:false,yo:{orig:clean,vars:vars}}) : null; });
      } else {
        var msg = likelyRateLimit
          ? "Too many lookups just now — wait a moment and try again."
          : 'Could not define "' + clean + '" — ' + rawMsg;
        setPopup(function(p){ return p ? Object.assign({},p,{loading:false,error:msg}) : null; });
      }
    }
  };

  var defWithYo = async function(word) {
    setPopup(function(p){ return p ? Object.assign({},p,{loading:true,yo:null,error:null,word:word}) : null; });
    try {
      var data = await fetchDef(word);
      setPopup(function(p){ return p ? Object.assign({},p,{data:data,loading:false}) : null; });
    } catch(err) {
      var m = 'Could not define "' + word + '" — ' + ((err && err.message) || "Unknown error");
      setPopup(function(p){ return p ? Object.assign({},p,{loading:false,error:m}) : null; });
    }
  };

  // Speaker button in the definition popup. Three layers, the same shape as the
  // definition tiers themselves:
  //   1. a real recording by a native speaker, if Wikimedia Commons has one
  //   2. the browser's Russian voice, which the app already ships
  //   3. an honest message when neither works
  // Commons coverage is strongest for common vocabulary and thinnest for the
  // rare and archaic words — the inverse of where the dictionary tiers struggle
  // — so layer 2 carries more of this than you would hope. Ogg Vorbis also
  // doesn't play on older Safari, which lands in the same fallback.
  var sayWord = function(entry, clicked) {
    var lemma = String((entry && entry.lemma) || clicked || "").replace(/\u0301/g, "").trim();
    if (!lemma) return;

    var speakIt = function() {
      try {
        if (!TTS_ENABLED) { setSayState("none"); return; }
        if (!window.speechSynthesis) { setSayState("none"); return; }
        var voice = pickRussianVoice();
        if (!voice) { setSayState("none"); return; }
        try { window.speechSynthesis.cancel(); } catch(e) {}
        var u = new SpeechSynthesisUtterance(lemma);
        u.lang = "ru-RU"; u.voice = voice; u.rate = 0.85;
        u.onend   = function(){ setSayState(""); };
        u.onerror = function(){ setSayState("none"); };
        setSayState("playing");
        window.speechSynthesis.speak(u);
      } catch (e) { setSayState("none"); }
    };

    // Commons names its Russian recordings Ru-<слово>.ogg, and Special:FilePath
    // resolves a bare filename with no API call. /api/define supplies the exact
    // name when the ru.wiktionary tier saw one; otherwise the guess is free —
    // the browser either gets a file or a 404, and a 404 falls through.
    var url = (entry && entry.audioUrl) ||
      ("https://commons.wikimedia.org/wiki/Special:FilePath/" +
       encodeURIComponent("Ru-" + lemma + ".ogg"));

    setSayState("");
    try {
      if (sayAudioRef.current) { try { sayAudioRef.current.pause(); } catch(e) {} }
      var a = new Audio(url);
      sayAudioRef.current = a;
      a.onplaying = function(){ setSayState("playing"); };
      a.onended   = function(){ setSayState(""); };
      a.onerror   = function(){ speakIt(); };
      var pr = a.play();
      if (pr && pr.catch) pr.catch(function(){ speakIt(); });
    } catch (e) { speakIt(); }
  };

  // Admin-only curation. Блатной жаргон and сленг are a long tail no free
  // dictionary covers completely, so the fix for a missed word happens here —
  // in the popup, at the moment the word stops you — and is written straight
  // into the R2 glossary, which /api/define checks ahead of every other tier.
  var startCurate = function(word) {
    setCurate({ word: word, translation: "", definitionRu: "", register: "блатной жаргон",
                partOfSpeech: "", example: "", forms: "", busy: false, err: "" });
  };

  var curateField = function(key, value) {
    setCurate(function(c){ if (!c) return c; var n = Object.assign({}, c); n[key] = value; return n; });
  };

  var saveCurate = async function() {
    if (!curate || curate.busy) return;
    if (!curate.translation.trim()) { curateField("err", "A definition is required."); return; }
    setCurate(function(c){ return c ? Object.assign({}, c, {busy:true, err:""}) : c; });
    try {
      var r = await authFetch("/api/define", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word: curate.word,
          lemma: curate.word,
          translation: curate.translation,
          definitionRu: curate.definitionRu,
          register: curate.register,
          partOfSpeech: curate.partOfSpeech,
          example: curate.example,
          forms: curate.forms,
          source: SITE_NAME_LATIN + " glossary",
        }),
      });
      var body = await r.json().catch(function(){ return {}; });
      if (!r.ok || !body.entry) throw new Error(body.error || ("HTTP " + r.status));
      writeDefCache(String(curate.word).toLowerCase(), body.entry);
      setPopup(function(p){ return p ? Object.assign({}, p, {data:body.entry, noEntry:null, trace:null}) : null; });
      setCurate(null);
    } catch (e) {
      setCurate(function(c){ return c ? Object.assign({}, c, {busy:false, err:(e && e.message) || "Save failed"}) : c; });
    }
  };

              var startLit = async function(idx, chs, metaOverride, startPidx) {
    var p = chs || chapters; if (!p || !p.length) return;
    var i = idx !== undefined ? idx : cbm;
    // Clamp to a valid chapter — a stale source-link jump (or any bad idx) must
    // never land on a non-existent chapter (which renders an empty reader).
    if (typeof i !== "number" || isNaN(i) || i < 0) i = 0;
    if (i >= p.length) i = p.length - 1;
    var pi = (typeof startPidx === "number" && startPidx >= 0) ? startPidx : 0;
    // Open the book. Comprehension is button-triggered, not auto-loaded.
    setCidx(i); setCbm(i); setPidx(pi); setStarted(true); setMsgs([]);
    setPopup(null); stopTTS(); setLview("read");
    charPos.current = 0; paraText.current = "";
  };

  // Look up saved progress for a given book meta. Returns {cidx, pidx} or null.
  var loadBookProgress = async function(meta) {
    var key = bookKey(meta);
    if (!key) return null;
    try {
      var r = await storage.get(BOOK_PROGRESS);
      if (!r) return null;
      var all = JSON.parse(r.value) || {};
      var entry = all[key];
      if (!entry) return null;
      return { cidx: entry.cidx || 0, pidx: entry.pidx || 0 };
    } catch(e) { return null; }
  };

  var navLit = async function(idx) {
    checkForUpdate();
    stopTTS(); charPos.current = 0; paraText.current = "";
    if (idx < 0 || idx >= chapters.length) return;
    // Navigate; no auto-comprehension. User triggers via "Test your comprehension" button.
    setCidx(idx); setCbm(idx); setPidx(0); setMsgs([]); setLview("read");
  };

  // Navigate to a new PAGE within the current chapter. Comprehension questions
  // are only loaded when the user explicitly clicks "Test your comprehension".
  var navPage = async function(newPidx) {
    if (newPidx < 0 || newPidx >= totalPages) return;
    checkForUpdate();
    stopTTS(); charPos.current = 0; paraText.current = "";
    setPidx(newPidx); setMsgs([]); setLview("read");
  };

  // ── Smart song-collection splitter ──────────────────────────────────────
  // Tries multiple deterministic patterns to find song boundaries in a song-
  // collection book. Returns an array of chapters (one per song) if any pattern
  // produces >= options.minSongs (default 3) plausible sections, otherwise null.
  // For Song Lyrics books we lower the threshold to 2 since even 2 songs is
  // valuable — for unknown books we keep 3 to avoid false-positive splits.
  var splitSongsHeuristic = function(chapters, options) {
    options = options || {};
    var minSongs = typeof options.minSongs === "number" ? options.minSongs : 3;
    if (!chapters || !chapters.length) {
      console.log("[songs:heuristic] no chapters passed in — bail");
      return null;
    }
    var fullText = chapters.map(function(ch){ return ch.text || ""; }).join("\n\n");
    if (fullText.length < 300) {
      console.log("[songs:heuristic] full text < 300 chars (" + fullText.length + ") — bail");
      return null;
    }
    var lines = fullText.split("\n");
    console.log("[songs:heuristic] starting — " + lines.length + " lines, " + fullText.length + " chars, minSongs=" + minSongs);

    var strategies = [
      {
        name: "standalone-numbered",
        // Just a digit (optionally with . or )), nothing else
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^\(?\d{1,3}[.)]?\)?$/.test(t);
        },
        // For standalone-numbered, the title is on the NEXT non-blank line
        titleOffset: 1,
      },
      {
        name: "inline-numbered",
        // "1. Title" or "12) Title" — number then dot/paren then title text
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^\d{1,3}[.)]\s+[А-ЯЁA-Z"«].{1,70}$/.test(t) && t.length < 80;
        },
        titleOffset: 0,
      },
      {
        name: "standalone-roman",
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^[IVX]{1,5}\.?$/.test(t);
        },
        titleOffset: 1,
      },
      {
        name: "inline-roman",
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          return /^[IVX]{1,5}[.)]\s+[А-ЯЁA-Z"«].{1,70}$/.test(t) && t.length < 80;
        },
        titleOffset: 0,
      },
      {
        name: "all-caps-cyrillic",
        // Short ALL-CAPS Russian line, surrounded by blank lines.
        // Avoids matching things like "ПРОЩАЙ!" inside a lyric line.
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          if (t.length < 3 || t.length > 80) return false;
          if (!/^[А-ЯЁ][А-ЯЁ\s\-—–.,!?']{1,79}$/.test(t)) return false;
          if (!/[А-ЯЁ]{3,}/.test(t)) return false;  // need actual Cyrillic letters
          var prevBlank = i === 0 || !L[i-1].trim();
          var nextBlank = i + 1 >= L.length || !L[i+1].trim();
          return prevBlank && nextBlank;
        },
        titleOffset: 0,
      },
      {
        name: "title-case-cyrillic",
        // Short Title Case line alone, surrounded by blanks. Strict to avoid
        // matching sentences. Excludes lines ending in . , ; : ! ? (which
        // are likely sentences, not titles).
        isTitleLine: function(L, i) {
          var t = L[i].trim();
          if (t.length < 3 || t.length > 60) return false;
          if (!/^[А-ЯЁ]/.test(t)) return false;
          if (/[.,;:!?]$/.test(t)) return false;
          // Reject sentence-like lines (many words)
          var words = t.split(/\s+/);
          if (words.length > 7) return false;
          // Must be alone on its line: blanks before AND after
          var prevBlank = i === 0 || !L[i-1].trim();
          var nextBlank = i + 1 >= L.length || !L[i+1].trim();
          return prevBlank && nextBlank;
        },
        titleOffset: 0,
      },
    ];

    var best = null;
    var bestName = "";

    for (var s = 0; s < strategies.length; s++) {
      var strat = strategies[s];
      var titleIdxs = [];
      for (var i = 0; i < lines.length; i++) {
        if (strat.isTitleLine(lines, i)) titleIdxs.push(i);
      }
      console.log("[songs:heuristic] " + strat.name + ": " + titleIdxs.length + " marker lines found"
        + (titleIdxs.length > 0 ? " at lines " + titleIdxs.slice(0, 8).join(",") + (titleIdxs.length > 8 ? "..." : "") : ""));
      // Heuristic validity checks
      if (titleIdxs.length < minSongs) {
        console.log("[songs:heuristic]   ↳ rejected: needs >= " + minSongs);
        continue;
      }
      // Sections shouldn't be too dense — if there's a title every 3 lines,
      // we're probably matching false positives (like ALL CAPS dialogue tags).
      var avgGap = lines.length / titleIdxs.length;
      if (avgGap < 6) {
        console.log("[songs:heuristic]   ↳ rejected: density too high (avgGap=" + avgGap.toFixed(1) + ")");
        continue;
      }

      var sections = [];
      for (var k = 0; k < titleIdxs.length; k++) {
        var start = titleIdxs[k];
        var end = k + 1 < titleIdxs.length ? titleIdxs[k+1] : lines.length;
        var heading = lines[start].trim();
        // For standalone-numbered/roman, the actual title is on the next
        // non-blank line after the marker
        if (strat.titleOffset === 1) {
          for (var n = start + 1; n < end && n < lines.length; n++) {
            if (lines[n].trim()) { heading = lines[n].trim(); break; }
          }
        }
        var bodyText = lines.slice(start, end).join("\n").trim();
        // Drop sections that are mostly empty / non-Russian — those are
        // probably false-positive matches (front matter, table of contents).
        var cyrCount = (bodyText.match(/[а-яёА-ЯЁ]/g) || []).length;
        if (cyrCount < 20) continue;
        sections.push({ heading: heading, text: bodyText });
      }
      console.log("[songs:heuristic]   ↳ " + sections.length + " valid sections after filtering");

      if (sections.length >= minSongs) {
        if (!best || sections.length > best.length) {
          best = sections;
          bestName = strat.name;
        }
      }
    }

    if (best) console.log("[songs] heuristic split via " + bestName + " → " + best.length + " songs");
    return best;
  };

  // Apply a regex pattern (from AI or other source) to split full text into
  // song chapters. Pattern matches a line that begins a new song.
  var splitByRegexPattern = function(fullText, patternStr) {
    try {
      var re = new RegExp(patternStr, "m");
      var lines = fullText.split("\n");
      var indices = [];
      for (var i = 0; i < lines.length; i++) {
        // Test against trimmed line (most patterns assume no leading whitespace)
        if (re.test(lines[i].trim())) indices.push(i);
      }
      if (indices.length < 3) return null;
      var result = [];
      for (var k = 0; k < indices.length; k++) {
        var start = indices[k];
        var end = k + 1 < indices.length ? indices[k+1] : lines.length;
        var text = lines.slice(start, end).join("\n").trim();
        var heading = lines[start].trim();
        var cyr = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
        if (cyr < 20) continue;
        result.push({ heading: heading, text: text });
      }
      return result.length >= 3 ? result : null;
    } catch(e) { return null; }
  };

  // Re-split chapters by lines that contain only a digit (or "digit.")
  // Used for song-collection EPUBs like Tsoi, where each track number marks a new "chapter".
  // The first non-empty line after the number becomes the chapter heading (song title).
  var resplitByNumberedSections = function(chapters) {
    var fullText = chapters.map(function(ch){ return ch.text || ""; }).join("\n\n");
    var lines = fullText.split("\n");
    console.log("[songs:numbered] scanning " + lines.length + " lines for /^\\d{1,3}\\.?$/ markers");
    var out = [];
    var current = null;
    var awaitingTitle = false;
    var markerLines = [];
    for (var i = 0; i < lines.length; i++) {
      var t = lines[i].trim();
      if (/^\d{1,3}\.?$/.test(t)) {
        markerLines.push(i);
        // Track number found — start a new section
        if (current && (current.text || "").trim()) out.push(current);
        current = { heading: "", text: "" };
        awaitingTitle = true;
      } else if (current) {
        if (awaitingTitle && t) {
          current.heading = t;
          current.text = t + "\n";
          awaitingTitle = false;
        } else if (!awaitingTitle) {
          current.text += lines[i] + "\n";
        }
      }
    }
    if (current && (current.text || "").trim()) out.push(current);
    console.log("[songs:numbered] found " + markerLines.length + " markers at lines [" + markerLines.slice(0, 10).join(",") + (markerLines.length > 10 ? "..." : "") + "] → " + out.length + " sections");
    if (out.length > 0) {
      out.forEach(function(s, i){ console.log("  song " + (i+1) + ": \"" + (s.heading || "(no heading)") + "\""); });
    }
    return out.length ? out : chapters;
  };

  var loadFile = async function(buf, fname, opts) {
    setFErr("");
    opts = opts || {};
    try {
      var result = await parseBook(buf, fname);
      if (!result.chapters || result.chapters.length < 1) throw new Error("No chapters found in file.");
      var chs = result.chapters;
      // Song-collection mode: any book in the "Song Lyrics" category should
      // be split one-song-per-chapter, regardless of how the source EPUB
      // structured its spine. We use a tiered strategy:
      //   1. If the existing chapters already look like one-song-each (short,
      //      named, multiple of them), trust the source's split.
      //   2. Otherwise run the smart heuristic splitter — tries numbered,
      //      Roman numeral, ALL CAPS, Title Case patterns.
      //   3. If heuristics fail, ask the AI to find the boundary pattern.
      //   4. Last resort: the legacy resplitByNumberedSections (if the user
      //      explicitly set the flag in index.json).
      var isSongBook = opts.category === "Song Lyrics";
      console.log("[songs:load] file=" + fname + " category=" + opts.category + " flag=" + opts.splitByNumberedSections + " initial-chapters=" + chs.length);
      if (isSongBook) {
        // 1. EXPLICIT FORMAT FLAG WINS. Uploads always set `splitByNumberedSections: true`
        //    because we know the file format (numbered Tsoi-style). Trust it. This is the
        //    fast path for every uploaded artist file.
        if (opts.splitByNumberedSections) {
          console.log("[songs:load] explicit splitByNumberedSections flag set — trying numbered split first");
          var byNum = resplitByNumberedSections(chs);
          if (byNum && byNum.length > chs.length) {
            console.log("[songs:load] numbered split won: " + byNum.length + " sections (was " + chs.length + ")");
            chs = byNum;
          } else {
            console.log("[songs:load] numbered split did not improve count (" + (byNum ? byNum.length : 0) + " vs " + chs.length + ")");
          }
        }
        // 2. After (or in lieu of) the explicit flag, if we STILL have one big chapter,
        //    try smart splitting. This handles song books from external sources without
        //    the explicit flag, AND the case where splitByNumberedSections didn't find
        //    its markers (different format).
        if (chs.length <= 1) {
          var avgLen0 = chs.length ? (chs[0].text || "").length : 0;
          if (avgLen0 > 500) {
            console.log("[songs:load] still 1 chapter — running heuristic splitter");
            var smart = splitSongsHeuristic(chs, { minSongs: 2 });
            if (smart && smart.length >= 2) {
              console.log("[songs:load] heuristic won: " + smart.length + " sections");
              chs = smart;
            } else {
              console.log("[songs:load] heuristic failed — file will be shown as one page");
            }
          } else {
            console.log("[songs:load] file too short for smart splitting (" + avgLen0 + " chars)");
          }
        }
      } else if (opts.splitByNumberedSections) {
        // Non-song-category book with the legacy flag set: use original behavior.
        chs = resplitByNumberedSections(chs);
      } else {
        // Default for novels/stories/plays: re-split by in-text chapter markers
        // (Roman numerals, "Глава N", etc.). The author told us the chapter
        // boundaries by putting markers in the text — use those instead of
        // trusting spine items or TOC labels.
        // Scripture (Bible) already arrives fully structured from the FB2 parser as
        // "Testament — Book — Глава N". Re-splitting by in-text markers (isChapterMarker
        // treats bare numbers / "Глава N" as boundaries) would flatten it to bare "Глава N"
        // and destroy the Testament/Book tiers - so skip the re-split when 3-tier headings exist.
        var alreadyScripture = chs.length > 1 && chs.some(function(c){
          return c.heading && c.heading.split(/\s+[\u2013—]\s+/).length >= 3;
        });
        // Don't re-split by in-text markers when the source already gave us two
        // or more real, distinct chapter headings (e.g. an FB2 with a
        // <title>\u0413\u043b\u0430\u0432\u0430 \u043f\u0435\u0440\u0432\u0430\u044f</title> per chapter). The marker re-split exists for
        // blob / heading-less imports; run on a properly-structured book it shreds
        // poems on their stanza numerals — \u041e\u043d\u0435\u0433\u0438\u043d's "I, II, III …" each became a
        // "chapter", so a whole \u0413\u043b\u0430\u0432\u0430's audio played against a single stanza of
        // text. Placeholder headings ("\u0413\u043b\u0430\u0432\u0430 1", "Chapter 1") don't count as real.
        var realHeadings = chs.filter(function(c){
          var h = (c.heading || "").trim();
          return h && !/^\u0433\u043b\u0430\u0432\u0430\s+\d+$/i.test(h) && !/^chapter\s+\d+$/i.test(h);
        }).length;
        var bymark = (alreadyScripture || realHeadings >= 2) ? null : splitByMarkers(chs);
        if (bymark && bymark.length >= 2) {
          chs = bymark;
        } else if (!alreadyScripture && chs.length > 1) {
          // Only collapse if chapters have no meaningful headings. Books with
          // subtitle-split chapters (e.g. "ЧАСТЬ ПЕРВАЯ — I") already have
          // proper headings and should NOT be merged.
          var hasHeadings = chs.some(function(c){ return c.heading && c.heading.trim().length > 0; });
          if (!hasHeadings) {
            var merged = chs.map(function(c){ return c.text || ""; }).join("\n\n").trim();
            chs = [{ heading: "", text: merged }];
          }
        } else if (chs.length === 1) {
          // Single chapter from spine — strip any auto-generated heading.
          var h = chs[0].heading || "";
          if (/^глава\s+\d+$/i.test(h.trim()) || /^chapter\s+\d+$/i.test(h.trim())) h = "";
          chs = [{ heading: h, text: chs[0].text || "" }];
        }
      }
      // Attach per-chapter YouTube URLs from the optional `songs` array on the
      // book entry. The array is indexed by chapter position (0-based), so the
      // user just lists URLs in song order in index.json. Missing/null entries
      // mean "no link for this song".
      if (Array.isArray(opts.songs)) {
        chs = chs.map(function(ch, i){
          var entry = opts.songs[i];
          var url = "";
          if (typeof entry === "string") url = entry;
          else if (entry && typeof entry === "object" && typeof entry.youtube === "string") url = entry.youtube;
          return url ? Object.assign({}, ch, { youtubeUrl: url }) : ch;
        });
      }

      var title = opts.title || result.title;
      var author = opts.author || result.author;
      // bookMeta carries title/author plus presentation flags the reader needs.
      // `category` drives single-page display mode (anything in "Song Lyrics"
      // shows one song per screen). `splitByNumberedSections` is the older
      // parsing flag — kept for backward compatibility and still triggers
      // single-page mode independently.
      var meta = {
        title: title,
        author: author,
        filename: fname || "",   // needed for vocab source backlinks (goToSource matches on this)
        category: opts.category || "",
        splitByNumberedSections: !!opts.splitByNumberedSections,
        audiobook: opts.audiobook || null,
        // Carried so the audiobook loader knows to fetch this book's chapter
        // JSON and audio through /api/media rather than from /books/.
        restricted: !!opts.restricted,
        parallelEn: opts.parallelEn || null,
        // Shown above the English pane. A verse translation is a work in its
        // own right and does not track the Russian line for line, so a book
        // that pairs one says so rather than implying a literal gloss.
        translationNote: opts.translationNote || "",
        // Plays only: enables inline golden speaker-name formatting. Novels
        // must never get it — "Москва. Тишина стояла..." is not a character.
        play: !!opts.play,
      };
      setChapters(chs);
      setBookMeta(meta);
      setCbm(0);
      try {
        if (opts.restricted) {
          // A restricted book is never cached locally: the cache outlives the
          // session, and the whole point of the gate is that the text does
          // not. Clear whatever was cached before rather than leaving the
          // previous book to be restored on the next launch.
          await storage.delete(EPUB_CACHE);
          await storage.delete(EPUB_BM);
        } else {
          await storage.set(EPUB_CACHE, JSON.stringify({
            chapters: chs, title: title, author: author,
            category: opts.category || "",
            splitByNumberedSections: !!opts.splitByNumberedSections
          }));
          await storage.set(EPUB_BM, "0");
        }
        await storage.delete(QHIST_KEY);
      } catch(e) {}
      // Track user uploads (not preset book downloads) in the multi-upload list
      // so they show up in the library view alongside the preset books.
      if (!opts.fromPreset) {
        try {
          var id = "u" + Date.now();
          var entry = {
            id: id,
            title: title,
            author: author,
            filename: fname || "Upload",
            category: opts.category || "",
            splitByNumberedSections: !!opts.splitByNumberedSections,
            addedAt: Date.now(),
          };
          await storage.set(UPLOAD_BOOK_PREFIX + id, JSON.stringify({
            chapters: chs, title: title, author: author,
            category: entry.category, splitByNumberedSections: entry.splitByNumberedSections,
            filename: entry.filename,
          }));
          // Update list, newest-first, with eviction of oldest beyond MAX_UPLOADS.
          var current = uploadedBooks.slice();
          current.unshift(entry);
          while (current.length > MAX_UPLOADS) {
            var evicted = current.pop();
            try { await storage.delete(UPLOAD_BOOK_PREFIX + evicted.id); } catch(e) {}
          }
          await storage.set(UPLOADS_LIST_KEY, JSON.stringify(current));
          setUploadedBooks(current);
        } catch(e) { console.log("Failed to track upload:", e); }
      }
      // Resume from saved progress if this exact book has been opened before.
      var savedProg = await loadBookProgress(meta);
      var startCi = savedProg ? savedProg.cidx : 0;
      var startPi = savedProg ? savedProg.pidx : 0;
      if (srcJumpChapterRef.current !== null && srcJumpChapterRef.current !== undefined) {
        startCi = srcJumpChapterRef.current; startPi = 0;
        srcJumpChapterRef.current = null;
      }
      startLit(startCi, chs, meta, startPi);
    } catch(err) { setFErr(err.message); }
  };

  // Download a preset book from the server and load it through the normal pipeline.
  var loadPresetBook = async function(book) {
    // Opening a story is the other navigation moment worth checking on.
    checkForUpdate();
    setFErr("");
    setBookLoading(book.filename);
    try {
      var r = await fetch(bookFileUrl(book), { credentials: "same-origin" });
      if (!r.ok) throw new Error("Could not load « " + book.filename + " »: HTTP " + r.status);
      var buf = await r.arrayBuffer();
      await loadFile(buf, book.filename, {
        fromPreset: true,
        splitByNumberedSections: !!book.splitByNumberedSections,
        title: book.title,
        author: book.author,
        category: book.category || "",
        // Optional per-chapter YouTube links (used by song collections). Array
        // indexed 0..N where each entry is a URL or null/missing.
        songs: Array.isArray(book.songs) ? book.songs : null,
        audiobook: book.audiobook || null,
        restricted: !!book.restricted,
        parallelEn: book.parallelEn || null,
        translationNote: book.translationNote || "",
        play: !!book.play,
      });
    } catch(err) {
      setFErr(err.message || "Failed to load preset book");
    }
    setBookLoading(null);
  };

  // Open one of the user's previously uploaded books from local storage.
  // Reads the parsed content saved by loadFile and rehydrates the reader state.
  var openUploadedBook = async function(book) {
    setFErr("");
    setBookLoading(book.id);
    try {
      var r = await storage.get(UPLOAD_BOOK_PREFIX + book.id);
      if (!r || !r.value) {
        setFErr("This uploaded book is no longer available in storage.");
        setBookLoading(null);
        return;
      }
      var d = JSON.parse(r.value);
      var meta = {
        title: d.title || book.title || "Untitled",
        author: d.author || book.author || "",
        category: d.category || book.category || "",
        splitByNumberedSections: !!d.splitByNumberedSections,
        audiobook: book.audiobook || d.audiobook || null,
      };
      setChapters(d.chapters);
      setBookMeta(meta);
      setCbm(0);
      // Bring the entry to the top of the recents list (touch to refresh "addedAt").
      try {
        var updated = uploadedBooks.filter(function(x){ return x.id !== book.id; });
        updated.unshift(Object.assign({}, book, { addedAt: Date.now() }));
        await storage.set(UPLOADS_LIST_KEY, JSON.stringify(updated));
        setUploadedBooks(updated);
      } catch(e) {}
      // Resume from saved progress if this book has been opened before.
      var savedProg2 = await loadBookProgress(meta);
      var startCi2 = savedProg2 ? savedProg2.cidx : 0;
      var startPi2 = savedProg2 ? savedProg2.pidx : 0;
      startLit(startCi2, d.chapters, meta, startPi2);
    } catch(err) {
      setFErr("Failed to open uploaded book: " + (err.message || err));
    }
    setBookLoading(null);
  };

  // Permanently remove an uploaded book from the library + storage.
  var removeUploadedBook = async function(id) {
    try {
      await storage.delete(UPLOAD_BOOK_PREFIX + id);
      var current = uploadedBooks.filter(function(b){ return b.id !== id; });
      await storage.set(UPLOADS_LIST_KEY, JSON.stringify(current));
      setUploadedBooks(current);
    } catch(e) {
      console.log("Failed to remove upload:", e);
    }
  };

  // Fetch the library manifest once on mount. Silent if missing — pre-loaded books are optional.
  useEffect(function() {
    fetch("/api/catalogue", { credentials: "same-origin" })
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(list){ if (Array.isArray(list)) setPresetBooks(list); })
      .catch(function(){ /* no library, that's fine */ });
    // Re-fetch when the session changes: signing in as the admin adds the
    // restricted books, signing out has to take them away again.
  }, [me]);

  // Fetch the grammar curriculum once on mount. The file lives in /public/grammar/
  // so it's served as a static asset; edits to the JSON take effect immediately
  // on next deploy without code changes.
  useEffect(function() {
    fetch("/grammar/curriculum.json")
      .then(function(r){ if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function(data){ setCurriculum(data); })
      .catch(function(err){ setGramErr("Couldn't load curriculum: " + (err.message || err)); });
  }, []);

      var addV = function(ruOrEntry, en) {
    // Accepts either (ruString, enString) for legacy callers OR a full entry object:
    //   {ru, en, pos, aspect, grammar, example, exampleTranslation}
    var entry = (typeof ruOrEntry === "string")
      ? { ru: ruOrEntry, en: en || "" }
      : (ruOrEntry || {});
    var ru = (entry.ru || "").trim();
    if (!ru) return;
    if (vocab.find(function(v){ return v.ru === ru; })) return;
    var now = Date.now();
    // Capture where the word was saved from, for the source backlink. Only set
    // when reading a book (bookMeta.filename present). Stored fields are added
    // to the server allowlist in api/user-data.js so they persist.
    var srcFields = {};
    if (bookMeta && bookMeta.filename) {
      srcFields.srcBook = bookMeta.filename;
      srcFields.srcTitle = bookMeta.title || "";
      srcFields.srcChapter = (typeof cidx === "number") ? cidx : null;
    }
    setVocab(function(p){
      var key = String(now) + "_" + p.length;
      return p.concat([Object.assign({}, entry, srcFields, { ru: ru, created: now, _key: key })]);
    });
  };
  var addT = function(tip) {
    if (!tips.find(function(t){ return t.tip===tip; })) {
      var now = Date.now();
      setTips(function(p){ return p.concat([{tip:tip,id:now,created:now}]); });
    }
  };
  // ── Vocab quiz generator ─────────────────────────────────────────────────
  // Builds an array of multiple-choice questions from the vocab list. For each
  // word (with an English meaning AND a part-of-speech tag), we pick 3 random
  // distractors from OTHER words with the same `pos`. If a word's pos group has
  // fewer than 3 valid siblings, that word is skipped (insufficient distractors).
  // Words without a `pos` tag are also skipped — verbs-vs-nouns mixing defeats
  // the pedagogy.
  var goToSource = function(v) {
    if (!v || !v.srcBook) return;
    var book = null;
    for (var i = 0; i < presetBooks.length; i++) {
      if (presetBooks[i].filename === v.srcBook) { book = presetBooks[i]; break; }
    }
    if (!book) { alert("That book isn't in the library anymore."); return; }
    srcJumpChapterRef.current = (typeof v.srcChapter === "number") ? v.srcChapter : 0;
    srcJumpOffsetRef.current = (typeof v.srcOffset === "number") ? v.srcOffset : null;
    // The reader renders inside the "chat" tab (when started && isLit), so we
    // must switch there — from the vocab tab the reader is otherwise hidden.
    setMode("read");
    setTab("chat");
    loadPresetBook(book);
  };

  var startQuiz = function(posFilter) {
    // Known-words stoplist first: saved words that are among the ~500 most
    // common are never quizzed. They stay in the vocab list (still visible,
    // still usable in chat practice) — they just aren't tested.
    var quizVocab = dropCommonWords(vocab, function(v){ return v && v.ru; });
    var commonSkipped = vocab.length - quizVocab.length;

    // Group vocab by normalized pos. A word needs `en` (the English meaning to
    // quiz on) and `pos` (so we can find same-category distractors) to qualify.
    var groups = {};
    quizVocab.forEach(function(v){
      var p = (v.pos || "").toLowerCase().trim();
      if (!p) return;          // no pos → skipped entirely
      if (!v.en) return;       // no English meaning → can't quiz
      if (!groups[p]) groups[p] = [];
      groups[p].push(v);
    });

    // GATE: a quiz needs at least 10 words sharing one part of speech. If no
    // type reaches 10, tell the user clearly instead of starting an empty quiz.
    var QUIZ_MIN = 10;
    var biggest = 0, biggestType = "";
    Object.keys(groups).forEach(function(k){
      if (groups[k].length > biggest) { biggest = groups[k].length; biggestType = k; }
    });
    if (biggest < QUIZ_MIN) {
      var near = biggest > 0 ? (" Your largest group is " + biggestType + " with " + biggest + ".") : "";
      var common = commonSkipped > 0 ? (" (" + commonSkipped + " saved word(s) were skipped because they're on your known-words list.)") : "";
      alert("A quiz needs at least 10 saved words of the same part of speech (for example, 10 nouns or 10 verbs), each with an English meaning." + near + common + " Keep adding words!");
      return;
    }

    var shuffle = function(arr) {
      var a = arr.slice();
      for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
      }
      return a;
    };

    var questions = [];
    var skipped = 0;
    quizVocab.forEach(function(v){
      var p = (v.pos || "").toLowerCase().trim();
      if (!p || !v.en) { skipped++; return; }
      var filterPos = (typeof posFilter === "string" && posFilter) ? posFilter.toLowerCase().trim() : null;
      if (filterPos && p !== filterPos) { skipped++; return; }
      if ((groups[p] || []).length < QUIZ_MIN) { skipped++; return; }   // only quiz 10+ types
      var siblings = (groups[p] || []).filter(function(x){ return (x._key||x.id) !== (v._key||v.id); });
      if (siblings.length < 3) { skipped++; return; }
      var distractors = shuffle(siblings).slice(0, 3).map(function(s){ return s.en; });
      questions.push({
        word: v.ru,
        correct: v.en,
        options: shuffle(distractors.concat([v.en])),
        pos: v.pos,
      });
    });

    if (questions.length === 0) {
      alert("You need more saved vocabulary! Add at least 4 words that share the same part of speech (e.g. 4 verbs), each with an English meaning and a part-of-speech tag.");
      return;
    }

    var skipNote = skipped > 0 ? skipped + " word(s) skipped (no part-of-speech tag or too few same-pos siblings)." : "";
    if (commonSkipped > 0) skipNote += (skipNote ? " " : "") + commonSkipped + " word(s) skipped — already on your known-words list.";
    setQuizSkipNote(skipNote);
    setQuizQuestions(shuffle(questions));
    setQuizIdx(0);
    setQuizSelected(null);
    setQuizScore(0);
    setQuizMenu(false);
    setQuizMode(true);
  };

  // Bookmarks for grammar curriculum topics. We only store the topic ID — when
  // the user clicks a saved card we re-render the full content from curriculum.json,
  // so edits to the curriculum are reflected in already-saved entries.
  var addTopic = function(topicId) {
    if (!topicId) return;
    setSavedTopics(function(p){ return p.indexOf(topicId) === -1 ? p.concat([topicId]) : p; });
  };
  var rmTopic = function(topicId) {
    setSavedTopics(function(p){ return p.filter(function(id){ return id !== topicId; }); });
  };

  // Format a timestamp (ms since epoch) as a friendly relative date string.
  var formatVocabDate = function(ts) {
    if (!ts || isNaN(ts)) return "";
    var d = new Date(ts);
    var now = new Date();
    var diffMs = now - d;
    var diffMins = Math.floor(diffMs / 60000);
    var diffHrs  = Math.floor(diffMs / 3600000);
    var diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1)  return "just now";
    if (diffMins < 60) return diffMins + " min ago";
    if (diffHrs  < 24 && now.getDate() === d.getDate()) {
      return "Today, " + d.getHours().toString().padStart(2,"0") + ":" + d.getMinutes().toString().padStart(2,"0");
    }
    if (diffDays < 2)  return "Yesterday";
    if (diffDays < 7)  return diffDays + " days ago";
    // Older: "11 May 2026"
    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return d.getDate() + " " + months[d.getMonth()] + " " + d.getFullYear();
  };

  // Builds the canonical vocab entry from popup data:
  //   - nouns/adj/etc → lemma in nominative
  //   - verb without clear pair → infinitive
  //   - verb with pair → "imperfective / perfective" (or just "lemma / pair" if aspect unknown)
  var formatVocabEntry = function(data, fallback) {
    var fallbackRu = (fallback || "").trim();
    if (!data) return { ru: fallbackRu, en: "" };
    var lemma = (data.lemma || data.word || fallbackRu || "").trim();
    var pair  = (data.aspectPair || "").trim();
    var aspect = (data.aspect || "").toLowerCase();
    var ru;
    if (pair) {
      // Conventional dictionary order: imperfective / perfective.
      if (/imperf/.test(aspect))      ru = lemma + " / " + pair;
      else if (/^perf/.test(aspect))  ru = pair + " / " + lemma;
      else                            ru = lemma + " / " + pair;
    } else {
      ru = lemma;
    }
    return {
      ru: ru || fallbackRu,
      en: (data.translation || "").trim(),
      pos: (data.partOfSpeech || "").trim(),
      aspect: (data.aspect || "").trim(),
      grammar: (data.grammar || "").trim(),
      example: (data.example || "").trim(),
      exampleTranslation: (data.exampleTranslation || "").trim()
    };
  };

  var xBold = function(text) {
    var r = []; var re = /\*\*([^*\n(]{1,40})\(([^)]{1,60})\)\*\*/g; var m;
    while ((m = re.exec(text)) !== null) if (m[1].trim()) r.push({ru:m[1].trim(),en:m[2].trim()});
    return r;
  };
  var xTips = function(text) {
    var r = []; var re = /📝\s*TIP[:\s]+(.+)/g; var m;
    while ((m = re.exec(text)) !== null) if (m[1].trim()) r.push(m[1].trim());
    return r;
  };

  var renderLit = function(text) {
    var str = typeof text === "string" ? text : ((text && text.text) ? text.text : "");

    // Build tokens with absolute character positions in the original chapter text,
    // so we can match against onboundary events from speechSynthesis.
    var tokens = [];
    var tre = /[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+/g;
    var tm;
    while ((tm = tre.exec(str)) !== null) {
      tokens.push({
        text: tm[0],
        start: tm.index,
        end: tm.index + tm[0].length,
        isRu: /[а-яёА-ЯЁ]/.test(tm[0][0])
      });
    }

    // ── Highlight matching ──
    // The TTS engine fires onboundary events that may land in whitespace, punctuation,
    // or be slightly off the start of a word. We compute the "active word" as the LAST
    // Russian token whose start ≤ spokenChar. The highlight then stays on a word from
    // the moment the engine reports its position until the next word's position arrives.
    // This prevents the shakiness/skipping you see when matching only on exact ranges.
    var activeStart = -1;
    if (noAIMode && spokenChar >= 0) {
      for (var ai = 0; ai < tokens.length; ai++) {
        if (tokens[ai].isRu && tokens[ai].start <= spokenChar) {
          activeStart = tokens[ai].start;
        } else if (tokens[ai].isRu && tokens[ai].start > spokenChar) {
          break;
        }
      }
      // Clear the highlight if the spoken position has run well past the last Russian word
      // (handles the moment between speech ending and onend firing).
      if (activeStart >= 0) {
        var lastRu = tokens.reduce(function(acc, t){ return t.isRu ? t : acc; }, null);
        if (lastRu && spokenChar > lastRu.end + 200) activeStart = -1;
      }
    }

    // Group tokens into paragraphs. For song books, EVERY newline creates a
    // new visual line (one lyric line per paragraph). For prose, only blank
    // lines (\n{2,}) separate paragraphs — single newlines are just word-wrap.
    var paraBreakRe = singlePageMode ? /\n+/g : /\n{2,}/g;
    var paragraphs = [[]];
    for (var ti = 0; ti < tokens.length; ti++) {
      var tok = tokens[ti];
      if (tok.isRu) {
        paragraphs[paragraphs.length-1].push(tok);
        continue;
      }
      var sub = tok.text, subStart = tok.start, lastIdx = 0;
      var brkRe = new RegExp(paraBreakRe.source, "g"), brk;
      while ((brk = brkRe.exec(sub)) !== null) {
        if (brk.index > lastIdx) {
          paragraphs[paragraphs.length-1].push({
            text: sub.slice(lastIdx, brk.index),
            start: subStart + lastIdx,
            end:   subStart + brk.index,
            isRu: false
          });
        }
        paragraphs.push([]);
        lastIdx = brk.index + brk[0].length;
      }
      if (lastIdx < sub.length) {
        paragraphs[paragraphs.length-1].push({
          text: sub.slice(lastIdx),
          start: subStart + lastIdx,
          end:   tok.end,
          isRu: false
        });
      }
    }

    // Side-by-side dual language is on whenever this chapter has English
    // loaded (Bible verses or parallelEn prose). RU column = full reader
    // width; EN column slides in from the right.
    var dualActive = !!(proseEn || bibleEn);
    var litEntries = (function() {
      // Pull the non-empty paragraphs in the order they appear, matching how
      // computePages indexes them.
      var nonEmpty = paragraphs.filter(function(p){ return p.some(function(t){ return t.text.trim().length > 0; }); });
      if (!currentPage) return [];

      // Single-page mode (e.g. song lyrics): show the whole chapter, no slicing.
      if (currentPage.isSinglePage || currentPage.paraIndices === null) {
        return nonEmpty.map(function(p2, i2){ return { para: p2, chIdx: i2 }; });
      }

      if (currentPage.isSplit) {
        // Giant single-paragraph chapter: the only paragraph is split across
        // multiple pages by sentence boundary. Render only the tokens that fall
        // within this page's char range.
        var giant = nonEmpty[0] || [];
        var sliced = giant.filter(function(tok) {
          return tok.start >= currentPage.startChar && tok.end <= currentPage.endChar;
        });
        return sliced.length > 0 ? [{ para: sliced, chIdx: 0 }] : [];
      }
      // Normal case: render the whole paragraphs that belong to this page,
      // keeping each one's chapter-level paragraph index (parallel text keys on it).
      return currentPage.paraIndices.map(function(idx){ return { para: nonEmpty[idx] || [], chIdx: idx }; }).filter(function(e2){ return e2.para.length > 0; });
    })();
    var litRendered = litEntries.map(function(entry, pi, paraArr) {
        var para = entry.para;
        // Detect play-style speaker attribution at the start of a paragraph.
        // Russian plays commonly use Title Case names like "Маша. ..." or "Медведенко. ..."
        // (Chekhov, Ostrovsky, Tolstoy plays). Older drama uses ALL CAPS like "ЛУКА. ..." (Gorky).
        // Pattern: 1-3 Russian Title-Case or ALL-CAPS words, then . : — – or -, then space + dialogue.
        var paraText = para.map(function(t){ return t.text; }).join("");
        // Play-line detection: NAME punct dialogue. Skip for song books since
        // lines like "Владимирский централ - ветер северный" would otherwise
        // false-match as a speaker named "Владимирский централ".
        // Горе от ума: speaker names are merged into the first line of each
        // speech in the FB2 (Chekhov print style, "Имя. Реплика"), but the
        // generic Title-Case pattern below misses this play's odd labels
        // ("1-я княжна", "Лиза и София", "Лакей его"), so the play matches
        // against its exact cast list instead — zero false positives on verse
        // lines that merely open with a capitalized word.
        var isGorePlay = bookMeta && bookMeta.filename && bookMeta.filename.indexOf("gore-ot-uma") !== -1;
        var goreSpeakerRe = /^(Графиня-бабушка|Графиня-внучка|Наталья Дмитриевна|Платон Михайлович|Голос Софии|Лиза и София|Все вместе|Лакей его|[1-6]-я княжна|Лизанька|Молчалин|Репетилов|Скалозуб|Загорецкий|Хлёстова|Княгиня|Фамусов|Чацкий|София|Князь|Лакей|Слуга|Лиза|Всё|Все)([.:])(\s+)/;
        // Speaker formatting is opt-in per book via the catalogue's
        // "play": true flag — prose paragraphs that happen to open with a
        // Title-Case word + period ("Москва. Тишина...") must stay plain.
        var speakerMatch = (singlePageMode || !(bookMeta && bookMeta.play)) ? null
          : (isGorePlay
              ? paraText.match(goreSpeakerRe)
              : paraText.match(/^([А-ЯЁ][а-яёА-ЯЁ\-]+(?:\s+[А-ЯЁ][а-яёА-ЯЁ\-]+){0,2})\s*([.:—–\-])(\s+)/));
        var speakerNameEnd = -1, attribEnd = -1;
        // Guard against false positives — name must look like a name (≤40 chars) and there must be dialogue after.
        if (speakerMatch && speakerMatch[1].length <= 40 && paraText.length > speakerMatch[0].length + 3) {
          speakerNameEnd = (para[0] ? para[0].start : 0) + speakerMatch[1].length;
          attribEnd     = (para[0] ? para[0].start : 0) + speakerMatch[0].length;
        }

        // Dual-language Bible: the English line for this verse (if loaded and
        // this paragraph is a numbered verse). Display-only; the audio and word
        // highlighting stay Russian, since the aligner only tokenizes Cyrillic.
        var bibleEnLine = null, bibleHeadingLine = null, bibleEnNum = null;
        if (bibleEn || bibleHeadings) {
          // Section headings ("Сотворение мира") and the chapter title
          // ("Глава 1") live inside <title>/<subtitle><p>..</p></title>; the
          // verse-splitter merges them into a fake verse ("1 Сотворение мира"),
          // and mid-chapter headings appear as bare paragraphs ("Каин и Авель").
          // Strip an optional leading verse number and see if what's left is a
          // known section heading — if so, show its English translation instead
          // of treating it as scripture.
          var headKey = paraText.replace(/^\s*\d+\s+/, "").trim();
          if (bibleHeadings && bibleHeadings[headKey]) {
            bibleHeadingLine = bibleHeadings[headKey];
          } else if (bibleEn) {
            var vno = (paraText.match(/^\s*(\d+)/) || [])[1];
            if (vno && bibleEn[vno]) {
              // Fallback for any heading artifact not in the headings map: the
              // real verse with a given number always comes AFTER its heading,
              // so only attach English to the LAST paragraph carrying that number.
              var isLastForNum = true;
              for (var pj = pi + 1; pj < paraArr.length; pj++) {
                var pjt = paraArr[pj].para.map(function(t){ return t.text; }).join("");
                if ((pjt.match(/^\s*(\d+)/) || [])[1] === vno) { isLastForNum = false; break; }
              }
              if (isLastForNum) { bibleEnLine = bibleEn[vno]; bibleEnNum = vno; }
            }
          }
        }

        // Dual-language prose: English for this paragraph, by chapter index.
        var proseEnLine = null;
        if (proseEn && !bibleEnLine && !bibleHeadingLine) {
          proseEnLine = proseEn[String(entry.chIdx)] || null;
        }

        var isTight = !!(curChapter && curChapter.tightIdx && curChapter.tightIdx.indexOf(entry.chIdx) !== -1);
        var pMargin = {marginBottom: singlePageMode ? "0.35em"
          : (bookMeta && bookMeta.filename && bookMeta.filename.indexOf("негин") !== -1 ? "0.1em"
          : (isTight ? "0.15em" : "1.2em"))};
        var ruBody = (function(){
              // If this paragraph is a play line, replace the punctuation between name and dialogue with an em-dash.
              if (speakerNameEnd > -1) {
                var elems = [];
                for (var i = 0; i < para.length; i++) {
                  var tk = para[i];
                  var hl = tk.isRu && tk.start === activeStart;
                  var inName = tk.end <= speakerNameEnd;
                  var inAttrib = tk.end <= attribEnd;

                  // Skip the original separator (.:—) and the whitespace right after.
                  if (inAttrib && !inName) continue;

                  if (tk.isRu) {
                    var clickPlay;
                    if (inName) {
                      clickPlay = undefined;
                    } else if (noAIMode) {
                      // No AI: nothing to define, so keep the direct jump.
                      clickPlay = (function(pos){ return function(e){ e.stopPropagation(); jumpTTS(pos); }; })(tk.start);
                    } else {
                      clickPlay = (function(w, pos){ return function(e){ defWord(w, e, pos); }; })(tk.text, tk.start);
                    }
                    elems.push(
                      <span key={i}
                        className={"rw" + (hl ? " rwhl" : "") + (inName ? " play-speaker" : "")}
                        data-rw-start={tk.start}
                        onClick={clickPlay}
                        title={inName ? "" : (noAIMode ? "Click to read from here" : "Click for a definition")}>{tk.text}</span>
                    );
                    // Just after the speaker name finishes, insert the em-dash separator.
                    if (inName && (i+1 >= para.length || para[i+1].end > speakerNameEnd)) {
                      elems.push(<span key={"d"+i} className="play-dash">— </span>);
                    }
                  } else {
                    var verseNumMatch2 = tk.text.match(/^(\d+)(\s*)$/);
                  if (verseNumMatch2 && bookMeta && bookMeta.filename && bookMeta.filename.indexOf("Библии") !== -1) {
                    elems.push(<span key={i}><span style={{fontSize:"0.7em",fontWeight:700,color:"#c4955a",verticalAlign:"super",lineHeight:1,marginRight:"2px",fontFamily:"sans-serif"}}>{verseNumMatch2[1]}</span>{verseNumMatch2[2]}</span>);
                  } else {
                    elems.push(<span key={i}>{tk.text.replace(/\n/g, " ")}</span>);
                  }
                  }
                }
                return elems;
              }
              // Regular paragraph rendering.
              return para.map(function(tk, i) {
                var hl = tk.isRu && tk.start === activeStart;
                if (tk.isRu) {
                  var clickReg = noAIMode
                    ? (function(pos){ return function(e){ e.stopPropagation(); jumpTTS(pos); }; })(tk.start)
                    : (function(w, pos){ return function(e){ defWord(w, e, pos); }; })(tk.text, tk.start);
                  return (
                    <span key={i}
                      className={"rw" + (hl ? " rwhl" : "")}
                      data-rw-start={tk.start}
                      onClick={clickReg}
                      title={noAIMode ? "Click to read from here" : "Click for a definition"}>{tk.text}</span>
                  );
                }
                // Bible verse numbers: token is just a number (e.g. "1", "23")
                // followed by a space — render as styled verse number
                var verseNumMatch = tk.text.match(/^(\d+)(\s*)$/);
                // On a section-heading paragraph the leading number is a parsing
                // artifact (the chapter-title number merged in) — drop it so the
                // heading reads cleanly ("Сотворение мира", not "1 Сотворение мира").
                if (verseNumMatch && bibleHeadingLine) { return null; }
                if (verseNumMatch && bookMeta && bookMeta.filename && bookMeta.filename.indexOf("Библии") !== -1) {
                  return (
                    <span key={i}>
                      <span style={{
                        fontSize:"0.7em", fontWeight:700, color:"#c4955a",
                        verticalAlign:"super", lineHeight:1, marginRight:"2px",
                        fontFamily:"sans-serif", letterSpacing:"0.02em"
                      }}>{verseNumMatch[1]}</span>
                      {verseNumMatch[2]}
                    </span>
                  );
                }
                return <span key={i}>{tk.text.replace(/\n/g, " ")}</span>;
              });
            })();
        // Dual-language: one grid row per paragraph — RU cell in the left
        // column, EN cell in the right — so the two columns stay vertically
        // lined up however tall either side runs. The empty-EN cell keeps the
        // grid's two-cells-per-row rhythm intact.
        if (dualActive) {
          var enLine = bibleHeadingLine || bibleEnLine || proseEnLine;
          // Verse books (Онегин) carry English per STANZA, keyed to the
          // stanza's first line: that EN cell spans down to the next
          // EN-bearing row so the Russian lines keep their own rhythm while
          // the stanza translation sits beside the whole stanza. Prose books
          // have EN on (nearly) every row, so spans collapse to 1. Rows are
          // placed explicitly to keep the two columns deterministic.
          var enSpan = 1, emitEn = true;
          if (proseEn && !bibleEn) {
            if (proseEnLine) {
              for (var q2 = pi + 1; q2 < paraArr.length; q2++) {
                if (proseEn[String(paraArr[q2].chIdx)]) break;
                enSpan++;
              }
            } else {
              emitEn = false;   // covered by a previous spanning EN cell
            }
          }
          // Bible: repeat the verse number at the head of the English cell,
          // styled exactly like the Russian column's, so a reader scanning
          // across sees the same numeral on both sides of the split.
          var enContent = enLine || "\u00a0";
          if (bibleEnNum && enLine) {
            enContent = [
              <span key="vno" className="bible-en-vno">{bibleEnNum}</span>,
              <span key="txt">{enLine}</span>
            ];
          }
          var dualCells = [
            <p key={"ru" + pi} className="dual-ru"
               style={Object.assign({gridColumn: 1, gridRow: String(pi + 1)}, pMargin)}>{ruBody}</p>
          ];
          if (emitEn) {
            dualCells.push(
              <p key={"en" + pi} className={"dual-en" + (bibleHeadingLine ? " dual-en-heading" : "")}
                 style={Object.assign({gridColumn: 2, gridRow: (pi + 1) + (enSpan > 1 ? " / span " + enSpan : "")}, pMargin)}>{enContent}</p>
            );
          }
          return dualCells;
        }
        return (
          <p key={pi} style={pMargin}>
            {ruBody}
          </p>
        );
      });
    if (dualActive) {
      // Horizontal slide viewport: full-width RU pane on screen, EN pane one
      // swipe / shift-scroll to the right, snap points at each pane edge.
      return (
        <div className="dual-outer">
          <div className="dual-hint">⇄ English</div>
          {bookMeta && bookMeta.translationNote && (
            <div className="pmt tnote">{bookMeta.translationNote}</div>
          )}
          <div className="dual-scroll" ref={dualRef} onScroll={onDualScroll}>
            <div className="dual-grid">{litRendered}</div>
          </div>
          <button
            className={"dual-toggle" + (dualPane === 1 ? " on" : "")}
            onClick={toggleDual}
            aria-label={dualPane === 0 ? "Show the English translation" : "Back to the Russian text"}
            title={dualPane === 0 ? "Show English" : "Back to Russian"}
          >
            {dualPane === 0 ? "EN →" : "← RU"}
          </button>
        </div>
      );
    }
    return litRendered;
  };

  // Scroll the pane rather than moving it: the container keeps its scroll-snap,
  // so swipe and shift-wheel keep working exactly as before and this is just a
  // third way to drive the same thing.
  var toggleDual = function() {
    var el = dualRef.current;
    if (!el) return;
    var to = dualPane === 0 ? el.clientWidth : 0;
    try { el.scrollTo({ left: to, behavior: "smooth" }); }
    catch (e) { el.scrollLeft = to; }          // older browsers: jump, don't fail
  };

  // Keep the label honest when the reader swipes or shift-scrolls by hand.
  var onDualScroll = function(e) {
    var el = e.currentTarget;
    if (!el || !el.clientWidth) return;
    var pane = el.scrollLeft > el.clientWidth / 2 ? 1 : 0;
    setDualPane(function(prev){ return prev === pane ? prev : pane; });
  };

  // A new page always opens on the Russian side.
  useEffect(function(){ setDualPane(0); }, [cidx, pidx]);

  var renderBubble = function(text) {
    // Diagnostic: log the raw AI message so we can verify whether footnotes
    // are actually being produced. Visible in browser console (F12).
    if (text && text.indexOf("📝") !== -1) {
      console.log("[chat] response contains 📝 — note count:", (text.match(/📝/g) || []).length);
    } else if (text) {
      console.log("[chat] response — NO 📝 found. First 200 chars:", text.slice(0, 200));
    }
    try {
      return text.split("\n").map(function(line, li) {
        var t = line.trim();
        // Detect English footnote / tip lines FIRST (before title check, which
        // would otherwise match bolded notes like **📝 NOTE: x** and steal them).
        // Be forgiving about formatting: strip leading/trailing `*` (bold) and
        // optional label prefix (TIP / NOTE) and optional separator (: - —).
        var stripped = t.replace(/^\*+\s*/, "").replace(/\s*\*+$/, "");
        if (stripped.indexOf("📝") === 0) {
          var noteText = stripped.replace(/^📝\s*(?:TIP|NOTE|Note|note|Tip|tip)?\s*[:\-—]?\s*/i, "").trim();
          if (noteText) return <div key={li} className="tipline">📝 {noteText}</div>;
        }
        var trm = t.match(/^\*{1,2}([^*]+)\*{1,2}$/);
        if (trm && !/[а-яёА-ЯЁ]{3,}/.test(trm[1])) return <div key={li} className="tline">{trm[1]}</div>;
        if (t.startsWith("❓")) return <div key={li} className="qline">{t}</div>;
        var toks = []; var rem = line; var ki = 0;
        while (rem.length > 0) {
          var bm = rem.match(/^\*\*([^*\n(]{1,40})\(([^)]{1,60})\)\*\*/);
          if (bm) {
            var bmRu = bm[1].trim();
            toks.push(<strong key={ki++} className="vw rw" onClick={(function(w){ return function(e){ defWord(w, e); }; })(bmRu)}>{bmRu}</strong>);
            rem = rem.slice(bm[0].length);
            continue;
          }
          if (rem.startsWith("**")) { rem=rem.slice(2); continue; }
          var cm = rem.match(/^\[([^\]]{1,60})\]/);
          if (cm) { toks.push(<span key={ki++} className="corr">[{cm[1]}]</span>); rem=rem.slice(cm[0].length); continue; }
          var rw = rem.match(/^[а-яёА-ЯЁ]+/);
          if (rw) {
            var rwWord = rw[0];
            toks.push(<span key={ki++} className="rw" onClick={(function(w){ return function(e){ defWord(w, e); }; })(rwWord)}>{rwWord}</span>);
            rem = rem.slice(rwWord.length);
            continue;
          }
          toks.push(<span key={ki++}>{rem[0]}</span>); rem=rem.slice(1);
        }
        return <div key={li} className="mline">{toks}</div>;
      });
    } catch(err) { return <div>{text}</div>; }
  };

    // Voice picker panel — extracted into a helper so we can drop it into BOTH
  // the reading view (above the book text) and the chat view (above the input
  // bar). Same state (showVP, voice, allVoices) drives both call sites, so
  // picking a voice anywhere updates the entire app.
  var renderVoicePicker = function() {
    // Picking a robot voice, and previewing it aloud, both go with the
    // feature they configure.
    if (!TTS_ENABLED) return null;
    if (!showVP) return null;
    return (
      <div className="vpanel" style={{maxHeight: diagLogs.length > 0 ? 380 : 180}}>
        <div className="vphdr" style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8}}>
          <span>Choose a Russian voice</span>
          <div style={{display:"flex",gap:6}}>
            {diagLogs.length > 0 && <button className="ttsbtn" style={{height:22,fontSize:11}} onClick={copyDiagLogs}>📋 Copy log</button>}
            <button className="ttsbtn" style={{height:22,fontSize:11}} onClick={function(){
              // List every Russian voice the platform exposes, with full URI +
              // localService flag — lets us see if Enhanced/Siri variants are
              // present in JS (vs. only visible to native iOS apps).
              var lines = ["=== RUSSIAN VOICE INSPECTOR ===",
                "Total voices: " + allVoices.length];
              var ruVoices = allVoices.filter(function(v){ return v.lang && v.lang.toLowerCase().startsWith("ru"); });
              lines.push("Russian voices (lang ru-*): " + ruVoices.length);
              ruVoices.forEach(function(v, i){
                lines.push("[" + (i+1) + "] name=\"" + v.name + "\"  lang=" + v.lang + "  local=" + v.localService + "  default=" + v.default);
                lines.push("    voiceURI=" + (v.voiceURI || "(none)"));
              });
              if (ruVoices.length === 0) {
                lines.push("(no voices with lang ru-* — iOS Safari may not expose installed Russian voices to JavaScript)");
              }
              lines.push("=== INSPECTOR COMPLETE ===");
              setDiagLogs(lines);
            }}>🔬 Inspect</button>
            <button className="ttsbtn" style={{height:22,fontSize:11}} onClick={runDiagnostics}>🩺 Diagnose</button>
          </div>
        </div>
        {diagLogs.length > 0 && (
          <div style={{maxHeight:180,overflowY:"auto",padding:"6px 28px",fontFamily:"monospace",fontSize:11,color:"#d8d8d8",background:"#0a0908",borderBottom:"1px solid rgba(210,197,175,.06)",lineHeight:1.5}}>
            {diagLogs.map(function(line,i){
              var color = line.indexOf("onerror") >= 0 || line.indexOf("THREW") >= 0 ? "#c87a6806a"
                       : line.indexOf("onstart") >= 0 ? "#82a882"
                       : line.indexOf("===") >= 0 ? "#c8a276" : "rgba(210,197,175,.7)";
              return <div key={i} style={{color:color,whiteSpace:"pre-wrap",wordBreak:"break-all"}}>{line}</div>;
            })}
          </div>
        )}
        <div className="vplist">
          {allVoices.length===0 && <div className="vpem">No voices found. Install a Russian voice in system settings.</div>}
          {allVoices.length>0 && allVoices.filter(function(v){ return !!(v.lang && v.lang.toLowerCase().startsWith("ru")); }).length===0 && <div className="vpem">No Russian voices on this device.<br/>In Microsoft Edge you'll see Russian neural voices automatically — try opening the app in Edge. Or install a Russian voice in your system Speech settings.</div>}
          {(function() {
            // Strict: ONLY voices whose lang code starts with "ru" (ru-RU, ru, etc.).
            // We had a name-based fallback that was leaking unrelated voices on iOS
            // (any voice with Cyrillic characters in its descriptor was matching);
            // ditching it. If a voice doesn't claim ru-* it isn't useful for Russian.
            var isRu = function(v) {
              return !!(v.lang && v.lang.toLowerCase().startsWith("ru"));
            };
            var isMsNatural = function(v) {
              return /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
            };
            var isGoogle = function(v) { return /google/i.test(v.name); };
            // iOS / macOS Enhanced and Premium voices — higher-quality local
            // voices that the user can download via Settings → Accessibility →
            // Spoken Content → Voices → Russian. Detect via voiceURI which
            // contains "enhanced" or "premium" for these tiers on iOS.
            var isEnhanced = function(v) {
              var uri = (v.voiceURI || "").toLowerCase();
              return /enhanced|premium/i.test(v.name) || uri.indexOf("enhanced") !== -1 || uri.indexOf("premium") !== -1;
            };
            // Apple Siri voices — top-tier neural voices on iOS 16+/macOS 13+.
            var isSiri = function(v) {
              var uri = (v.voiceURI || "").toLowerCase();
              return /\bsiri\b/i.test(v.name) || uri.indexOf("siri") !== -1;
            };
            var tier = function(v) {
              if (v._cloud) return 0;  // Cloud voices first — highest practical quality, work everywhere
              if (v.localService && (isSiri(v) || isEnhanced(v))) return 1;
              if (v.localService) return 2;
              if (isMsNatural(v) || isGoogle(v)) return 3;
              return 4;
            };
            var byQuality = function(a, b) { return tier(a) - tier(b); };
            var ruVoices = allVoices.filter(isRu).slice().sort(byQuality);
            return ruVoices;
          })()
            .map(function(v,i){
              var ru = true;  // We've already filtered — all voices in the list are Russian.
              var network = !v.localService;
              // Microsoft Edge's Online Natural neural voices AND Chrome's Google network
              // voices are both high-quality neural — flag them positively, not as warnings.
              var isMsNatural = /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
              var isGoogle = /google/i.test(v.name);
              var isHighQualityNetwork = isMsNatural || isGoogle;
              // iOS / macOS quality markers — surface these prominently.
              var isEnhanced = /\b(enhanced|premium)\b/i.test(v.name);
              var isSiri = /\bsiri\b/i.test(v.name) || /com\.apple\.ttsbundle\.siri/i.test(v.voiceURI || "");
              var isCloud = !!v._cloud;
              var labelText, labelColor, rowOpacity;
              if (isCloud) {
                labelText = " · Azure Cloud";
                labelColor = "#c4955a";
                rowOpacity = null;
              } else if (isSiri && !network) {
                labelText = " · Siri ★★★";
                labelColor = "#c4955a";
                rowOpacity = null;
              } else if (isEnhanced && !network) {
                labelText = " · Enhanced ★★";
                labelColor = "#c4955a";
                rowOpacity = null;
              } else if (!network) {
                labelText = " · local ✓";
                labelColor = null;
                rowOpacity = null;
              } else if (isHighQualityNetwork) {
                labelText = " · neural ★";
                labelColor = "#c4955a";
                rowOpacity = null;
              } else {
                labelText = " · network ⚠";
                labelColor = "#9d4630";
                rowOpacity = 0.55;
              }
              return (
                <button key={i} className={"vprow"+(voice&&voice.name===v.name?" sel":"")}
                  style={rowOpacity ? {opacity: rowOpacity} : null}
                  onClick={function(){
                    console.log("[picker] clicked voice:", {
                      name: v.name,
                      _cloud: !!v._cloud,
                      _azureVoice: v._azureVoice || "(n/a)",
                      voiceURI: v.voiceURI,
                    });
                    // Record the explicit choice so the async voiceschanged
                    // handler stops overriding it, and persist for next session.
                    userPickedRef.current = true;
                    try { localStorage.setItem(GVT_VOICE_KEY, v.voiceURI || ""); } catch(e) {}
                    // Also immediately push to ref so speakMsg sees the new
                    // value even before React commits the state update (defends
                    // against rapid 🎙pick → 🔊click sequences).
                    voiceRef.current = v;
                    setVoice(v); stopTTS(); setTtsErr("");
                    // Speak a short test phrase so the user immediately knows if the voice works.
                    setTimeout(function() {
                      // Local voice path — original speechSynthesis test
                      var u = new SpeechSynthesisUtterance("Привет! Я твой голос.");
                      u.lang = "ru-RU"; u.voice = v; u.rate = 0.9;
                      u.onerror = function(e) {
                        var err = (e && e.error) || "unknown";
                        if (err !== "interrupted" && err !== "canceled") {
                          var hint = (network && !isHighQualityNetwork) ? " — pick a voice marked « local » or « neural ★ » instead" : "";
                          setTtsErr("Voice « " + v.name + " » failed: " + err + hint);
                        }
                      };
                      try { window.speechSynthesis.speak(u); }
                      catch(ex) { setTtsErr("speak() threw: " + (ex.message || ex)); }
                    }, 80);
                  }}>
                  <span className={"vpn"+(ru?" vpnru":"")}>{v.name}</span>
                  <span className="vpl" style={labelColor ? {color:labelColor} : null}>{v.lang}{labelText}</span>
                </button>
              );
          })}
        </div>
      </div>
    );
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,400&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        html,body{height:100%;background:#f5f0e8;color:#000;font-family:'Crimson Pro',serif;overflow:hidden}
        /* Lock the app to the viewport: full width, viewport height. Inner panels
           (book text, chat messages) scroll within their own bounds — the page
           itself never scrolls. Uses 100dvh (dynamic viewport height) so mobile
           browsers with collapsing chrome behave correctly; falls back to 100vh
           for older browsers. */
        .app{height:100vh;height:100dvh;background:#f5f0e8;display:flex;flex-direction:column;width:100%;overflow:hidden}
        .app::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:none}
        .hdr{padding:16px 28px 12px;border-bottom:1px solid rgba(42,31,20,.1);display:flex;align-items:center;justify-content:space-between;gap:16px;position:relative;z-index:10}
        .logo{display:flex;align-items:baseline;gap:10px}
        .lru{font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#c4955a}
        .lsub{font-size:11px;color:rgba(42,31,20,.35);letter-spacing:2.5px;text-transform:uppercase}
        .tbadge{background:rgba(196,149,90,.1);border:1px solid rgba(196,149,90,.25);color:#c4955a;padding:6px 14px;border-radius:20px;font-size:13px;cursor:pointer;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        /* Library browser: search + card-grid of preset & uploaded books.
           Replaces the prior <select> dropdown on the Read launch screen. */
        .lib-search{width:100%;padding:12px 16px;font-size:16px;background:rgba(42,31,20,.05);border:1px solid rgba(42,31,20,.18);border-radius:10px;color:#000;font-family:'Crimson Pro',serif;margin-bottom:20px;box-sizing:border-box;letter-spacing:.01em}
        .lib-search:focus{outline:none;border-color:rgba(196,149,90,.5);background:rgba(42,31,20,.08)}
        .lib-search::placeholder{color:rgba(42,31,20,.4)}
        .lib-section{margin-bottom:22px}
        .lib-section-hdr{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:rgba(42,31,20,.55);margin-bottom:10px;padding-left:4px;font-weight:600}
        .lib-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
        .lib-card{padding:14px;border-radius:10px;background:rgba(42,31,20,.04);border:1px solid rgba(42,31,20,.1);cursor:pointer;transition:all .15s;position:relative;display:flex;flex-direction:column;gap:4px}
        .lib-card:hover{background:rgba(42,31,20,.08);border-color:rgba(196,149,90,.3);transform:translateY(-1px)}
        .lib-card-title{font-family:'Playfair Display',serif;font-size:15px;color:#c4955a;line-height:1.3;margin-bottom:8px}
        .lib-card-author{font-size:12px;color:rgba(42,31,20,.6);font-style:italic;margin-bottom:6px}
        .lib-card-meta{display:flex;align-items:center;justify-content:space-between;font-size:11px;color:rgba(42,31,20,.4);margin-top:auto;padding-top:4px}
        .lib-card-cat{background:rgba(196,149,90,.1);border:1px solid rgba(196,149,90,.25);color:#c4955a;padding:2px 8px;border-radius:10px;font-size:10px;letter-spacing:.5px;text-transform:uppercase;font-weight:600}
        .lib-card-remove{background:transparent;border:none;color:rgba(42,31,20,.35);font-size:18px;cursor:pointer;padding:0 4px;line-height:1}
        .lib-card-remove:hover{color:#9d4630}
        /* Loading state: dim the card content and overlay a centered spinner.
           Disabled state (a different card is loading): grey out + ignore clicks. */
        .lib-card.is-loading{pointer-events:none;border-color:rgba(196,149,90,.45);background:rgba(196,149,90,.06)}
        .lib-card.is-loading > *:not(.lib-card-loader){opacity:.3}
        .lib-card.is-disabled{pointer-events:none;opacity:.45}
        .lib-card-loader{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:6px;background:rgba(35,32,26,.65);border-radius:10px;backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px);z-index:1}
        .lib-card-loader span{font-size:13px;color:#c4955a;font-family:'Crimson Pro',serif;font-style:italic}
        /* Persistent CEFR level selector pinned in the header. Compact pill style
           that matches the Topic badge. The label sits to the left of the dropdown. */
        .level-wrap{display:flex;align-items:center;gap:6px}
        .level-lbl{font-size:10px;color:rgba(42,31,20,.4);text-transform:uppercase;letter-spacing:1.5px;font-weight:600}
        .level-pill{background:rgba(196,149,90,.1);border:1px solid rgba(196,149,90,.25);color:#c4955a;padding:5px 10px;border-radius:14px;font-size:13px;font-family:'Crimson Pro',serif;cursor:pointer;width:auto;outline:none}
        .level-pill:hover{background:rgba(196,149,90,.18)}
        .level-pill option{background:#ede8dd}
        @media(max-width:600px){.level-lbl{display:none}.level-pill{padding:4px 8px;font-size:12px}}
        .tbadge:hover{background:rgba(196,149,90,.18)}
        .tabs{display:flex;border-bottom:1px solid rgba(42,31,20,.1);padding:0 28px;position:relative;z-index:10}
        .tab{padding:11px 20px;background:none;border:none;color:#000;font-family:'Crimson Pro',serif;font-size:14px;cursor:pointer;border-bottom:2px solid transparent;position:relative;top:1px;transition:color .2s}
        .tab.on{color:#000;border-bottom-color:#c4955a;font-weight:600}
        .tab:hover:not(.on){color:#c4955a}
        .bdg{background:#c4955a;color:#fff;font-size:10px;border-radius:10px;padding:1px 5px;margin-left:4px;vertical-align:middle}
        .bdg.g{background:#5a8556}
        .main{flex:1;display:flex;flex-direction:column;position:relative;z-index:1;min-height:0}
        .ss{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:48px 28px;text-align:center;gap:22px;overflow-y:auto;min-height:0}
        .sico{font-size:54px;line-height:1}
        .sti{font-family:'Playfair Display',serif;font-size:30px;color:#000;font-weight:400}
        .sde{color:rgba(42,31,20,.5);font-size:16px;max-width:500px;line-height:1.6}
        .tsel{width:100%;max-width:500px;display:flex;flex-direction:column;gap:12px;text-align:left}
        .slbl{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:rgba(42,31,20,.35)}
        select,input[type="text"],textarea{width:100%;background:rgba(42,31,20,.06);border:1px solid rgba(42,31,20,.16);color:#000;padding:12px 16px;border-radius:10px;font-family:'Crimson Pro',serif;font-size:16px;outline:none;transition:border-color .2s}
        select{appearance:none;cursor:pointer} select option{background:#ede8dd}
        ::placeholder{color:rgba(42,31,20,.28)}
        input:focus,textarea:focus,select:focus{border-color:rgba(196,149,90,.5)}
        .btn-p{background:linear-gradient(135deg,#c4955a,#a87a42);color:#fff;border:none;padding:14px 32px;border-radius:10px;font-family:'Playfair Display',serif;font-size:17px;cursor:pointer;width:100%;box-shadow:0 4px 20px rgba(196,149,90,.3);transition:opacity .2s}
        .btn-p:hover:not(:disabled){opacity:.88} .btn-p:disabled{opacity:.4;cursor:default}
        .btn-g{background:rgba(42,31,20,.07);color:rgba(42,31,20,.6);border:1px solid rgba(42,31,20,.15);padding:12px 24px;border-radius:10px;font-family:'Crimson Pro',serif;font-size:15px;cursor:pointer;width:100%;transition:background .2s}
        .btn-g:hover{background:rgba(42,31,20,.12)}
        .chat-wrap{flex:1;display:flex;flex-direction:column;min-height:0}
        .msgs{flex:1;overflow-y:auto;padding:20px 28px 8px;display:flex;flex-direction:column;gap:12px}
        .msg{display:flex;flex-direction:column;gap:6px}
        .msg.user{align-items:flex-end} .msg.ai{align-items:flex-start}
        .bub{max-width:72%;padding:14px 18px;font-size:16px;line-height:1.7}
        .abub{background:rgba(42,31,20,.065);border:1px solid rgba(42,31,20,.11);border-radius:4px 16px 16px 16px}
        .ubub{background:rgba(196,149,90,.2);border:1px solid rgba(196,149,90,.28);border-radius:16px 4px 16px 16px}
        .mline{display:block;margin-bottom:3px;line-height:1.7}
        .tline{color:rgba(42,31,20,.5);font-size:14px;margin-top:6px;display:block;line-height:1.65;padding-top:5px;border-top:1px solid rgba(42,31,20,.08)}
        .tipline{color:rgba(128,168,128,.85);font-size:13.5px;border-left:2px solid rgba(128,168,128,.35);padding-left:8px;margin-top:7px;display:block;line-height:1.5}
        .qline{color:#c4955a;font-size:15px;margin-top:10px;display:block;line-height:1.6;padding:8px 12px;background:rgba(196,149,90,.07);border-radius:8px;border-left:2px solid rgba(196,149,90,.4)}
        .vw{color:#c4955a} .corr{color:#2f4a6b}
        .vw.rw{color:#c4955a;border-bottom:1px dotted rgba(196,149,90,.5)}
        .vw.rw:hover{color:#000;border-bottom-color:#c4955a;background:rgba(196,149,90,.18);border-radius:2px}
        .rw{cursor:pointer;border-bottom:1px dotted rgba(42,31,20,.18);transition:color .15s,background .12s}
        .rw:hover{color:#c4955a;border-bottom-color:#c4955a}
        .rwhl{background:rgba(196,149,90,.18);color:#000;border-bottom-color:#c4955a;border-radius:3px;padding:1px 2px}
        /* Two-choice bubble on a clicked word: define it, or play from it. */
        /* Above the floating audio bar (z-index 100) so a word near the
           bottom of the page doesn't open its menu underneath the player,
           and below the definition popup (200/201) it hands off to. */
        /* Dual-language Bible: English translation shown under each Russian verse */
        .bible-en{display:block;margin-top:3px;color:rgba(42,31,20,.5);font-size:0.9em;font-style:italic;line-height:1.5;letter-spacing:.005em}
        .bible-heading-en{font-style:normal;font-weight:600;color:rgba(42,31,20,.62);font-size:0.95em;letter-spacing:.01em}
        /* Side-by-side dual language: the Russian column takes the full reader
           width; the English column sits just off-screen to the right. The
           block scrolls horizontally — swipe on mobile, shift-wheel / drag /
           thin scrollbar on desktop — with snap points at each column, and one
           grid row per paragraph keeps RU and EN vertically lined up. */
        .dual-hint{text-align:right;font-family:'Inter',sans-serif;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:rgba(42,31,20,.38);margin:0 0 8px;user-select:none}
        .dual-scroll{overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:thin;padding-bottom:4px}
        .dual-grid{display:grid;grid-template-columns:100% 100%;column-gap:36px;align-items:start}
        .dual-grid > p{scroll-snap-align:start}
        /* Pinned to the viewport, not to the end of the scroll container, so it
           is reachable from anywhere in a long chapter. */
        .tnote{margin:0 0 10px;max-width:70ch}
        /* The closed control IS stylable, unlike its options. Full width and a
           16px minimum, because anything smaller makes iOS zoom the page on
           focus and leaves it zoomed. */
        .quickpick{width:100%;box-sizing:border-box;font-size:15px;padding:10px 12px;
                   font-family:'Crimson Pro',serif;border-radius:8px;
                   border:1px solid rgba(42,31,20,.18);background:rgba(42,31,20,.05);color:#000}
        /* Style the list too, the way .level-pill does. A select whose control
           is painted but whose options are not falls back to the system palette
           the moment it opens, which reads as the styling having vanished. */
        .quickpick option{background:#ede8dd;color:#2a1f14;padding:4px 0}
        .quickpick optgroup{background:#e4ddcf;color:#8a6a35;font-weight:600;font-style:normal}
        .quickpick:hover{background:rgba(42,31,20,.08)}
        .quickpick:focus{outline:none;border-color:rgba(196,149,90,.5)}
        @media (max-width:700px){.quickpick{font-size:16px;padding:12px}}
        .dual-toggle{position:fixed;right:14px;top:50%;transform:translateY(-50%);z-index:40;
          background:rgba(255,252,246,.94);border:1px solid rgba(42,31,20,.18);color:rgba(42,31,20,.7);
          font-family:'Inter',sans-serif;font-size:12px;letter-spacing:.06em;font-weight:600;
          padding:9px 11px;border-radius:999px;cursor:pointer;box-shadow:0 2px 10px rgba(42,31,20,.13);
          transition:background .15s,color .15s,border-color .15s}
        .dual-toggle:hover{background:#fff;color:rgba(42,31,20,.95);border-color:rgba(42,31,20,.34)}
        .dual-toggle:focus-visible{outline:2px solid #a06e14;outline-offset:2px}
        .dual-toggle.on{background:#a06e14;border-color:#a06e14;color:#fff}
        @media (max-width:640px){.dual-toggle{right:10px;padding:8px 10px;font-size:11px}}
        .dual-en{color:rgba(42,31,20,.72)}
        .bible-en-vno{font-size:0.7em;font-weight:700;color:#c4955a;vertical-align:super;line-height:1;margin-right:2px;font-family:'Inter',sans-serif;letter-spacing:.02em}
        .dual-en-heading{font-weight:600;color:rgba(42,31,20,.62)}
        /* Words inside the sentence currently being read aloud. Applied at
           the start of each sentence's playback via direct DOM manipulation
           (no React re-render). Uses a soft warm tint so a whole sentence's
           worth of words reads as a single coherent block, not as flashing
           individual highlights. */
        .rw-reading{color:#8b4513;border-bottom:2px solid #c4955a;transition:color .1s ease,border-color .1s ease}
        .acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:2px}
        .spk{padding:5px 12px;border-radius:20px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;background:rgba(42,31,20,.07);border:1px solid rgba(42,31,20,.2);color:rgba(42,31,20,.7);transition:all .15s}
        .spk:hover{background:rgba(42,31,20,.14)} .spkon{background:rgba(196,149,90,.18);border-color:rgba(196,149,90,.35);color:#e08a78}
        .chip{padding:5px 12px;border-radius:20px;font-size:12px;cursor:pointer;font-family:'Crimson Pro',serif;border:1px solid;transition:background .15s}
        .vc{background:rgba(196,149,90,.09);border-color:rgba(196,149,90,.28);color:#c4955a} .vc:hover:not(:disabled){background:rgba(196,149,90,.18)}
        .tc{background:rgba(128,168,128,.08);border-color:rgba(128,168,128,.25);color:rgba(128,168,128,.9)} .tc:hover:not(:disabled){background:rgba(128,168,128,.15)}
        .chip:disabled,.chipsaved{cursor:default;opacity:.7}
        .chipsaved{background:rgba(128,168,128,.15)!important;border-color:rgba(128,168,128,.4)!important;color:rgba(150,190,150,.95)!important}
        .typing{display:flex;align-items:center;gap:5px;padding:12px 16px;background:rgba(42,31,20,.065);border:1px solid rgba(42,31,20,.11);border-radius:4px 16px 16px 16px;width:fit-content}
        .dot{width:6px;height:6px;background:rgba(42,31,20,.4);border-radius:50%;animation:bounce 1.2s ease-in-out infinite}
        .dot:nth-child(2){animation-delay:.2s} .dot:nth-child(3){animation-delay:.4s}
        @keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-5px);opacity:1}}
        .ibar{padding:12px 28px 16px;border-top:1px solid rgba(42,31,20,.09);display:flex;gap:10px;align-items:flex-end;background:#f5f0e8;z-index:10}
        .ibar textarea{flex:1;resize:none;min-height:44px;max-height:120px;padding:10px 14px;border-radius:22px;font-size:15px;line-height:1.5}
        .isend{background:linear-gradient(135deg,#c4955a,#a87a42);color:#fff;border:none;width:44px;height:44px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s}
        .isend:hover:not(:disabled){opacity:.85} .isend:disabled{opacity:.35;cursor:default}
        .inew{background:rgba(42,31,20,.06);color:rgba(42,31,20,.5);border:1px solid rgba(42,31,20,.15);padding:0 16px;border-radius:22px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;height:44px;white-space:nowrap;transition:all .15s}
        .inew:hover{background:rgba(42,31,20,.12);color:#000}
        .lit-wrap{flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden}
        .lit-top{display:flex;align-items:center;gap:8px;padding:8px 28px;border-bottom:1px solid rgba(42,31,20,.1);flex-shrink:0;background:#f5f0e8;flex-wrap:wrap}
        .ltab{padding:6px 14px;border-radius:16px;background:none;border:1px solid rgba(42,31,20,.14);color:rgba(42,31,20,.45);font-family:'Crimson Pro',serif;font-size:13px;cursor:pointer;transition:all .15s}
        .ltab.on{background:rgba(196,149,90,.12);border-color:rgba(196,149,90,.3);color:#c4955a}
        .ltab:hover:not(.on){background:rgba(42,31,20,.06)}
        /* Inline page/chapter nav — compact buttons in the top tab row,
           freed from the bottom of the screen so the floating audio bar
           can sit there without blocking navigation. */
        .lit-top-nav{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
        .lnb-inline{padding:5px 11px;border-radius:8px;border:1px solid rgba(42,31,20,.16);background:rgba(42,31,20,.05);color:rgba(42,31,20,.55);font-family:'Crimson Pro',serif;font-size:13px;cursor:pointer;transition:all .15s}
        .lnb-inline:hover:not(:disabled){background:rgba(42,31,20,.1);color:#000}
        .lnb-inline:disabled{opacity:.3;cursor:default}
        .lnb-inline.p{background:linear-gradient(135deg,#c4955a,#a87a42);border-color:transparent;color:#fff}
        .lnb-inline.p:hover:not(:disabled){opacity:.9}
        .lnb-inline.ch{border-color:rgba(196,149,90,.3);background:rgba(196,149,90,.08);color:#c4955a;font-size:12px;padding:5px 9px}
        .lnb-inline.ch:hover:not(:disabled){background:rgba(196,149,90,.18);border-color:rgba(196,149,90,.5)}
        .lbm-inline{border-color:rgba(196,149,90,.25);background:rgba(196,149,90,.07);color:#c4955a}
        .lbm-inline:hover{background:rgba(196,149,90,.15)}
        @media(max-width:780px){
          .lit-top{padding:6px 12px;gap:5px}
          .ltab{padding:5px 10px;font-size:12px}
          .lnb-inline,.lnb-inline.ch{padding:4px 8px;font-size:11px}
          .lprog{display:none}  /* progress hidden on narrow screens — nav is the priority */
        }
        .lprog{margin-left:auto;display:flex;align-items:center;gap:10px}
        .lpct{font-size:12px;color:rgba(42,31,20,.35)}
        .lpbar{width:80px;height:3px;background:rgba(42,31,20,.1);border-radius:2px;overflow:hidden}
        .lpfill{height:100%;background:#c4955a;border-radius:2px;transition:width .3s}
        .ttsbar{display:flex;align-items:center;gap:10px;padding:7px 28px;background:#f0ebe0;border-bottom:1px solid rgba(42,31,20,.08);flex-shrink:0}
        .ttsplay{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#c4955a,#a87a42);border:none;color:#fff;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s}
        .ttsplay:hover{opacity:.85}
        .ttspause{width:32px;height:32px;border-radius:50%;background:rgba(196,149,90,.2);border:1px solid rgba(196,149,90,.4);color:#e08a78;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
        .ttslab{flex:1;font-size:12px;color:rgba(42,31,20,.4);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .ttsbtn{background:none;border:1px solid rgba(42,31,20,.15);color:rgba(42,31,20,.4);height:26px;border-radius:8px;font-size:12px;cursor:pointer;padding:0 10px;transition:all .15s}
        .ttsbtn:hover{background:rgba(42,31,20,.08);color:rgba(42,31,20,.7)}

        /* Floating audio bar (reading mode) — sticky to viewport bottom,
           always visible while reading so pause/skip are one tap away. */
        .faudio{position:fixed;left:0;right:0;bottom:0;height:68px;background:rgba(245,240,232,.96);border-top:1px solid rgba(42,31,20,.18);display:flex;align-items:center;justify-content:center;gap:14px;z-index:100;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);padding:0 22px;box-shadow:0 -4px 18px rgba(42,31,20,.15)}
        .faudio-btn{background:rgba(42,31,20,.08);border:1px solid rgba(42,31,20,.28);color:#000;width:44px;height:44px;border-radius:50%;font-size:17px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background .15s,opacity .15s}
        .faudio-btn:hover{background:rgba(42,31,20,.18)}
        .faudio-btn:disabled{opacity:.35;cursor:not-allowed}
        .faudio-play{background:#c4955a;color:#fff;border-color:#c4955a;width:52px;height:52px;font-size:22px}
        .faudio-play:hover{background:#d4ae7f}
        .faudio-status{color:rgba(42,31,20,.55);font-size:12px;font-family:'Inter',system-ui,sans-serif;margin-left:10px;letter-spacing:.3px;min-width:90px;text-align:left}
        .faudio-narrator{color:#c4955a;font-style:italic}
        .faudio-seek{flex:1;min-width:80px;max-width:280px;accent-color:#c4955a;cursor:pointer;height:4px}
        .faudio-clock{color:rgba(42,31,20,.7);font-size:12px;font-family:'Inter',system-ui,sans-serif;font-variant-numeric:tabular-nums;letter-spacing:.3px;min-width:82px;text-align:right;white-space:nowrap}
        /* 🎧 ↔ 🤖 mode toggle — only renders when an audiobook is available */
        .faudio-mode{background:rgba(42,31,20,.06);border:1px solid rgba(42,31,20,.2);color:rgba(42,31,20,.7);border-radius:50%;width:36px;height:36px;font-size:16px;cursor:pointer;transition:all .15s;display:flex;align-items:center;justify-content:center;flex-shrink:0}
        .faudio-mode:hover{background:rgba(196,149,90,.12);color:#c4955a;border-color:rgba(196,149,90,.4)}
        .faudio-mode.active{background:rgba(196,149,90,.18);color:#c4955a;border-color:#c4955a}
        .faudio-speed{margin-left:auto;background:rgba(42,31,20,.06);border:1px solid rgba(42,31,20,.2);color:rgba(42,31,20,.7);border-radius:14px;padding:6px 12px;font-size:12px;font-family:'Crimson Pro',serif;cursor:pointer;transition:all .15s;letter-spacing:.3px}
        .faudio-speed:hover{background:rgba(196,149,90,.12);color:#c4955a;border-color:rgba(196,149,90,.3)}
        .faudio-speed:disabled{opacity:.35;cursor:not-allowed}
        @media(max-width:600px){
          .faudio{padding:0 12px;gap:10px;height:62px}
          .faudio-btn{width:40px;height:40px;font-size:15px}
          .faudio-play{width:48px;height:48px;font-size:20px}
          .faudio-status{font-size:11px;min-width:0;margin-left:6px}
          .faudio-seek{min-width:60px;max-width:140px}
          .faudio-clock{font-size:11px;min-width:74px}
          .faudio-mode{width:32px;height:32px;font-size:14px}
          .faudio-speed{padding:5px 9px;font-size:11px}
        }
        /* Push reading-mode content up so the floating bar doesn't cover it. */
        .lit-body{padding-bottom:80px}
        /* Grammar reference page (📚 Grammar mode) */
        .gramref{flex:1;display:flex;flex-direction:column;min-height:0}
        .gramref-hdr{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 28px;background:#f0ebe0;border-bottom:1px solid rgba(42,31,20,.08);flex-shrink:0}
        .gramref-body{flex:1;overflow-y:auto;padding:32px 28px 60px;max-width:780px;width:100%;margin:0 auto;line-height:1.55}
        .gramref-body section h2{margin-top:4px}
        .gramref-body section:first-of-type{margin-top:8px}
        .gramref-nav{display:flex;gap:10px;margin-top:32px;padding-top:24px;border-top:1px solid rgba(42,31,20,.08)}
        .gramref-nav .btn-g{font-size:13px;padding:10px 14px;text-align:center}
        @media (max-width:600px){.gramref-body{padding:24px 18px 60px}.gramref-hdr{padding:10px 18px}.gramref-nav{flex-direction:column}}
        .vpanel{background:#f0ebe0;border-bottom:1px solid rgba(42,31,20,.08);max-height:180px;display:flex;flex-direction:column;flex-shrink:0}
        .vphdr{padding:7px 28px 4px;border-bottom:1px solid rgba(42,31,20,.06);font-size:12px;color:rgba(42,31,20,.35)}
        .vplist{overflow-y:auto;padding:4px 28px}
        .vprow{width:100%;background:none;border:none;border-bottom:1px solid rgba(42,31,20,.05);padding:7px 0;display:flex;align-items:center;justify-content:space-between;cursor:pointer;gap:10px;transition:background .15s}
        .vprow:hover,.vprow.sel{background:rgba(196,149,90,.06)}
        .vpn{font-size:14px;color:#000;font-family:'Crimson Pro',serif;text-align:left}
        .vpnru{color:#c4955a} .vpl{font-size:11px;color:rgba(42,31,20,.28)}
        .vpem{font-size:13px;color:rgba(42,31,20,.3);padding:14px 0;text-align:center}
        .lit-body{flex:1;display:flex;min-height:0;overflow:hidden}
        .lit-left{flex:1;overflow-y:auto;padding:24px 28px;border-right:1px solid rgba(42,31,20,.08)}
        /* Book text gets a comfortable reading width even when the column is very
           wide on big monitors — humans don't enjoy reading lines that span
           1000+ pixels. Center the content. */
        .lit-left > *{max-width:760px;margin-left:auto;margin-right:auto}
        .lit-right{width:460px;flex-shrink:0;display:flex;flex-direction:column;min-height:0}
        @media(max-width:900px){
          /* Mobile reading layout: vertical flow, page scrolls.
             - Book text dominates the top — natural height, fully readable
             - Chat panel (messages + input) flows below in document order
             - Nav buttons (Previous / 📌 / Next) sit at the very bottom
             User scrolls DOWN to reach the answer field and the next-page buttons.
             No more 40vh chat panel eating screen space.
             Overrides the desktop "lock-to-viewport" model (overflow:hidden, height:100vh). */
          html, body { overflow: auto; height: auto; }
          .app { height: auto; min-height: 100vh; overflow: visible; }
          .lit-body { flex-direction: column; overflow: visible; flex: none; }
          .lit-left {
            border-right: none;
            border-bottom: 1px solid rgba(42,31,20,.08);
            overflow: visible;
            padding: 20px 18px 28px;
            flex: none;
            /* Reset desktop max-width centering — on mobile, book uses the full viewport width. */
            max-width: none;
          }
          .lit-left > * { max-width: none; margin-left: 0; margin-right: 0; }
          .lit-left.noai { padding-bottom: 20px; }
          .lit-right {
            position: static;
            width: 100%;
            max-width: none;
            margin: 0;
            height: auto;
            z-index: auto;
            background: #f5f0e8;
            border-top: none;
            -webkit-backdrop-filter: none;
            backdrop-filter: none;
            padding-bottom: 0;
            flex: none;
          }
          .lit-msgs {
            max-height: none;
            overflow: visible;
            padding: 16px 18px 8px;
          }
          .lit-ibar {
            flex: none;
            padding: 10px 18px 16px;
          }
          .lit-ibar textarea { min-height: 80px; }
          .lnav {
            position: static;
            width: 100%;
            max-width: none;
            margin: 0;
            z-index: auto;
            border-radius: 0;
            box-shadow: none;
            background: #f5f0e8;
            border-top: 1px solid rgba(42,31,20,.08);
            padding: 12px 18px calc(20px + env(safe-area-inset-bottom));
          }
          .lnav.noai { bottom: auto; }
        }
        .lhdr{font-size:11px;color:rgba(42,31,20,.3);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px}
        .lch-heading{font-family:'Playfair Display',serif;font-size:20px;color:#c4955a;margin-bottom:14px}
        .ltxt{font-size:17.5px;line-height:1.85;color:#000;font-family:'Crimson Pro',serif;word-wrap:break-word;overflow-wrap:break-word;letter-spacing:.005em}
        .play-speaker{color:#c4955a;font-weight:600;letter-spacing:.04em;border-bottom:none !important;cursor:default !important}
        .play-speaker:hover{color:#c4955a !important;background:none !important}
        .play-dash{color:rgba(42,31,20,.45);padding:0 6px;font-weight:300}
        .lit-msgs{flex:0 1 auto;max-height:50%;overflow-y:auto;padding:14px 20px 8px;display:flex;flex-direction:column;gap:10px}
        .lit-ibar{position:relative;padding:10px 20px 14px;border-top:1px solid rgba(42,31,20,.08);background:#f5f0e8;flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
        .lit-ibar textarea{flex:1;width:100%;resize:none;min-height:80px;max-height:none;padding:14px 60px 14px 16px;border-radius:14px;font-size:16px;line-height:1.55}
        .lit-ibar .isend{position:absolute;bottom:22px;right:28px;box-shadow:none;flex-direction:column;gap:6px;padding:10px 28px 12px;border-top:1px solid rgba(42,31,20,.08);flex-shrink:0;background:#f5f0e8}
        .lnav-row{display:flex;gap:8px;justify-content:center;align-items:stretch}
        .lnav-row-sm{margin-top:2px}
        .lnb{flex:1;padding:10px;border-radius:10px;border:1px solid rgba(42,31,20,.14);background:rgba(42,31,20,.05);color:rgba(42,31,20,.55);font-family:'Crimson Pro',serif;font-size:14px;cursor:pointer;transition:all .15s;text-align:center}
        .lnb:hover:not(:disabled){background:rgba(42,31,20,.1);color:#000} .lnb:disabled{opacity:.22;cursor:default}
        .lnb.p{background:linear-gradient(135deg,#9d4630,#82362a);border-color:transparent;color:#fff} .lnb.p:hover{opacity:.9}
        .lbm{padding:10px 14px;border-radius:10px;border:1px solid rgba(196,149,90,.25);background:rgba(196,149,90,.07);color:#c4955a;font-size:15px;cursor:pointer;transition:background .15s}
        .lbm:hover{background:rgba(196,149,90,.15)}
        .lnb-sm{flex:1;padding:7px 12px;border-radius:8px;border:1px solid rgba(196,149,90,.3);background:rgba(196,149,90,.08);color:#c4955a;font-family:'Crimson Pro',serif;font-size:13px;cursor:pointer;transition:all .15s;text-align:center}
        .lnb-sm:hover:not(:disabled){background:rgba(196,149,90,.18);border-color:rgba(196,149,90,.5)}
        .lnb-sm:disabled{opacity:.35;cursor:default}
        .navpanel{flex:1;overflow-y:auto;padding:16px 28px;display:flex;flex-direction:column;gap:8px}
        .lcard{padding:12px 14px;border-radius:10px;background:rgba(42,31,20,.04);border:1px solid rgba(42,31,20,.09);cursor:pointer;transition:all .15s}
        .lcard:hover{background:rgba(42,31,20,.08)} .lcard.cur{border-color:rgba(196,149,90,.4);background:rgba(196,149,90,.07)}
        .lcn{font-size:10px;color:rgba(42,31,20,.28);letter-spacing:1px;margin-bottom:4px}
        .lchead{font-size:14px;color:#c4955a;font-family:'Playfair Display',serif;margin-bottom:3px}
        .lcp{font-size:13px;color:rgba(42,31,20,.55);line-height:1.4}
        .lem{text-align:center;color:rgba(42,31,20,.28);padding:32px;font-size:14px}
        .lsbar{padding:12px 28px;border-bottom:1px solid rgba(42,31,20,.08)}
        .pover{position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.15)}
        .pop{position:fixed;z-index:201;background:#f5f0e8;border:1px solid rgba(196,149,90,.3);border-radius:14px;padding:16px 18px 18px;box-shadow:0 4px 24px rgba(42,31,20,.12);animation:pf .15s ease;max-height:calc(100vh - 32px);overflow-y:auto;overscroll-behavior:contain}
        @keyframes pf{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
        .pcl{position:absolute;top:10px;right:12px;background:none;border:none;color:rgba(42,31,20,.35);font-size:18px;cursor:pointer}
        .pcl:hover{color:rgba(42,31,20,.7)}
        .pw{font-family:'Playfair Display',serif;font-size:22px;color:#c4955a;margin-bottom:2px;padding-right:24px}
        .ppos{font-size:11px;color:rgba(42,31,20,.35);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px}
        /* Russian-language definition — top of the popup body so the Russian reading practice happens first. */
        .pdru{font-family:'Crimson Pro',serif;font-size:15px;color:#000;line-height:1.5;margin-bottom:8px;padding:8px 10px;background:rgba(196,149,90,.06);border-left:2px solid rgba(196,149,90,.4);border-radius:4px}
        .ptr{font-size:16px;color:rgba(42,31,20,.65);margin-bottom:7px;font-style:italic;padding-left:2px}
        .pgr{font-size:13px;color:#33507a;margin-bottom:7px;background:rgba(135,168,196,.08);border-radius:8px;padding:5px 10px}
        .pex{font-size:13px;color:rgba(42,31,20,.5);border-top:1px solid rgba(42,31,20,.08);padding-top:7px;line-height:1.5}
        .pext{font-size:12px;color:rgba(42,31,20,.3);margin-top:3px}
        .pload{color:rgba(42,31,20,.4);font-size:14px;text-align:center;padding:14px 0}
        .perr{color:#9d4630;font-size:13px}
        .psave{margin-top:12px;width:100%;border:1px solid rgba(196,149,90,.28);background:rgba(196,149,90,.09);color:#c4955a;padding:10px;border-radius:10px;font-size:14px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s}
        .psave:hover{background:rgba(196,149,90,.2)}
        .yobtn{width:100%;background:rgba(42,31,20,.06);border:1px solid rgba(42,31,20,.15);color:#000;padding:9px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s;text-align:left;margin-bottom:4px}
        .yobtn:hover{background:rgba(42,31,20,.12)}
        .gvin{width:100%;box-sizing:border-box;background:rgba(42,31,20,.04);border:1px solid rgba(42,31,20,.15);color:#000;padding:8px 9px;border-radius:9px;font-size:14px;font-family:'Crimson Pro',serif}
        .gvin:focus{outline:none;border-color:rgba(42,31,20,.4);background:rgba(42,31,20,.07)}
        .gvin::placeholder{color:rgba(42,31,20,.45)}
        .pmt{font-size:.78em;line-height:1.35;color:#7a5c2e;background:rgba(160,110,20,.09);
             border-left:2px solid rgba(160,110,20,.45);padding:6px 8px;border-radius:0 6px 6px 0;margin-bottom:8px}
        .pwrow{display:flex;align-items:baseline;gap:8px}
        .pwrow .pw{flex:1;min-width:0}
        .psay{flex:none;background:none;border:none;cursor:pointer;font-size:17px;line-height:1;
              padding:2px 4px;border-radius:6px;color:rgba(42,31,20,.45);transition:color .15s,background .15s}
        .psay:hover{color:rgba(42,31,20,.85);background:rgba(42,31,20,.07)}
        .psay.on{color:#a06e14}
        .panel{flex:1;padding:28px;overflow-y:auto;display:flex;flex-direction:column;gap:14px}
        .phdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
        .pti{font-family:'Playfair Display',serif;font-size:20px;color:#000}
        .ab{border:1px solid rgba(196,149,90,.28);background:rgba(196,149,90,.08);color:#c4955a;padding:7px 16px;border-radius:20px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s}
        .ab:hover{background:rgba(196,149,90,.18)}
        .ab.g{border-color:rgba(128,168,128,.28);background:rgba(128,168,128,.07);color:rgba(128,168,128,.9)} .ab.g:hover{background:rgba(128,168,128,.15)}
        .empty{text-align:center;color:rgba(42,31,20,.3);font-size:15px;padding:48px 0;line-height:1.7}
        .ilist{display:flex;flex-direction:column;gap:8px}
        .icard{background:rgba(42,31,20,.04);border:1px solid rgba(42,31,20,.09);border-radius:12px;padding:13px 16px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;transition:background .15s}
        .icard:hover{background:rgba(42,31,20,.07)}
        .icont{display:flex;flex-direction:column;gap:3px;flex:1;min-width:0}
        .ipri{font-size:17px;color:#000;font-family:'Playfair Display',serif}
        .ipos{font-size:11px;color:rgba(196,149,90,.7);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:1px}
        .isec{font-size:14px;color:rgba(42,31,20,.75)}
        .igr{font-size:12px;color:#33507a;background:rgba(135,168,196,.06);border-radius:6px;padding:3px 8px;align-self:flex-start;margin-top:3px}
        .iex{font-size:13px;color:rgba(42,31,20,.5);font-style:italic;margin-top:6px;padding-top:6px;border-top:1px solid rgba(42,31,20,.06);line-height:1.5}
        .iext{font-style:normal;font-size:12px;color:rgba(42,31,20,.35);margin-top:2px}
        .rmb{background:rgba(196,149,90,.1);border:1px solid rgba(196,149,90,.25);color:rgba(200,128,112,.75);font-size:18px;cursor:pointer;padding:0;width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .15s}
        .rmb:hover{background:rgba(196,149,90,.3);border-color:rgba(196,149,90,.5);color:#fff}
        .mover{position:fixed;inset:0;background:rgba(26,22,17,.85);z-index:100;display:flex;align-items:center;justify-content:center;padding:24px}
        .modal{background:#fbf8f2;border:1px solid rgba(42,31,20,.14);border-radius:16px;padding:28px;width:100%;max-width:480px;display:flex;flex-direction:column;gap:16px}
        .mti{font-family:'Playfair Display',serif;font-size:22px;color:#000}
        .mact{display:flex;gap:10px;justify-content:flex-end;margin-top:4px}
        .mcanc{background:none;border:1px solid rgba(42,31,20,.18);color:rgba(42,31,20,.55);padding:10px 20px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:all .15s}
        .mcanc:hover{color:#000;border-color:rgba(42,31,20,.35)}
        .mconf{background:linear-gradient(135deg,#c4955a,#a87a42);color:#fff;border:none;padding:10px 20px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:opacity .15s}
        .mconf:hover{opacity:.85} .mconf.g{background:linear-gradient(135deg,#5a8556,#4a6845)}

        /* First-visit landing screen */
        .land{position:fixed;inset:0;z-index:9999;background:#f5f0e8;display:flex;align-items:flex-start;justify-content:center;padding:32px 32px 60px;overflow-y:auto}
        .land::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .land-card{position:relative;max-width:580px;width:100%;text-align:center;display:flex;flex-direction:column;gap:28px;align-items:center;padding:24px}
        .land-icon{font-size:56px;margin-bottom:-4px}
        .land-title{font-family:'Playfair Display',serif;font-size:54px;font-weight:700;color:#c4955a;letter-spacing:-1px;line-height:1}
        .land-sub{font-size:12px;letter-spacing:3px;text-transform:uppercase;color:rgba(42,31,20,.45);margin-top:-12px}
        .land-tagline{font-family:'Crimson Pro',serif;font-style:italic;font-size:18px;color:rgba(42,31,20,.75);max-width:440px;line-height:1.5}
        .land-tips{background:rgba(196,149,90,.06);border:1px solid rgba(196,149,90,.18);border-radius:14px;padding:22px 26px;text-align:left;width:100%;max-width:440px;display:flex;flex-direction:column;gap:14px;margin-top:8px}
        .land-features{background:rgba(80,120,90,.04);border:1px solid rgba(120,160,130,.16);border-radius:14px;padding:22px 26px;text-align:left;width:100%;max-width:440px;display:flex;flex-direction:column;gap:12px;margin-top:8px}
        .land-features-title{font-family:'Playfair Display',serif;font-size:14px;color:#3f6b3a;letter-spacing:2px;text-transform:uppercase;text-align:center;margin-bottom:4px}
        .land-feat{display:flex;gap:12px;align-items:flex-start;font-size:14px;line-height:1.5;color:#000}
        .land-feat-icon{flex-shrink:0;font-size:18px;line-height:1.4;width:26px;text-align:center}
        .land-feat strong{color:#c4955a;font-weight:600}
        .land-tips-title{font-family:'Playfair Display',serif;font-size:14px;color:#c4955a;letter-spacing:2px;text-transform:uppercase;text-align:center;margin-bottom:4px}
        .land-tip{display:flex;gap:12px;align-items:flex-start;font-size:15px;line-height:1.5;color:#000}
        .land-tip-num{flex-shrink:0;width:24px;height:24px;border-radius:50%;background:rgba(196,149,90,.15);border:1px solid rgba(196,149,90,.3);color:#c4955a;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;margin-top:1px}
        .land-tip strong{color:#c4955a;font-weight:600}
        .land-begin{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;padding:16px 48px;border-radius:12px;font-size:18px;font-family:'Crimson Pro',serif;cursor:pointer;transition:opacity .15s,transform .1s;letter-spacing:1px;margin-top:8px;box-shadow:none;transform:translateY(-1px)}
        .land-begin:active{transform:translateY(0)}
        @media (max-width:520px){
          .land-title{font-size:42px}
          .land-tagline{font-size:16px}
          .land-tips,.land-features{padding:18px 20px}
          .land-tip{font-size:14px}
          .land-feat{font-size:13px}
        }

        /* Sign-in / sign-out auth UI */
        .auth-page{min-height:100vh;background:#f5f0e8;display:flex;align-items:center;justify-content:center;padding:32px;position:relative}
        .auth-page::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .auth-card{position:relative;display:flex;flex-direction:column;align-items:center;gap:20px;max-width:440px;width:100%}
        .auth-brand{text-align:center;margin-bottom:8px}
        .auth-brand-icon{font-size:44px}
        .auth-brand-title{font-family:'Playfair Display',serif;font-size:42px;font-weight:700;color:#c4955a;line-height:1;margin-top:8px}
        .auth-brand-sub{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:rgba(42,31,20,.45);margin-top:6px}
        /* Account gate. html/body are overflow:hidden for the app shell, so the
           gate has to own its own scrolling or a short viewport clips the form. */
        .auth-page{height:100vh;height:100dvh;overflow-y:auto;align-items:flex-start;padding:44px 32px}
        .gate-card{position:relative;background:#fbf8f2;border:1px solid rgba(42,31,20,.14);border-radius:16px;width:100%;padding:6px 4px 14px}
        .gate-blurb{font-family:'Crimson Pro',serif;font-size:15px;line-height:1.6;color:rgba(42,31,20,.75);text-align:center;max-width:400px;margin:0 auto}
        .gate-feats{display:flex;flex-direction:column;gap:9px;padding:16px 22px 4px;max-width:420px;margin:0 auto}
        .gate-feat{display:flex;gap:10px;align-items:flex-start;font-family:'Crimson Pro',serif;font-size:14px;line-height:1.45;color:rgba(42,31,20,.8)}
        .gate-feat span{flex-shrink:0;width:22px;text-align:center}
        .gate-note{font-family:'Crimson Pro',serif;font-style:italic;font-size:13px;color:rgba(42,31,20,.5);text-align:center;max-width:400px;margin:0 auto}
        @media (max-width:560px){
          .auth-page{padding:26px 16px}
          .auth-brand-title{font-size:34px}
          .gate-feats{padding:14px 8px 4px}
        }
        .userbtn-wrap{display:flex;align-items:center}

        /* Pending-approval screen */
        .pending{min-height:100vh;background:#f5f0e8;display:flex;align-items:center;justify-content:center;padding:32px;position:relative}
        .pending::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .pending-card{position:relative;max-width:480px;text-align:center;display:flex;flex-direction:column;gap:20px;align-items:center}
        .pending-icon{font-size:56px}
        .pending-title{font-family:'Playfair Display',serif;font-size:32px;color:#c4955a;line-height:1.2}
        .pending-msg{font-size:16px;line-height:1.6;color:rgba(42,31,20,.78);max-width:400px}
        .pending-email{font-size:13px;color:rgba(42,31,20,.5);background:rgba(196,149,90,.08);padding:8px 16px;border-radius:8px;border:1px solid rgba(196,149,90,.2)}
        .pending-userbtn{margin-top:8px}

        /* Admin panel overlay */
        .adm-over{position:fixed;inset:0;background:rgba(26,22,17,.92);z-index:200;display:flex;align-items:flex-start;justify-content:center;padding:24px;overflow-y:auto}
        .adm-modal{background:#fbf8f2;border:1px solid rgba(42,31,20,.14);border-radius:16px;width:100%;max-width:760px;display:flex;flex-direction:column;gap:0;margin:32px 0}

        /* Account panel */
        .auth-modal{max-width:420px}
        .auth-form{display:flex;flex-direction:column;gap:12px;padding:18px}
        .auth-why{font-family:'Crimson Pro',serif;font-size:13px;line-height:1.5;color:rgba(42,31,20,.65)}
        .auth-lbl{display:flex;flex-direction:column;gap:6px;font-family:'Crimson Pro',serif;font-size:13px;color:#000}
        .auth-in{background:#fff;border:1px solid rgba(42,31,20,.18);border-radius:8px;padding:10px 12px;font-family:'Crimson Pro',serif;font-size:15px;color:#000;outline:none}
        .auth-in:focus{border-color:rgba(196,149,90,.55)}
        .auth-hint{font-family:'Crimson Pro',serif;font-size:12px;color:rgba(42,31,20,.5)}
        .auth-err{font-family:'Crimson Pro',serif;font-size:13px;color:#9d4630;background:rgba(157,70,48,.08);border:1px solid rgba(157,70,48,.25);border-radius:8px;padding:8px 10px}
        .auth-note{font-family:'Crimson Pro',serif;font-size:13px;color:#5d4a2e;background:rgba(196,149,90,.12);border:1px solid rgba(196,149,90,.4);border-radius:8px;padding:8px 10px;line-height:1.45}
        .auth-switch{background:none;border:none;color:#c4955a;font-family:'Crimson Pro',serif;font-size:13px;cursor:pointer;text-decoration:underline;padding:0}
        .acct-email{font-family:'Crimson Pro',serif;font-size:12px;color:rgba(42,31,20,.6);max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        /* Small screens: let the header wrap instead of clipping, hide the
           email (Sign out still shows who you are on tap), and make the tab
           row horizontally scrollable so all four tabs stay reachable. */
        @media (max-width:640px){
          .hdr{flex-wrap:wrap;padding:10px 14px;row-gap:8px}
          .hdr>div:last-child{flex-wrap:wrap;row-gap:6px;justify-content:flex-end}
          .lsub{display:none}
          .acct-email{display:none}
          .tabs{padding:0 10px;overflow-x:auto;scrollbar-width:none}
          .tabs::-webkit-scrollbar{display:none}
          .tab{white-space:nowrap;flex-shrink:0}
          .tbadge{max-width:38vw}
          .ss{padding:28px 14px}
        }

        @media (max-width:560px){
          .auth-modal{max-width:100%;margin:16px 0}
        }
        .adm-head{padding:22px 28px 18px;border-bottom:1px solid rgba(42,31,20,.1);display:flex;align-items:center;justify-content:space-between;gap:16px}
        .adm-title{font-family:'Playfair Display',serif;font-size:24px;color:#c4955a}
        .adm-x{background:none;border:none;color:rgba(42,31,20,.6);font-size:24px;cursor:pointer;padding:0;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:8px;transition:all .15s}
        .adm-x:hover{background:rgba(42,31,20,.08);color:#000}
        .adm-body{padding:8px 20px 12px;display:flex;flex-direction:column;gap:0;max-height:65vh;overflow-y:auto}
        .adm-empty{text-align:center;padding:32px;color:rgba(42,31,20,.5);font-style:italic}
        /* One user per line: a list, not a stack of cards. The card treatment cost
           a card's worth of vertical space each and made ten users a scroll. */
        .adm-row{display:flex;align-items:center;gap:10px;padding:6px 8px;background:none;
                 border:none;border-bottom:1px solid rgba(42,31,20,.07);border-radius:0}
        .adm-row:last-child{border-bottom:none}
        .adm-row:hover{background:rgba(42,31,20,.035)}
        .adm-avatar{width:40px;height:40px;border-radius:50%;background:#f5f0e8 center/cover no-repeat;flex-shrink:0;border:1px solid rgba(42,31,20,.15)}
        .adm-info{flex:1;min-width:0;display:flex;align-items:baseline;gap:10px}
        .adm-name{font-size:14px;color:#000;font-weight:600;overflow:hidden;text-overflow:ellipsis;
                  white-space:nowrap;flex:0 1 auto;max-width:54%}
        .adm-email{font-size:12px;color:rgba(42,31,20,.5);overflow:hidden;text-overflow:ellipsis;
                   white-space:nowrap;flex:1 1 auto}
        .adm-status{font-size:10px;letter-spacing:.8px;text-transform:uppercase;padding:2px 8px;border-radius:5px;flex-shrink:0}
        .adm-status.approved{background:rgba(90,133,86,.18);color:#2f5a2a;border:1px solid rgba(90,133,86,.3)}
        .adm-status.rejected{background:rgba(196,149,90,.18);color:#9d4630;border:1px solid rgba(196,149,90,.3)}
        .adm-status.pending{background:rgba(196,149,90,.12);color:#c4955a;border:1px solid rgba(196,149,90,.25)}
        .adm-status.admin{background:rgba(135,168,196,.15);color:#2f4a6b;border:1px solid rgba(135,168,196,.3)}
        .adm-actions{display:flex;gap:8px;flex-shrink:0}
        .adm-btn{padding:4px 11px;border:none;border-radius:7px;font-size:12px;font-family:'Crimson Pro',serif;cursor:pointer;transition:opacity .15s;font-weight:600}
        .adm-btn:disabled{opacity:.5;cursor:wait}
        .adm-btn.approve{background:linear-gradient(135deg,#5a8556,#4a6845);color:#fff}
        .adm-btn.reject{background:rgba(196,149,90,.15);border:1px solid rgba(196,149,90,.4);color:#9d4630}
        .adm-btn.reject:hover:not(:disabled){background:rgba(196,149,90,.3)}
        .adm-err{margin:0 28px 16px;padding:12px 16px;background:rgba(196,149,90,.18);border:1px solid rgba(196,149,90,.35);color:#9d4630;border-radius:10px;font-size:13px}
        .adm-foot{padding:16px 28px;border-top:1px solid rgba(42,31,20,.08);display:flex;justify-content:space-between;align-items:center}
        .adm-refresh{background:none;border:1px solid rgba(42,31,20,.18);color:rgba(42,31,20,.7);padding:8px 16px;border-radius:8px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif}
        .adm-refresh:hover{color:#000;border-color:rgba(42,31,20,.4)}
        .adm-trigger{background:rgba(135,168,196,.12);border:1px solid rgba(135,168,196,.3);color:#2f4a6b;padding:6px 12px;border-radius:8px;font-size:12px;cursor:pointer;font-family:'Crimson Pro',serif;display:flex;align-items:center;gap:6px}
        .adm-trigger:hover{background:rgba(135,168,196,.2)}
        /* All admin mobile rules live here, AFTER every .adm- base rule —
           equal specificity means source order decides the winner. */
        @media (max-width:560px){
          .adm-over{padding:0;align-items:stretch}
          .adm-modal{margin:0;border-radius:0;border:none;min-height:100dvh;max-width:none}
          .adm-head{padding:14px 16px 12px}
          .adm-title{font-size:18px}
          .adm-body{padding:4px 10px 10px;max-height:none;flex:1}
          .adm-row{gap:8px;padding:9px 6px;align-items:center;flex-wrap:nowrap}
          .adm-info{flex-direction:column;align-items:flex-start;gap:1px}
          .adm-name{font-size:13px;max-width:100%}
          .adm-email{font-size:11px;max-width:100%}
          .adm-status{font-size:9px;padding:2px 6px;letter-spacing:.5px}
          .adm-actions{margin-left:0;flex-shrink:0;width:auto}
          .adm-btn{font-size:11px;padding:4px 9px}
          .adm-foot{padding:10px 16px}
        }
        html{-webkit-text-size-adjust:100%}
      .cl-formFieldInput,.cl-input,[class*='cl-formFieldInput'],[class*='cl-input']{
          background:#ffffff !important;
          color:#000 !important;
          border-color:rgba(196,149,90,.4) !important;
        }
        [class*='cl-card'],[class*='cl-modalContent']{
          background:#f5f0e8 !important;
          color:#000 !important;
        }
        [class*='cl-headerTitle'],[class*='cl-headerSubtitle'],[class*='cl-formFieldLabel'],[class*='cl-identityPreviewText']{
          color:#000 !important;
        }
        [class*='cl-formButtonPrimary']{
          background:#c4955a !important;
          color:#fff !important;
        }
        [class*='cl-footerActionLink'],[class*='cl-formFieldAction']{
          color:#c4955a !important;
        }
      `}</style>

      {/* The app itself. No sign-in gate: reading, audio, definitions and
          exercises all work signed out. The account panel below is optional
          and only affects whether vocabulary syncs across devices. */}
      {authOpen && (
        <div className="adm-over" onClick={function(e){ if (e.target.className === "adm-over") setAuthOpen(false); }}>
          <div className="adm-modal auth-modal">
            <div className="adm-head">
              <div className="adm-title">{authMode === "login" ? "Sign in" : "Create an account"}</div>
              <button className="adm-x" onClick={function(){ setAuthOpen(false); }}>×</button>
            </div>
            <form className="auth-form" onSubmit={submitAuth}>
              <div className="auth-why">
                Saving vocabulary works without an account — signing in just keeps
                it in step across your devices.
              </div>
              <label className="auth-lbl">Email
                <input className="auth-in" type="email" autoComplete="username"
                  value={authEmail} onChange={function(e){ setAuthEmail(e.target.value); }} required />
              </label>
              <label className="auth-lbl">Password
                <input className="auth-in" type="password"
                  autoComplete={authMode === "login" ? "current-password" : "new-password"}
                  value={authPassword} onChange={function(e){ setAuthPassword(e.target.value); }} required />
              </label>
              {authMode === "signup" && (
                <div className="auth-hint">At least 10 characters. Longer is better than fancier.</div>
              )}
              {authErr && <div className="auth-err">{authErr}</div>}
              {authNotice && <div className="auth-note">{authNotice}</div>}
              <button className="adm-btn approve" type="submit" disabled={authBusy}>
                {authBusy ? "…" : (authMode === "login" ? "Sign in" : "Create account")}
              </button>
              <button className="auth-switch" type="button" onClick={function(){
                setAuthMode(authMode === "login" ? "signup" : "login"); setAuthErr("");
              }}>
                {authMode === "login" ? "No account yet? Create one" : "Already have an account? Sign in"}
              </button>
            </form>
          </div>
        </div>
      )}

      {showAdmin && isAdmin && (
        <div className="adm-over" onClick={function(e){ if (e.target.className === "adm-over") setShowAdmin(false); }}>
          <div className="adm-modal">
            <div className="adm-head">
              <div className="adm-title">👥 Manage Users</div>
              <button className="adm-x" onClick={function(){ setShowAdmin(false); }}>×</button>
            </div>
            {adminErr && <div className="adm-err">{adminErr}</div>}
            <div className="adm-body">
              {adminLoad && <div className="adm-empty">Loading users…</div>}
              {!adminLoad && adminUsers.length === 0 && <div className="adm-empty">No users yet.</div>}
              {!adminLoad && adminUsers.map(function(u){
                var when = function(t){ return t ? new Date(t).toLocaleDateString() : "—"; };
                return (
                  <div key={u.id} className="adm-row">
                    <div className="adm-info">
                      <div className="adm-name">{u.email}</div>
                      <div className="adm-email">
                        {when(u.createdAt)} · seen {when(u.lastLoginAt)}
                      </div>
                    </div>
                    {u.isAdmin && <div className="adm-status admin">Admin</div>}
                    {!u.isAdmin && (
                      <div className="adm-status pending" style={u.approved ? {background:"rgba(90,133,86,.18)",color:"#2f5a2a",borderColor:"rgba(90,133,86,.3)"} : null}>
                        {u.approved ? (u.grandfathered ? "Existing" : "Approved") : "Pending"}
                      </div>
                    )}
                    {!u.isAdmin && (
                      <div className="adm-actions">
                        {!u.approved && (
                          <button className="adm-btn approve" disabled={adminLoad}
                            onClick={function(){ setUserApproval(u.email, true); }}>Approve</button>
                        )}
                        {u.approved && (
                          <button className="adm-btn reject" disabled={adminLoad}
                            onClick={function(){ setUserApproval(u.email, false); }}>Revoke</button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="adm-foot">
              <span style={{fontSize:12,color:"rgba(0,0,0,.5)"}}>
                {adminUsers.length} {adminUsers.length === 1 ? "user" : "users"}
                {adminUsers.filter(function(u){ return !u.isAdmin && !u.approved; }).length > 0 &&
                  " · " + adminUsers.filter(function(u){ return !u.isAdmin && !u.approved; }).length + " awaiting approval"}
              </span>
              <button className="adm-refresh" onClick={loadAdminUsers} disabled={adminLoad}>Refresh</button>
            </div>
          </div>
        </div>
      )}
      {showUpload && isAdmin && (
        <div className="adm-over" onClick={function(e){ if (e.target.className === "adm-over") setShowUpload(false); }}>
          <div className="adm-modal" style={{maxWidth:640}}>
            <div className="adm-head">
              <div className="adm-title">📤 Upload</div>
              <button className="adm-x" onClick={function(){ setShowUpload(false); }}>×</button>
            </div>
            <div className="adm-body" style={{padding:20,display:"flex",flexDirection:"column",gap:14}}>



              {upMode === "book" && (
                <div style={{fontSize:12,opacity:.6,lineHeight:1.5}}>
                  Upload an EPUB, FB2, TXT, or HTML file. Max 20MB. The file gets committed to <code style={{background:"rgba(0,0,0,.3)",padding:"1px 5px",borderRadius:3}}>public/books/&lt;category&gt;/</code> and added to the manifest.
                </div>
              )}

              {upErr && <div className="adm-err">{upErr}</div>}
              {upMsg && (
                <div style={{padding:"8px 12px",background:"rgba(138,171,124,.15)",border:"1px solid rgba(138,171,124,.4)",borderRadius:4,color:"#2f5a2a",fontSize:13}}>
                  ✓ {upMsg}
                </div>
              )}

              {upMode === "book" && (
                <>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Book file</label>
                    <input type="file" accept=".epub,.fb2,.txt,.html,.htm,.xhtml"
                      onChange={function(e){
                        var f = e.target.files && e.target.files[0];
                        setUpBookFile(f || null);
                        // Auto-fill title from filename if empty
                        if (f && !upTitle.trim()) {
                          var stem = f.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");
                          setUpTitle(stem);
                        }
                      }}
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#000",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                    {upBookFile && (
                      <div style={{fontSize:11,opacity:.55,marginTop:4,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>
                        {upBookFile.name} · {Math.round(upBookFile.size / 1024)} KB
                      </div>
                    )}
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Title</label>
                    <input type="text" value={upTitle} onChange={function(e){ setUpTitle(e.target.value); }}
                      placeholder="e.g. Анна Каренина"
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#000",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Author <span style={{opacity:.5}}>(optional)</span></label>
                    <input type="text" value={upBookAuthor} onChange={function(e){ setUpBookAuthor(e.target.value); }}
                      placeholder="e.g. Лев Толстой"
                      disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#000",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}/>
                  </div>
                  <div>
                    <label style={{display:"block",marginBottom:5,fontSize:13,opacity:.75,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Category</label>
                    <select value={upBookCategory} onChange={function(e){ setUpBookCategory(e.target.value); }} disabled={upBusy}
                      style={{width:"100%",padding:"9px 12px",background:"rgba(0,0,0,.3)",border:"1px solid rgba(210,197,175,.2)",color:"#000",borderRadius:4,fontSize:14,fontFamily:"inherit",boxSizing:"border-box"}}>
                      <option value="Works">Works</option>
                      <option value="Poetry">Poetry</option>
                      <option value="Spectacle">Spectacle</option>
                      <option value="Speeches">Speeches</option>
                      <option value="Speeches by Soviet Leaders">Speeches by Soviet Leaders</option>
                    </select>
                  </div>
                  <div style={{display:"flex",gap:10,alignItems:"center",marginTop:4}}>
                    <button onClick={uploadBook} disabled={upBusy || !upBookFile || !upTitle.trim()}
                      style={{padding:"10px 22px",background:"#c8a276",color:"#1a1612",border:"none",borderRadius:4,fontWeight:600,fontSize:14,cursor:upBusy?"wait":"pointer",opacity:(upBusy || !upBookFile || !upTitle.trim())?.5:1,fontFamily:"'Crimson Pro',serif"}}>
                      {upBusy ? "Uploading..." : "Upload book"}
                    </button>
                    <button onClick={function(){ setUpBookFile(null); setUpTitle(""); setUpBookAuthor(""); setUpMsg(""); setUpErr(""); }} disabled={upBusy}
                      style={{padding:"10px 16px",background:"transparent",color:"#000",border:"1px solid rgba(210,197,175,.25)",borderRadius:4,fontSize:13,cursor:"pointer",fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>
                      Clear
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
      {false && !seenLanding && (
        <div className="land">
          <div className="land-card">
            <div className="land-icon" style={{color:"#c4955a"}}><Pushkin size={68}/></div>
            <div>
              <div className="land-title">{SITE_NAME}</div>
              <div className="land-sub">Russian Practice</div>
            </div>
            <div className="land-tagline">
              A reader for Russian-language texts — read books from the built-in library with narrated audiobooks split chapter by chapter so you can follow along, tap any word for an instant definition, and test your comprehension with an AI tutor tuned to your level.
            </div>

            <div className="land-features">
              <div className="land-features-title">What you can do</div>
              <div className="land-feat"><span className="land-feat-icon">📖</span><div><strong>Read</strong> — Choose from the preloaded library of Russian books and stories.</div></div>
              <div className="land-feat"><span className="land-feat-icon">🔊</span><div><strong>Listen</strong> — Most books come with a narrated audiobook, split by chapter (or by act, for plays) so the recording lines up with what’s on the page.</div></div>
              <div className="land-feat"><span className="land-feat-icon">✏️</span><div><strong>Define</strong> — Tap any Russian word for translation, lemma, aspect pairs, and example sentences.</div></div>
              <div className="land-feat"><span className="land-feat-icon">🎯</span><div><strong>Pick your level</strong> — Set your proficiency (A1–C2) and the AI tutor calibrates the difficulty of its reading-comprehension questions to match.</div></div>
              <div className="land-feat"><span className="land-feat-icon">📚</span><div><strong>Build a library</strong> — Save vocab and grammar tips; they sync across all your devices.</div></div>
            </div>

            <div style={{margin:"2px 0 0",padding:"12px 14px",borderRadius:10,background:"rgba(200,162,118,.10)",border:"1px solid rgba(200,162,118,.28)",fontSize:14,lineHeight:1.55,color:"rgba(0,0,0,.92)"}}>
              <strong style={{color:"#c4955a"}}>About the audio:</strong> Most books in the library — Патриот, Тёмные аллеи, Анна Каренина and others — come with real human narration, split chapter by chapter so each recording matches the chapter you’re reading. A few are still text-only while we add their audio.
            </div>
            <div className="land-tips">
              <div className="land-tips-title">For the best experience</div>
              <div className="land-tip">
                <span className="land-tip-num">1</span>
                <span>Open the app in <strong>Google Chrome</strong> on a computer or Android. Chrome ships with high-quality Russian voices built in.<br/><span style={{opacity:.7,fontStyle:"italic",fontSize:13}}>On iPhone, use Safari with Russian Premium voices downloaded under Settings → Accessibility → Spoken Content → Voices.</span></span>
              </div>
              <div className="land-tip">
                <span className="land-tip-num">2</span>
                <span>On any Russian text, tap <strong>🎙 Voice</strong>. In the picker, choose <strong>Google русский</strong> — it's the most natural-sounding option in Chrome and the one we recommend.</span>
              </div>
              <div className="land-tip">
                <span className="land-tip-num">3</span>
                <span>If you don't see <strong>Google русский</strong> listed, pick any voice marked <strong>★ neural</strong> or <strong>✓ local</strong> — those are the next best options.</span>
              </div>
            </div>

            <button className="land-begin" onClick={dismissLanding}>Begin →</button>
          </div>
        </div>
      )}

      {/* ── Account gate ──────────────────────────────────────────────────
          The site is for account holders. Sign-up is instant — api/auth.js
          issues the session on signup, there is no approval step — but the app
          shell does not mount until /api/auth/me confirms who you are. The API
          routes enforce the same rule independently (catalogue, define, chat
          and tts all 401 without a session), so this screen is the front door,
          not the lock. */}
      {!authReady && (
        <div className="auth-page">
          <div className="auth-card">
            <div className="auth-brand">
              <div style={{color:"#c4955a"}}><Pushkin size={64}/></div>
              <div className="auth-brand-title">{SITE_NAME}</div>
              <div className="auth-brand-sub">Russian Practice</div>
            </div>
          </div>
        </div>
      )}

      {authReady && !me && (
        <div className="auth-page">
          <div className="auth-card">
            <div className="auth-brand">
              <div style={{color:"#c4955a"}}><Pushkin size={64}/></div>
              <div className="auth-brand-title">{SITE_NAME}</div>
              <div className="auth-brand-sub">Russian Practice</div>
            </div>

            <div className="gate-blurb">
              A reader for Russian literature — with narrated audiobooks and
              instant, dictionary-backed word definitions.
            </div>

            <div className="gate-card">
              <div className="gate-feats">
                <div className="gate-feat"><span>📖</span><div>Read from a library of Russian books and stories.</div></div>
                <div className="gate-feat"><span>🔊</span><div>Listen along — most books have a narrated recording, split by chapter.</div></div>
                <div className="gate-feat"><span>✏️</span><div>Tap any word for its dictionary entry, and save it to your vocabulary.</div></div>
              </div>

              <form className="auth-form" onSubmit={submitAuth}>
                <label className="auth-lbl">Email
                  <input className="auth-in" type="email" autoComplete="username" autoFocus
                    value={authEmail} onChange={function(e){ setAuthEmail(e.target.value); }} required />
                </label>
                <label className="auth-lbl">Password
                  <input className="auth-in" type="password"
                    autoComplete={authMode === "login" ? "current-password" : "new-password"}
                    value={authPassword} onChange={function(e){ setAuthPassword(e.target.value); }} required />
                </label>
                {authMode === "signup" && (
                  <div className="auth-hint">At least 10 characters. Longer is better than fancier.</div>
                )}
                {authErr && <div className="auth-err">{authErr}</div>}
              {authNotice && <div className="auth-note">{authNotice}</div>}
                <button className="btn-p" type="submit" disabled={authBusy}>
                  {authBusy ? "…" : (authMode === "login" ? "Sign in" : "Create account")}
                </button>
                <button className="auth-switch" type="button" onClick={function(){
                  setAuthMode(authMode === "login" ? "signup" : "login"); setAuthErr("");
                }}>
                  {authMode === "login" ? "No account yet? Create one" : "Already have an account? Sign in"}
                </button>
              </form>
            </div>

            <div className="gate-note">
              Accounts are created instantly — no approval, no waiting. Your
              vocabulary and reading progress follow you between devices.
            </div>
          </div>
        </div>
      )}

      {authReady && me && (
      <div className="app">
        <header className="hdr">
          <div
            className="logo"
            role="button"
            tabIndex={0}
            title="Back to home"
            onClick={function(){
              // Reset all the state that defines "where you are" so the user
              // lands on the home screen (the chat/read/grammar mode picker).
              // We do NOT clear `chapters` — if the user was reading a book,
              // they can pick "Read" again and resume where they left off.
              setMode("");
              setStarted(false);
              setMsgs([]);
              setGramTopicId("");
              setGramLevel("");
              setGramSearch("");
              setShowVP(false);
              setTab("chat");
              stopTTS();
            }}
            onKeyDown={function(e){ if (e.key === "Enter" || e.key === " ") { e.currentTarget.click(); } }}
            style={{cursor:"pointer"}}>
            <span className="lru">{SITE_NAME}</span><span className="lsub">{SITE_TAGLINE}</span>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:12}}>
            {false && <div className="level-wrap" title="Russian proficiency level. Adapts AI questions to your skill. Changes apply immediately to chat and reading-mode analysis.">
              <span className="level-lbl">Level</span>
              <select className="level-pill" value={level} onChange={function(e){ setLevel(e.target.value); }}>
                {LEVELS.map(function(l){ return <option key={l.code} value={l.code}>{l.label}</option>; })}
              </select>
            </div>}
            {started && isLit && <button className="tbadge" onClick={function(){ setShowTopic(true); }}>{"📖 " + (bookMeta.title || "Book")}</button>}

            {isAdmin && <button className="adm-trigger" onClick={function(){ setShowAdmin(true); }} title="Accounts">👥 Users</button>}
            {authReady && (me ? (
              <div className="userbtn-wrap">
                <span className="acct-email" title={me.email}>{me.email}</span>
                <button className="adm-trigger" onClick={signOut} title="Sign out">Sign out</button>
              </div>
            ) : (
              <button className="adm-trigger" onClick={function(){ setAuthMode("login"); setAuthErr(""); setAuthOpen(true); }} title="Sign in to sync vocabulary">Sign in</button>
            ))}
          </div>
        </header>

        <div className="tabs">
          {["chat","vocab","grammar","forum","music"].map(function(t){
            return (
              <button key={t} className={"tab"+(tab===t?" on":"")} onClick={function(){ setTab(t); }}>
                {t==="chat"?"Reading":t==="vocab"?"Vocabulary":t==="grammar"?"Grammar":t==="forum"?"Forum":"Music"}
                {t==="vocab"&&vocab.length>0&&<span className="bdg">{vocab.length}</span>}
                {t==="grammar"&&tips.length>0&&<span className="bdg g">{tips.length}</span>}
              </button>
            );
          })}
        </div>
        {ttsErr && (
          <div style={{padding:"8px 28px",background:"rgba(157,70,48,.18)",borderBottom:"1px solid rgba(157,70,48,.35)",color:"#9d4630",fontSize:13,display:"flex",alignItems:"center",gap:10}}>
            <span style={{flex:1}}>🔊 {ttsErr}</span>
            <button onClick={function(){ setTtsErr(""); }} style={{background:"none",border:"none",color:"#9d4630",cursor:"pointer",fontSize:18,padding:0}}>×</button>
          </div>
        )}

        {syncErr && (
          <div style={{padding:"8px 28px",background:"rgba(157,70,48,.18)",borderBottom:"1px solid rgba(157,70,48,.35)",color:"#9d4630",fontSize:13,display:"flex",alignItems:"center",gap:10}}>
            <span style={{flex:1}}>⚠️ {syncErr} <span style={{opacity:.75,fontStyle:"italic"}}>Remove a few entries from the Vocabulary tab to keep syncing.</span></span>
            <button onClick={function(){ setSyncErr(""); }} style={{background:"none",border:"none",color:"#9d4630",cursor:"pointer",fontSize:18,padding:0}}>×</button>
          </div>
        )}

        {tab==="music" && (
          <div className="main">
            {(function(){
              var artist = (musicData && musicArtist != null) ? musicData[musicArtist] : null;
              var song = (artist && musicSong != null) ? artist.songs[musicSong] : null;

              /* ── Song view: title, definable lyrics, video pinned below ── */
              if (song) {
                return (
                  <div style={{flex:1,display:"flex",flexDirection:"column",minHeight:0}}>
                    <div style={{flex:1,overflowY:"auto",padding:"22px 20px 12px"}}>
                      <div style={{maxWidth:640,margin:"0 auto"}}>
                        <button className="btn-g" style={{padding:"5px 12px",fontSize:13,marginBottom:14}}
                          onClick={function(){ setMusicSong(null); setPopup(null); }}>← {artist.artist}</button>
                        <div style={{maxWidth:560,margin:"0 0 20px"}}>
                          <div style={{position:"relative",width:"100%",paddingBottom:"56.25%",height:0}}>
                            <iframe
                              src={"https://www.youtube.com/embed/" + song.youtube}
                              title={song.title}
                              style={{position:"absolute",inset:0,width:"100%",height:"100%",border:"none",borderRadius:10}}
                              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                              allowFullScreen />
                          </div>
                        </div>
                        <div style={{fontFamily:"'Crimson Pro',serif",fontSize:15,color:"rgba(42,31,20,.55)",letterSpacing:.5}}>{artist.artist}</div>
                        <h1 style={{fontFamily:"'Playfair Display',serif",fontSize:34,color:"#000",fontWeight:700,margin:"2px 0 18px",lineHeight:1.15}}>{song.title}</h1>
                        <div style={{fontFamily:"'Crimson Pro',serif",fontSize:19,color:"#1c1610"}}>
                          {renderLyrics(song.lyrics)}
                        </div>
                        <div style={{height:16}}/>
                      </div>
                    </div>
                  </div>
                );
              }

              /* ── Song list for an artist ── */
              if (artist) {
                return (
                  <div className="ss">
                    <div className="sico">🎤</div>
                    <h1 className="sti">{artist.artist}</h1>
                    <div style={{width:"100%",maxWidth:520,display:"flex",flexDirection:"column",gap:10}}>
                      {artist.songs.map(function(sg, i2){
                        return (
                          <button key={i2} className="btn-p" style={{textAlign:"left",padding:"14px 18px"}}
                            onClick={function(){ setMusicSong(i2); }}>
                            <div style={{fontSize:17}}>{sg.title}</div>
                          </button>
                        );
                      })}
                      <button className="btn-g" onClick={function(){ setMusicArtist(null); }}>← Артисты</button>
                    </div>
                  </div>
                );
              }

              /* ── Artist list ── */
              return (
                <div className="ss">
                  <div className="sico">🎵</div>
                  <h1 className="sti">Music</h1>
                  <p className="sde">Учите русский через песни — каждое слово можно нажать.</p>
                  <div style={{width:"100%",maxWidth:520,display:"flex",flexDirection:"column",gap:10}}>
                    {musicData === null && <p className="sde">Loading…</p>}
                    {(musicData || []).map(function(ar, i2){
                      return (
                        <button key={i2} className="btn-p" style={{textAlign:"left",padding:"16px 20px"}}
                          onClick={function(){ setMusicArtist(i2); setMusicSong(null); }}>
                          <div style={{fontSize:19}}>🎤 {ar.artist}</div>
                          <div style={{fontSize:12,opacity:.8,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>{ar.songs.length} {ar.songs.length===1?"песня":"песни"}</div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {tab==="forum" && (
          <div className="main">
              <div className="ss" style={{alignItems:"stretch",maxWidth:680,width:"100%"}}>
                <div style={{textAlign:"center"}}>
                  <div className="sico">💬</div>
                  <h1 className="sti">Forum</h1>
                  <p className="sde">Request books, report bugs, talk with other readers.</p>
                </div>

                {!me && (
                  <div style={{textAlign:"center",display:"flex",flexDirection:"column",gap:10,alignItems:"center"}}>
                    <p className="sde">The forum is for signed-in readers.</p>
                    <button className="btn-p" onClick={function(){ setAuthMode("login"); setAuthErr(""); setAuthOpen(true); }}>Sign in</button>
                    <button className="btn-g" onClick={function(){ setTab("chat"); }}>← Back</button>
                  </div>
                )}

                {me && (
                  <div style={{display:"flex",flexDirection:"column",gap:12}}>
                    {forumErr && (
                      <div style={{padding:"8px 12px",borderRadius:8,background:"rgba(157,70,48,.14)",color:"#9d4630",fontSize:13}}>
                        {forumErr}
                      </div>
                    )}

                    {/* Category tabs */}
                    {!forumThread && (
                      <div style={{display:"flex",gap:8,justifyContent:"center",flexWrap:"wrap"}}>
                        {FORUM_CATS.map(function(c){
                          var active = c.id === forumCat;
                          return (
                            <button key={c.id} onClick={function(){ setForumCat(c.id); setForumCompose(false); }}
                              style={{padding:"7px 14px",borderRadius:18,cursor:"pointer",fontSize:14,
                                border:"1px solid rgba(196,149,90,.5)",
                                background:active?"#c4955a":"transparent",
                                color:active?"#fff":"#c4955a",fontWeight:active?600:400}}>
                              {c.label}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {/* ── List view ── */}
                    {!forumThread && (
                      <div style={{display:"flex",flexDirection:"column",gap:8}}>
                        {!forumCompose && (
                          <button className="btn-g" style={{alignSelf:"flex-end",padding:"6px 14px",fontSize:13}}
                            onClick={function(){ setForumCompose(true); }}>＋ New post</button>
                        )}
                        {forumCompose && (
                          <div style={{display:"flex",flexDirection:"column",gap:8,padding:14,borderRadius:10,
                            border:"1px solid rgba(196,149,90,.4)",background:"rgba(196,149,90,.07)"}}>
                            <input value={forumTitle} maxLength={120} placeholder={forumCat==="requests"?"Book title and author…":forumCat==="bugs"?"What broke?":"Title…"}
                              onChange={function(e){ setForumTitle(e.target.value); }}
                              style={{padding:"9px 12px",borderRadius:8,border:"1px solid rgba(0,0,0,.2)",fontSize:15,fontFamily:"inherit"}}/>
                            <textarea value={forumBody} maxLength={4000} rows={4}
                              placeholder={forumCat==="requests"?"Why this book? A link to the audiobook recording helps a lot.":forumCat==="bugs"?"What happened, what did you expect, which book/chapter, which browser?":"Write your post…"}
                              onChange={function(e){ setForumBody(e.target.value); }}
                              style={{padding:"9px 12px",borderRadius:8,border:"1px solid rgba(0,0,0,.2)",fontSize:14,fontFamily:"inherit",resize:"vertical"}}/>
                            <div style={{display:"flex",gap:8,justifyContent:"flex-end"}}>
                              <button className="btn-g" style={{padding:"6px 14px",fontSize:13}} onClick={function(){ setForumCompose(false); }}>Cancel</button>
                              <button className="btn-p" style={{padding:"6px 16px",fontSize:13}} disabled={forumBusy} onClick={submitForumPost}>Post</button>
                            </div>
                          </div>
                        )}

                        {forumPosts === null && <p className="sde" style={{textAlign:"center"}}>Loading…</p>}
                        {forumPosts !== null && forumPosts.length === 0 && !forumCompose && (
                          <p className="sde" style={{textAlign:"center"}}>Nothing here yet — be the first to post.</p>
                        )}
                        {(forumPosts || []).map(function(p2){
                          return (
                            <div key={p2.id} style={{display:"flex",gap:10,alignItems:"flex-start",padding:"10px 12px",
                              borderRadius:10,border:"1px solid rgba(0,0,0,.1)",background:"rgba(255,255,255,.5)",cursor:"pointer"}}
                              onClick={function(){ openForumThread(p2.id); }}>
                              {forumCat === "requests" && (
                                <button title="Upvote" onClick={function(e){ e.stopPropagation(); toggleForumVote(p2.id); }}
                                  style={{border:"1px solid rgba(196,149,90,.5)",background:"transparent",color:"#c4955a",
                                    borderRadius:8,padding:"4px 9px",cursor:"pointer",fontSize:13,lineHeight:1.2,minWidth:38}}>
                                  ▲<br/>{p2.voteCount || 0}
                                </button>
                              )}
                              <div style={{flex:1,minWidth:0}}>
                                <div style={{fontSize:15,fontWeight:600,color:"#222"}}>
                                  {p2.pinned ? "📌 " : ""}{p2.title}{p2.closed ? " · 🔒" : ""}
                                </div>
                                <div style={{fontSize:12,opacity:.65,marginTop:2}}>
                                  {p2.authorName} · {forumWhen(p2.createdAt)} · {p2.replyCount || 0} {(p2.replyCount||0) === 1 ? "reply" : "replies"}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* ── Thread view ── */}
                    {forumThread && (
                      <div style={{display:"flex",flexDirection:"column",gap:10}}>
                        <button className="btn-g" style={{alignSelf:"flex-start",padding:"5px 12px",fontSize:13}}
                          onClick={function(){ setForumThread(null); loadForumBoard(forumCat); }}>← All posts</button>
                        <div style={{padding:"12px 14px",borderRadius:10,border:"1px solid rgba(196,149,90,.4)",background:"rgba(196,149,90,.07)"}}>
                          <div style={{display:"flex",gap:10,alignItems:"flex-start"}}>
                            {forumCat === "requests" && (
                              <button title="Upvote" onClick={function(){ toggleForumVote(forumThread.id); }}
                                style={{border:"1px solid rgba(196,149,90,.6)",borderRadius:8,padding:"4px 9px",cursor:"pointer",fontSize:13,lineHeight:1.2,minWidth:38,
                                  background:forumThread.youVoted?"#c4955a":"transparent",color:forumThread.youVoted?"#fff":"#c4955a"}}>
                                ▲<br/>{forumThread.voteCount || 0}
                              </button>
                            )}
                            <div style={{flex:1,minWidth:0}}>
                              <div style={{fontSize:17,fontWeight:700,color:"#222"}}>
                                {forumThread.pinned ? "📌 " : ""}{forumThread.title}{forumThread.closed ? " · 🔒 closed" : ""}
                              </div>
                              <div style={{fontSize:12,opacity:.65,margin:"2px 0 8px"}}>{forumThread.authorName} · {forumWhen(forumThread.createdAt)}</div>
                              <div style={{fontSize:14,whiteSpace:"pre-wrap",color:"#333"}}>{forumThread.body}</div>
                            </div>
                          </div>
                          {me.isAdmin && (
                            <div style={{display:"flex",gap:6,marginTop:10,flexWrap:"wrap"}}>
                              <button className="btn-g" style={{padding:"4px 10px",fontSize:12}} onClick={function(){ forumMod(forumThread.pinned ? "unpin" : "pin"); }}>{forumThread.pinned ? "Unpin" : "Pin"}</button>
                              <button className="btn-g" style={{padding:"4px 10px",fontSize:12}} onClick={function(){ forumMod(forumThread.closed ? "open" : "close"); }}>{forumThread.closed ? "Reopen" : "Close"}</button>
                              <button className="btn-g" style={{padding:"4px 10px",fontSize:12,color:"#9d4630"}} onClick={function(){ if (window.confirm("Delete this post?")) forumMod("delete"); }}>Delete</button>
                            </div>
                          )}
                        </div>

                        {(forumThread.replies || []).map(function(r2){
                          return (
                            <div key={r2.id} style={{padding:"9px 12px",borderRadius:10,border:"1px solid rgba(0,0,0,.08)",background:"rgba(255,255,255,.5)",marginLeft:18}}>
                              <div style={{fontSize:12,opacity:.65,marginBottom:3}}>
                                {r2.authorName}{r2.isAdmin ? " · ★ admin" : ""} · {forumWhen(r2.createdAt)}
                              </div>
                              <div style={{fontSize:14,whiteSpace:"pre-wrap",color:"#333"}}>{r2.body}</div>
                            </div>
                          );
                        })}

                        {(!forumThread.closed || me.isAdmin) && (
                          <div style={{display:"flex",flexDirection:"column",gap:6,marginLeft:18}}>
                            <textarea value={forumReply} maxLength={2000} rows={3} placeholder="Write a reply…"
                              onChange={function(e){ setForumReply(e.target.value); }}
                              style={{padding:"9px 12px",borderRadius:8,border:"1px solid rgba(0,0,0,.2)",fontSize:14,fontFamily:"inherit",resize:"vertical"}}/>
                            <button className="btn-p" style={{alignSelf:"flex-end",padding:"6px 16px",fontSize:13}} disabled={forumBusy || forumReply.trim().length < 2} onClick={submitForumReply}>Reply</button>
                          </div>
                        )}
                      </div>
                    )}

                    <button className="btn-g" style={{alignSelf:"center",marginTop:6}} onClick={function(){ setTab("chat"); setForumThread(null); setForumCompose(false); }}>← Back</button>
                  </div>
                )}
              </div>
          </div>
        )}

        {tab==="chat" && (
          <div className="main">
            {!started && !mode && (
              <div className="ss">
                <div className="sico" style={{color:"#c4955a"}}><Pushkin size={64}/></div>
                <h1 className="sti">{SITE_NAME}</h1>
                <p className="sde">Choose how you want to practice today.</p>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:14}}>
                  <button className="btn-p" onClick={function(){ setMode("read"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>📖 Read</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Open a book from the library and read along with the narration.</div>
                  </button>
                  <button className="btn-p" onClick={function(){ setMode("grammar"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>📚 Grammar</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Pick your level and a topic. Quick reference pages with rules and examples.</div>
                  </button>
                  {WORDBANK_ENABLED && (
                    <button className="btn-p" onClick={function(){ setMode("wordbank"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                      <div style={{fontSize:22,marginBottom:4}}>🗂️ Vocab</div>
                      <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Drill the most common Russian words, ranked by real-world frequency, in blocks of 30.</div>
                    </button>
                  )}
                  <button className="btn-p" onClick={function(){ setTab("forum"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>💬 Forum</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Request books, report bugs, and talk with other readers.</div>
                  </button>
                </div>
              </div>
            )}

            {!started && mode === "read" && (
              <div className="ss">
                <div className="sico">📖</div>
                <h1 className="sti">{chapters.length > 0 ? bookMeta.title : "Open a Russian book"}</h1>
                <p className="sde">{chapters.length > 0 ? bookMeta.author : "Choose a book from the library to begin reading."}</p>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:10}}>
                  {chapters.length > 0 ? (
                    <>
                      {cbm > 0 && <button className="btn-p" onClick={function(){ startLit(cbm); }}>📌 Resume at chapter {cbm+1}</button>}
                      <button className={cbm>0?"btn-g":"btn-p"} onClick={function(){ startLit(0); }}>{cbm>0?"Start from beginning":"Начать читать →"}</button>
                      
                      <button onClick={async function(){
                        setChapters([]); setCidx(0); setCbm(0); setBookMeta({title:"",author:""});
                        try { await storage.delete(EPUB_CACHE); } catch(e) {}
                        try { await storage.delete(EPUB_BM); } catch(e) {}
                        try { await storage.delete(QHIST_KEY); } catch(e) {}
                      }} style={{background:"none",border:"none",color:"rgba(0,0,0,.4)",fontSize:11,fontStyle:"italic",fontFamily:"'Crimson Pro',serif",cursor:"pointer",padding:"4px",marginTop:4,textDecoration:"underline",textDecorationColor:"rgba(210,197,175,.2)",alignSelf:"center"}}>clear cached book</button>
                    </>
                  ) : ( <></> )}

                  {/* Library browser — searchable card layout for preset books +
                      user uploads. Replaces the prior dropdown. Search filters
                      across both titles and authors. Books are grouped by category;
                      uploads show in their own "My Uploads" section at the top. */}
                  {(presetBooks.length > 0) && (
                    <div style={{marginTop:18,paddingTop:18,borderTop:"1px solid rgba(210,197,175,.1)",width:"100%"}}>
                      {/* Continue Reading — books with saved progress, newest first.
                          Clicking one resumes at the saved chapter/page. */}
                      {(function() {
                        var entries = Object.keys(progressMap).map(function(k){ return progressMap[k]; });
                        entries.sort(function(a, b){ return (b.lastRead || 0) - (a.lastRead || 0); });
                        var recent = entries.slice(0, 6);
                        if (recent.length === 0) return null;
                        // Match recents against actual library entries so we can resume them.
                        var findEntry = function(rec) {
                          // Try uploaded books first (matched by filename or title)
                          for (var i = 0; i < uploadedBooks.length; i++) {
                            var u = uploadedBooks[i];
                            if (rec.filename && u.filename === rec.filename && u.title === rec.title) return { type: "upload", book: u };
                            if (u.title === rec.title && (u.author || "") === (rec.author || "")) return { type: "upload", book: u };
                          }
                          for (var j = 0; j < presetBooks.length; j++) {
                            var pBook = presetBooks[j];
                            if (rec.filename && pBook.filename === rec.filename) return { type: "preset", book: pBook };
                          }
                          return null;
                        };
                        return (
                          <div className="lib-section" style={{marginBottom:18}}>
                            <div className="lib-section-hdr">Continue reading</div>
                            <div className="lib-grid">
                              {recent.map(function(rec, i) {
                                var match = findEntry(rec);
                                if (!match) return null;
                                var total = rec.totalChapters || 1;
                                var pct = total > 1 ? Math.round((rec.cidx / total) * 100) : (rec.pidx > 0 ? 50 : 0);
                                var humanLast = (function() {
                                  var ms = Date.now() - (rec.lastRead || 0);
                                  var min = Math.floor(ms / 60000);
                                  if (min < 1) return "just now";
                                  if (min < 60) return min + "m ago";
                                  var hr = Math.floor(min / 60);
                                  if (hr < 24) return hr + "h ago";
                                  var d = Math.floor(hr / 24);
                                  if (d < 30) return d + "d ago";
                                  return "a while ago";
                                })();
                                return (
                                  <div key={i} className="lcard" onClick={function() {
                                    if (match.type === "upload") openUploadedBook(match.book);
                                    else if (match.book.category === "Song Lyrics") openSongPicker(match.book);
                                    else loadPresetBook(match.book);
                                  }}>
                                    <div className="lcn" style={{color:"rgba(0,0,0,.5)"}}>↻ {humanLast}</div>
                                    <div className="lchead">{bookLabel(rec)}</div>
                                    <div style={{marginTop:8,fontSize:11,color:"rgba(0,0,0,.55)"}}>
                                      Ch. {(rec.cidx || 0) + 1}{total > 1 ? "/" + total : ""}
                                      {(rec.pidx || 0) > 0 && " · Page " + ((rec.pidx || 0) + 1)}
                                      {" · " + pct + "%"}
                                    </div>
                                    <div style={{marginTop:6,height:3,background:"rgba(210,197,175,.1)",borderRadius:2,overflow:"hidden"}}>
                                      <div style={{height:"100%",width:pct+"%",background:"#c8a276"}}/>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })()}

                      {/* Quick pick dropdown — for users who know exactly which book they want
                          and prefer not to scroll through the card grid below. Lives alongside
                          the card grid; both stay in sync via the same data source. */}
                      {presetBooks.length > 0 && (
                        <div style={{marginBottom:18}}>
                          <div style={{fontSize:11,letterSpacing:2,textTransform:"uppercase",color:"rgba(0,0,0,.45)",marginBottom:8,textAlign:"left"}}>Quick pick</div>
                          <select
                            className="quickpick"
                            defaultValue=""
                            onChange={function(e){
                              var idx = e.target.value;
                              if (idx === "") return;
                              var book = presetBooks[parseInt(idx,10)];
                              if (book && book.category === "Song Lyrics") {
                                openSongPicker(book);
                              } else {
                                loadPresetBook(book);
                              }
                              e.target.value = "";  // reset so picking same again triggers onChange
                            }}>
                            <option value="" disabled>📖 Choose a book from the library…</option>
                            {(function() {
                              // Grouped by author: that is how a reader looks for a text.
                              // One <optgroup> per author, and the option is the bare
                              // title, since the author is already the heading above it.
                              // Category grouping lives on in the card grid below, which
                              // has the room for it.
                              var groups = {};
                              presetBooks.forEach(function(book, idx) {
                                var author = String((book && book.author) || "").trim() || "Other";
                                if (!groups[author]) groups[author] = [];
                                groups[author].push({ book: book, idx: idx });
                              });
                              // Cyrillic sorts correctly only with an explicit locale;
                              // the unattributed bucket goes last rather than under "O".
                              var authors = Object.keys(groups).sort(function(a, b) {
                                if (a === "Other") return 1;
                                if (b === "Other") return -1;
                                return a.localeCompare(b, "ru");
                              });
                              return authors.map(function(author) {
                                var entries = groups[author].slice().sort(function(a, b) {
                                  return String((a.book && a.book.title) || "")
                                    .localeCompare(String((b.book && b.book.title) || ""), "ru");
                                });
                                return (
                                  <optgroup key={author} label={author}>
                                    {entries.map(function(entry) {
                                      var book = entry.book;
                                      var title = (book && (book.title || book.filename)) || "";
                                      // 🎧 for a recording, EN for a parallel
                                      // translation: the two things a reader
                                      // actually chooses between, and all the
                                      // width a dropdown row has to spare.
                                      // Both states are labelled, not just the
                                      // positive one: an absent marker reads as
                                      // an oversight, where "w/o ENG" is an
                                      // answer to the question being asked.
                                      var tight = optChars < 999;
                                      var lead = book && book.audiobook ? "🎧 " : "";
                                      // The tag never abbreviates. It is the
                                      // thing being asked of the row, so on a
                                      // narrow screen the TITLE gives way and
                                      // the tag stays whole.
                                      var tag = book && book.parallelEn ? "  w/ ENG" : "  w/o ENG";
                                      // The marker must survive: it is the whole
                                      // point of the row. So the title is what
                                      // gives way, and only by as much as needed.
                                      var room = optChars - lead.length - tag.length;
                                      var shown = tight && title.length > room
                                        ? title.slice(0, Math.max(4, room - 1)).trim() + "…"
                                        : title;
                                      return (
                                        <option key={entry.idx} value={entry.idx}>{lead + shown + tag}</option>
                                      );
                                    })}
                                  </optgroup>
                                );
                              });
                            })()}
                          </select>
                        </div>
                      )}
                      <input
                        type="text"
                        placeholder="🔍 Search books and authors…"
                        value={bookSearch}
                        onChange={function(e){ setBookSearch(e.target.value); }}
                        className="lib-search"
                      />
                      {(function() {
                        var q = bookSearch.toLowerCase().trim();
                        var matches = function(book) {
                          if (!q) return true;
                          var hay = ((book.title || "") + " " + (book.author || "") + " " + (book.filename || "")).toLowerCase();
                          return hay.indexOf(q) !== -1;
                        };
                        // Filter uploaded books
                        var filteredUploads = uploadedBooks.filter(matches);

                        // Group preset books by category, preserving original index for lookup.
                        // Normalize legacy "Novel"/"Short Stories"/"Plays" → "Works" so older
                        // entries in index.json fall into the right bucket without an admin edit.
                        var CATEGORIES = ["Works", "Song Lyrics", "Poetry", "Spectacle", "Speeches", "Speeches by Soviet Leaders", "Texts Without English"];
                        // Render order: "Texts Without English" sits at the very bottom,
                        // after the catch-all "Other" bucket.
                        var ORDER = ["Works", "Song Lyrics", "Poetry", "Spectacle", "Speeches", "Speeches by Soviet Leaders", "Other", "Texts Without English"];
                        var normalize = function(cat) {
                          if (cat === "Novel" || cat === "Short Stories" || cat === "Plays") return "Works";
                          return cat;
                        };
                        var buckets = {};
                        CATEGORIES.forEach(function(c){ buckets[c] = []; });
                        buckets["Other"] = [];
                        presetBooks.forEach(function(book, idx) {
                          if (!matches(book)) return;
                          var cat = normalize((book && book.category) || "");
                          var bucket = CATEGORIES.indexOf(cat) !== -1 ? cat : "Other";
                          buckets[bucket].push({ book: book, idx: idx });
                        });

                        var presetCount = ORDER.reduce(function(a, c){ return a + buckets[c].length; }, 0);
                        var totalResults = presetCount + filteredUploads.length;
                        if (q && totalResults === 0) {
                          return <div style={{padding:"40px 16px",textAlign:"center",color:"rgba(0,0,0,.5)",fontStyle:"italic"}}>No books match «{bookSearch}»</div>;
                        }
                        return (
                          <>
                            {/* My Uploads section — only when there are uploaded books matching the filter */}
                            {filteredUploads.length > 0 && (
                              <div className="lib-section">
                                <div className="lib-section-hdr">My Uploads</div>
                                <div className="lib-grid">
                                  {filteredUploads.map(function(book) {
                                    var isLoading = bookLoading === book.id;
                                    var isDisabled = bookLoading !== null && !isLoading;
                                    return (
                                      <div key={book.id}
                                        className={"lib-card" + (isLoading ? " is-loading" : "") + (isDisabled ? " is-disabled" : "")}
                                        onClick={function(){
                                          if (bookLoading !== null) return;
                                          openUploadedBook(book);
                                        }}>
                                        <div className="lib-card-title">{bookLabel(book)}</div>
                                        <div className="lib-card-meta">
                                          <span className="lib-card-cat">Upload</span>
                                          <button
                                            className="lib-card-remove"
                                            title="Remove from library"
                                            onClick={function(e){ e.stopPropagation(); removeUploadedBook(book.id); }}
                                          >×</button>
                                        </div>
                                        {isLoading && (
                                          <div className="lib-card-loader">
                                            <div className="typing"><div className="dot"/><div className="dot"/><div className="dot"/></div>
                                            <span>Loading…</span>
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                            {/* Preset library, grouped by category, then by audiobook availability */}
                            {ORDER.map(function(cat) {
                              var entries = buckets[cat];
                              if (!entries.length) return null;
                              var withAudio = entries.filter(function(e){ return !!(e.book.audiobook); });
                              var textOnly  = entries.filter(function(e){ return !e.book.audiobook; });
                              var renderCard = function(entry) {
                                var book = entry.book;
                                var isLoading = bookLoading === book.filename;
                                var isDisabled = bookLoading !== null && !isLoading;
                                return (
                                  <div key={entry.idx}
                                    className={"lib-card" + (isLoading ? " is-loading" : "") + (isDisabled ? " is-disabled" : "")}
                                    onClick={function(){
                                      if (bookLoading !== null) return;
                                      if (book.category === "Song Lyrics") {
                                        openSongPicker(book);
                                      } else {
                                        loadPresetBook(book);
                                      }
                                    }}>
                                    <div className="lib-card-title">{bookLabel(book)}</div>
                                    <div className="lib-card-meta">
                                      {cat !== "Other" && cat !== "Texts Without English" && <span className="lib-card-cat">{cat}</span>}
                                      {book.audiobook && <span style={{fontSize:11,color:"#c4955a"}}>🎧 Audiobook</span>}
                                      {cat === "Song Lyrics" && book.songs && book.songs.length > 0 && (
                                        <span style={{fontSize:11,color:"rgba(42,31,20,.45)"}}>{book.songs.length} song{book.songs.length === 1 ? "" : "s"}</span>
                                      )}
                                    </div>
                                    {isLoading && (
                                      <div className="lib-card-loader">
                                        <div className="typing"><div className="dot"/><div className="dot"/><div className="dot"/></div>
                                        <span>Loading…</span>
                                      </div>
                                    )}
                                  </div>
                                );
                              };
                              if (cat === "Texts Without English") {
                                // One undivided group: what these share is the missing
                                // translation, not whether they have a recording (the 🎧
                                // badge on each card already says that).
                                return (
                                  <div key={cat} className="lib-section">
                                    <div className="lib-section-hdr">📖 Texts Without English</div>
                                    <div className="lib-grid">{entries.map(renderCard)}</div>
                                  </div>
                                );
                              }
                              return (
                                <div key={cat} className="lib-section">
                                  {withAudio.length > 0 && (
                                    <>
                                      <div className="lib-section-hdr">🎧 {cat} — With Audiobook</div>
                                      <div className="lib-grid" style={{marginBottom:18}}>
                                        {withAudio.map(renderCard)}
                                      </div>
                                    </>
                                  )}
                                  {textOnly.length > 0 && (
                                    <>
                                      <div className="lib-section-hdr">📖 {cat} — Text Only</div>
                                      <div className="lib-grid">
                                        {textOnly.map(renderCard)}
                                      </div>
                                    </>
                                  )}
                                </div>
                              );
                            })}
                          </>
                        );
                      })()}

                      {/* Inline song picker — shown after picking a Song Lyrics
                          artist from the library so users can jump to a specific song.
                          Auto-scrolls into view via songPickerRef when shown. */}
                      {songPickerBook && (
                        <div ref={songPickerRef} style={{marginTop:14,padding:14,background:"rgba(0,0,0,.25)",border:"1px solid rgba(200,162,118,.4)",borderRadius:6,scrollMarginTop:20}}>
                          <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:10}}>
                            <div style={{fontFamily:"'Crimson Pro',serif",fontSize:15}}>
                              🎵 <span style={{fontStyle:"italic"}}>{songPickerBook.title}</span> · pick a song
                            </div>
                            <button onClick={function(){ setSongPickerBook(null); setSongPickerList([]); setSongPickerErr(""); }}
                              style={{background:"transparent",color:"rgba(0,0,0,.55)",border:"none",cursor:"pointer",fontSize:18,padding:"0 4px"}}>×</button>
                          </div>
                          {songPickerLoad && (
                            <div style={{fontSize:13,opacity:.6,padding:"6px 0",fontStyle:"italic"}}>Loading song list…</div>
                          )}
                          {songPickerErr && (
                            <div style={{fontSize:13,color:"#9d4630",padding:"6px 0"}}>{songPickerErr}</div>
                          )}
                          {!songPickerLoad && !songPickerErr && songPickerList.length === 0 && (
                            <div style={{fontSize:13,opacity:.6,padding:"6px 0",fontStyle:"italic"}}>No songs found.</div>
                          )}
                          {songPickerList.length > 0 && (
                            <div style={{maxHeight:320,overflowY:"auto",display:"flex",flexDirection:"column",gap:2}}>
                              {songPickerList.map(function(s){
                                return (
                                  <button key={s.index} onClick={function(){ jumpToSong(s.index); }}
                                    style={{textAlign:"left",padding:"8px 12px",background:"transparent",color:"#000",border:"1px solid rgba(210,197,175,.1)",borderRadius:4,cursor:"pointer",fontSize:14,fontFamily:"'Crimson Pro',serif",display:"flex",justifyContent:"space-between",alignItems:"center"}}
                                    onMouseEnter={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.1)"; e.currentTarget.style.borderColor = "rgba(200,162,118,.3)"; }}
                                    onMouseLeave={function(e){ e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "rgba(210,197,175,.1)"; }}>
                                    <span><span style={{opacity:.4,marginRight:8}}>{s.index + 1}.</span>{s.title}</span>
                                    <span style={{opacity:.4,fontSize:12}}>▶</span>
                                  </button>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {fErr && <p style={{color:"#9d4630",fontSize:13,lineHeight:1.5}}>{fErr}</p>}
                  <button className="btn-g" onClick={function(){ setMode(""); }}>← Back</button>
                </div>
              </div>
            )}

            {/* ── Frequency Vocab Bank (🗂️ Vocab) ───────────────────────────
                Gated entirely by local state — no `started`, same pattern as
                Grammar below. No AI at runtime: every word, gloss, aspect
                pair, and example sentence was baked into the static JSON
                files under /vocab/blocks/ ahead of time. */}
            {/* Unreachable while WORDBANK_ENABLED is false — the menu card
                that set this mode is gone. Kept so re-enabling is one flag. */}
            {WORDBANK_ENABLED && mode === "wordbank" && (
              <div className="ss">
                <div className="sico" style={{color:"#c4955a"}}>🗂️</div>
                <h1 className="sti">Vocab</h1>

                {!wbIndex && <p className="sde">Loading word bank…</p>}

                {wbIndex && wbScreen === "landing" && (function() {
                  var meta = wbIndex.blocks[wbBlockNum - 1];
                  var stats = wbBlockStats();
                  var allDone = wbCards && stats.total > 0 && stats.done === stats.total;
                  var totalMastered = Object.keys(wbProgress).filter(function(k){ return wbProgress[k].mastered; }).length;
                  var isLastBlock = wbBlockNum >= wbIndex.blocks.length;
                  return (
                    <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:14,alignItems:"center"}}>
                      <p className="sde">
                        {wbIndex.totalCards} words total, ranked by real-world frequency — imperfective/perfective
                        verb pairs count as one word. {totalMastered} mastered so far.
                      </p>
                      <div style={{width:"100%",background:"rgba(210,197,175,.08)",border:"1px solid rgba(210,197,175,.18)",borderRadius:10,padding:"16px 20px"}}>
                        <div style={{fontSize:16,fontWeight:600,marginBottom:4}}>Block {wbBlockNum} of {wbIndex.blocks.length}</div>
                        <div style={{fontSize:13,opacity:.7,marginBottom:10}}>words ranked #{meta ? meta.rankMin : "?"}–#{meta ? meta.rankMax : "?"}</div>
                        <div style={{fontSize:14}}>{stats.done} / {stats.total} mastered in this block</div>
                      </div>
                      {allDone ? (
                        <button className="btn-p" disabled={isLastBlock} onClick={wbNextBlock}>
                          {isLastBlock ? "All blocks complete! 🎉" : "Block complete! Continue to Block " + (wbBlockNum + 1) + " →"}
                        </button>
                      ) : (
                        <button className="btn-p" disabled={wbLoading || !wbCards || !wbCards.length} onClick={wbStart}>
                          {wbLoading ? "Loading…" : "Start Block " + wbBlockNum}
                        </button>
                      )}
                      <div style={{display:"flex",gap:8,width:"100%"}}>
                        <button className="btn-g" style={{flex:1}} disabled={wbBlockNum<=1} onClick={wbPrevBlock}>← Prev block</button>
                        <button className="btn-g" style={{flex:1}} disabled={isLastBlock} onClick={wbNextBlock}>Next block →</button>
                      </div>
                    </div>
                  );
                })()}

                {wbIndex && wbScreen === "quiz" && wbCur && (function() {
                  var curStreak = (wbProgress[wbCur.card.id] && wbProgress[wbCur.card.id].streak) || 0;
                  var speakText = wbCur.card.aspectPair ? (wbCur.card.impf + ", " + wbCur.card.pf) : wbCur.card.ru;
                  return (
                    <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:16,alignItems:"center"}}>
                      <div style={{fontSize:12,opacity:.6}}>Block {wbBlockNum} · {wbBlockStats().done}/{wbBlockStats().total} mastered</div>
                      <div style={{display:"flex",alignItems:"center",gap:10}}>
                        <span style={{fontSize:28,fontFamily:"'Playfair Display',serif"}}>{wbCur.card.ru}</span>
                        <button className="ttsbtn" onClick={function(){ speakMsg(speakText, "wb-" + wbCur.card.id); }} title="Listen">🔊</button>
                      </div>
                      <div style={{fontSize:11,opacity:.55,textTransform:"uppercase",letterSpacing:.5}}>
                        {wbCur.card.pos}{wbCur.card.aspectPair ? " · aspect pair" : ""} · {curStreak}/10 correct in a row
                      </div>
                      <div style={{width:"100%",display:"flex",flexDirection:"column",gap:8}}>
                        {wbCur.options.map(function(opt, oi) {
                          var isCorrect = opt === wbCur.correct;
                          var showState = wbSel !== null;
                          var style = { textAlign: "left" };
                          if (showState && isCorrect) { style.background = "rgba(90,150,90,.25)"; style.borderColor = "rgba(90,150,90,.6)"; }
                          if (showState && wbSel === opt && !isCorrect) { style.background = "rgba(157,70,48,.2)"; style.borderColor = "rgba(157,70,48,.6)"; }
                          return (
                            <button key={oi} className="btn-g" style={style} disabled={showState} onClick={function(){ wbAnswer(opt); }}>{opt}</button>
                          );
                        })}
                      </div>
                      {wbSel && (
                        <div style={{fontSize:13,fontStyle:"italic",color:"rgba(0,0,0,.6)",textAlign:"center"}}>
                          {wbCur.card.example_ru} <span style={{opacity:.7}}>— {wbCur.card.example_en}</span>
                          {wbJustMastered === wbCur.card.id && <div style={{color:"#5a965a",fontWeight:600,marginTop:6,fontStyle:"normal"}}>✓ Mastered — moved out of rotation!</div>}
                        </div>
                      )}
                      <button className="ab" onClick={wbKnowIt} title="Skip straight to mastered">I already know this word →</button>
                      <button className="btn-g" onClick={function(){ setWbScreen("landing"); setWbCur(null); setWbSel(null); }}>← Back to block overview</button>
                    </div>
                  );
                })()}

                <button className="btn-g" onClick={function(){ setMode(""); }}>← Back</button>
              </div>
            )}

            {/* ── Grammar reference (📚 Grammar) ────────────────────────────
                Three sub-states, gated entirely by local state — no `started`:
                  1. No level picked    → show level dropdown + intro
                  2. Level picked, no topic → show topic dropdown for that level
                  3. Topic picked → show the reference page for that topic
                Picking a level keeps the user inside grammar mode; picking the
                "← Back" buttons walks back one step at a time. */}
            {mode === "grammar" && !gramTopicId && (
              <div className="ss">
                <div className="sico" style={{color:"#c4955a"}}>📚</div>
                <h1 className="sti">Grammar Reference</h1>
                <p className="sde">Pick your level, then choose a topic. Rules and examples on every page.</p>

                {gramErr && <p style={{color:"#9d4630",fontSize:13,lineHeight:1.5,maxWidth:500}}>{gramErr}</p>}

                {curriculum && (
                  <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:14}}>
                    {/* Cross-level search — when this has text, it replaces the level/topic
                        dropdowns with a flat list of matching topics from every level.
                        Matches against title, subtitle, all bullets, and example text. */}
                    <div style={{position:"relative"}}>
                      <input
                        type="text"
                        value={gramSearch}
                        onChange={function(e){ setGramSearch(e.target.value); }}
                        placeholder="🔍 Search all levels (e.g. 'case', 'aspect', 'motion')"
                        style={{width:"100%",padding:"10px 36px 10px 14px",fontSize:14,background:"rgba(210,197,175,.05)",border:"1px solid rgba(210,197,175,.15)",borderRadius:8,color:"#000",fontFamily:"'Crimson Pro',serif"}}
                      />
                      {gramSearch && (
                        <button
                          onClick={function(){ setGramSearch(""); }}
                          title="Clear search"
                          style={{position:"absolute",right:6,top:"50%",transform:"translateY(-50%)",background:"none",border:"none",color:"rgba(0,0,0,.5)",cursor:"pointer",fontSize:18,padding:"2px 8px"}}>×</button>
                      )}
                    </div>

                    {gramSearch.trim() ? (function() {
                      // Search active — show flat result list across all levels.
                      var q = gramSearch.trim().toLowerCase();
                      var matches = curriculum.topics.filter(function(t) {
                        if ((t.title || "").toLowerCase().indexOf(q) !== -1) return true;
                        if ((t.subtitle || "").toLowerCase().indexOf(q) !== -1) return true;
                        var sections = t.sections || [];
                        for (var si = 0; si < sections.length; si++) {
                          var sec = sections[si];
                          if ((sec.heading || "").toLowerCase().indexOf(q) !== -1) return true;
                          var items = sec.items || [];
                          for (var ii = 0; ii < items.length; ii++) {
                            var item = items[ii];
                            if (typeof item === "string") {
                              if (item.toLowerCase().indexOf(q) !== -1) return true;
                            } else if (item) {
                              if ((item.ru || "").toLowerCase().indexOf(q) !== -1) return true;
                              if ((item.en || "").toLowerCase().indexOf(q) !== -1) return true;
                            }
                          }
                        }
                        return false;
                      });
                      // Sort by level so results group naturally (A1 → C2).
                      var levelOrder = curriculum.levels.map(function(L){ return L.code; });
                      matches.sort(function(a, b) {
                        return levelOrder.indexOf(a.level) - levelOrder.indexOf(b.level);
                      });
                      return (
                        <>
                          <span className="slbl">
                            {matches.length === 0 ? "No matches" : matches.length + " result" + (matches.length === 1 ? "" : "s") + " across all levels"}
                          </span>
                          {matches.length > 0 && (
                            <div style={{display:"flex",flexDirection:"column",gap:1,background:"rgba(210,197,175,.04)",border:"1px solid rgba(210,197,175,.1)",borderRadius:8,overflow:"hidden",maxHeight:340,overflowY:"auto"}}>
                              {matches.map(function(t) {
                                return (
                                  <button
                                    key={t.id}
                                    onClick={function(){ setGramTopicId(t.id); }}
                                    style={{textAlign:"left",background:"none",border:"none",borderBottom:"1px solid rgba(210,197,175,.06)",padding:"12px 14px",cursor:"pointer",color:"#000",fontFamily:"'Crimson Pro',serif",display:"flex",alignItems:"flex-start",gap:12,transition:"background .12s"}}
                                    onMouseEnter={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.06)"; }}
                                    onMouseLeave={function(e){ e.currentTarget.style.background = "none"; }}>
                                    <span style={{fontSize:11,fontWeight:600,letterSpacing:1.5,color:"#c4955a",background:"rgba(200,162,118,.12)",padding:"3px 7px",borderRadius:4,flexShrink:0,marginTop:1}}>{t.level}</span>
                                    <span style={{display:"flex",flexDirection:"column",gap:2,flex:1,minWidth:0}}>
                                      <span style={{fontSize:15,fontWeight:500,color:"#000"}}>{t.title}</span>
                                      {t.subtitle && <span style={{fontSize:12,fontStyle:"italic",color:"rgba(0,0,0,.55)",lineHeight:1.45}}>{t.subtitle}</span>}
                                    </span>
                                  </button>
                                );
                              })}
                            </div>
                          )}
                          {matches.length === 0 && (
                            <p style={{fontSize:13,fontStyle:"italic",color:"rgba(0,0,0,.5)",textAlign:"center",padding:"12px 0"}}>
                              Nothing matched "{gramSearch}". Try a different word, or clear the search to browse by level.
                            </p>
                          )}
                        </>
                      );
                    })() : (
                      // No search — show the normal level/topic dropdown picker.
                      <div className="tsel" style={{margin:0}}>
                        <span className="slbl">Your level</span>
                        <select value={gramLevel} onChange={function(e){ setGramLevel(e.target.value); }}>
                          <option value="" disabled>— select a CEFR level —</option>
                          {curriculum.levels.map(function(L) {
                            return <option key={L.code} value={L.code}>{L.name}</option>;
                          })}
                        </select>
                        {gramLevel && (function() {
                          var L = curriculum.levels.find(function(x){ return x.code === gramLevel; });
                          var topicsHere = curriculum.topics.filter(function(t){ return t.level === gramLevel; });
                          return (
                            <>
                              {L && L.description && (
                                <p style={{fontSize:13,fontStyle:"italic",color:"rgba(0,0,0,.55)",margin:"4px 2px 0",fontFamily:"'Crimson Pro',serif",lineHeight:1.5}}>{L.description}</p>
                              )}
                              <span className="slbl" style={{marginTop:14}}>Topic ({topicsHere.length} available)</span>
                              <select
                                value=""
                                onChange={function(e){
                                  var id = e.target.value;
                                  if (id) setGramTopicId(id);
                                  e.target.value = "";
                                }}>
                                <option value="" disabled>📖 Choose a topic…</option>
                                {topicsHere.map(function(t) {
                                  return <option key={t.id} value={t.id}>{t.title}</option>;
                                })}
                              </select>
                            </>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                )}

                {!curriculum && !gramErr && <p style={{color:"rgba(0,0,0,.55)",fontStyle:"italic"}}>Loading curriculum…</p>}

                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:8,marginTop:18}}>
                  <button className="btn-g" onClick={function(){ setMode(""); setGramLevel(""); setGramSearch(""); }}>← Back</button>
                </div>
              </div>
            )}

            {mode === "grammar" && gramTopicId && curriculum && (function() {
              var topic = curriculum.topics.find(function(t){ return t.id === gramTopicId; });
              if (!topic) {
                return (
                  <div className="ss">
                    <p style={{color:"#9d4630"}}>Topic not found.</p>
                    <button className="btn-g" onClick={function(){ setGramTopicId(""); }}>← Back to topics</button>
                  </div>
                );
              }
              // Topics in the same level, used for "Next topic" navigation.
              var siblings = curriculum.topics.filter(function(t){ return t.level === topic.level; });
              var thisIdx = siblings.findIndex(function(t){ return t.id === topic.id; });
              var prev = thisIdx > 0 ? siblings[thisIdx - 1] : null;
              var next = thisIdx < siblings.length - 1 ? siblings[thisIdx + 1] : null;

              return (
                <div className="gramref">
                  <div className="gramref-hdr">
                    <button className="ttsbtn" onClick={function(){ setGramTopicId(""); }}>← All {topic.level} topics</button>
                    <div style={{display:"flex",alignItems:"center",gap:10}}>
                      {(function(){
                        var saved = savedTopics.indexOf(topic.id) !== -1;
                        return (
                          <button
                            className="ttsbtn"
                            title={saved ? "Already saved — click to remove from Grammar tab" : "Save to Grammar tab for quick review"}
                            onClick={function(){ saved ? rmTopic(topic.id) : addTopic(topic.id); }}
                            style={saved ? {color:"#2f5a2a",borderColor:"rgba(154,178,142,.4)"} : null}>
                            {saved ? "✓ Saved" : "📚 Save topic"}
                          </button>
                        );
                      })()}
                      <span style={{color:"rgba(0,0,0,.4)",fontSize:12,letterSpacing:1.5,textTransform:"uppercase"}}>{topic.level}</span>
                    </div>
                  </div>

                  <div className="gramref-body">
                    <h1 style={{fontFamily:"'Playfair Display',serif",fontSize:32,fontWeight:700,color:"#c4955a",marginBottom:6,lineHeight:1.15}}>{topic.title}</h1>
                    {topic.subtitle && <p style={{fontStyle:"italic",fontSize:16,color:"rgba(0,0,0,.65)",marginBottom:24,fontFamily:"'Crimson Pro',serif",lineHeight:1.5}}>{topic.subtitle}</p>}

                    {(topic.sections || []).map(function(sec, si) {
                      return (
                        <section key={si} style={{marginBottom:22}}>
                          {sec.heading && <h2 style={{fontFamily:"'Playfair Display',serif",fontSize:14,fontWeight:700,color:"rgba(0,0,0,.5)",textTransform:"uppercase",letterSpacing:2,marginBottom:10,paddingBottom:6,borderBottom:"1px solid rgba(210,197,175,.08)"}}>{sec.heading}</h2>}
                          {sec.type === "bullets" && (
                            <ul style={{listStyle:"none",padding:0,margin:0,display:"flex",flexDirection:"column",gap:8}}>
                              {(sec.items || []).map(function(item, ii) {
                                return (
                                  <li key={ii} style={{paddingLeft:18,position:"relative",lineHeight:1.55,fontSize:15}}>
                                    <span style={{position:"absolute",left:0,top:0,color:"#c4955a"}}>•</span>
                                    {item}
                                  </li>
                                );
                              })}
                            </ul>
                          )}
                          {sec.type === "examples" && (
                            <div style={{display:"flex",flexDirection:"column",gap:14}}>
                              {(sec.items || []).map(function(ex, ii) {
                                var ru = typeof ex === "string" ? ex : (ex.ru || "");
                                var en = typeof ex === "string" ? "" : (ex.en || "");
                                return (
                                  <div key={ii} style={{borderLeft:"2px solid rgba(200,162,118,.35)",paddingLeft:14,display:"flex",flexDirection:"column",gap:3}}>
                                    <div style={{display:"flex",alignItems:"flex-start",gap:8}}>
                                      <span style={{fontSize:16,lineHeight:1.45,flex:1}}>{ru}</span>
                                      {ru && (
                                        <button
                                          className="ttsbtn"
                                          style={{height:22,fontSize:11,flexShrink:0}}
                                          onClick={function(){ speakMsg(ru, "gram-" + topic.id + "-" + si + "-" + ii); }}
                                          title="Listen">
                                          🔊
                                        </button>
                                      )}
                                    </div>
                                    {en && <span style={{fontStyle:"italic",fontSize:13,color:"rgba(0,0,0,.55)",fontFamily:"'Crimson Pro',serif",lineHeight:1.5}}>{en}</span>}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </section>
                      );
                    })}

                    <div className="gramref-nav">
                      <button
                        className="btn-g"
                        style={{flex:1,opacity: prev ? 1 : 0.35, cursor: prev ? "pointer" : "default"}}
                        disabled={!prev}
                        onClick={function(){ if (prev) { setGramTopicId(prev.id); window.scrollTo(0,0); } }}>
                        {prev ? "← " + prev.title : "← Previous"}
                      </button>
                      <button
                        className="btn-g"
                        style={{flex:1,opacity: next ? 1 : 0.35, cursor: next ? "pointer" : "default"}}
                        disabled={!next}
                        onClick={function(){ if (next) { setGramTopicId(next.id); window.scrollTo(0,0); } }}>
                        {next ? next.title + " →" : "Next →"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()}

            {started && isLit && (
              <div className="lit-wrap">
                <div className="lit-top">
                  <button className={"ltab"+(lview==="read"?" on":"")} onClick={function(){ setLview("read"); }}>📖 Read</button>
                  <button className={"ltab"+(lview==="nav"?" on":"")} onClick={function(){ setLview("nav"); }}>🗂 Chapters</button>
                  <button className={"ltab"+(lview==="search"?" on":"")} onClick={function(){ setLview("search"); }}>🔍 Search</button>
                  {exData && (exData.cases||[]).length > 0 && <button className={"ltab"+(lview==="exercises"?" on":"")} onClick={function(){ setLview("exercises"); }}>📝 Exercises</button>}
                  {/* Page + chapter nav moved up here so they stay visible
                      while the floating audio bar covers the bottom of the page. */}
                  {lview === "read" && (
                    <div className="lit-top-nav">
                      {totalPages > 1 && (<>
                      <button className="lnb-inline" style={{fontSize:15,padding:"8px 14px"}} onClick={function(){ if (pidx > 0) navPage(pidx - 1); }} disabled={loading || pidx <= 0} title="Previous page">‹ Previous Page</button>
                      <button className="lnb-inline p" style={{fontSize:15,padding:"8px 14px"}} onClick={function(){ if (pidx < totalPages - 1) navPage(pidx + 1); }} disabled={loading || pidx >= totalPages - 1} title="Next page">Next Page ›</button>
                      </>)}
                      {chapters.length > 1 && (
                        <>
                          <button className="lnb-inline ch" style={{fontSize:15,padding:"8px 14px"}} onClick={function(){ if (cidx > 0) navLit(cidx-1); }} disabled={loading || cidx <= 0} title={singlePageMode ? "Previous song" : "Previous chapter"}>‹ {singlePageMode ? "Previous Song" : "Previous Chapter"}</button>
                          <button className="lnb-inline ch" style={{fontSize:15,padding:"8px 14px"}} onClick={function(){ if (cidx < chapters.length - 1) navLit(cidx+1); }} disabled={loading || cidx >= chapters.length - 1} title={singlePageMode ? "Next song" : "Next chapter"}>{singlePageMode ? "Next Song" : "Next Chapter"} ›</button>
                        </>
                      )}
                      <button className="lnb-inline lbm-inline" onClick={function(){ setCbm(cidx); }} title="Bookmark this chapter">📌</button>
                    </div>
                  )}
                  <div className="lprog">
                    <span className="lpct">
                      {singlePageMode
                        ? <>Song {cidx+1}/{chapters.length} · {pct}%</>
                        : <>Ch. {cidx+1}/{chapters.length}{totalPages > 1 ? " · Page " + (pidx+1) + "/" + totalPages : ""} · {pct}%</>}
                    </span>
                    <div className="lpbar"><div className="lpfill" style={{width:pct+"%"}}/></div>
                  </div>
                </div>

                {lview==="read" && (
                  <>
                    {renderVoicePicker()}

                    <div className="lit-body">
                      <div className={"lit-left" + (noAIMode ? " noai" : "")}>
                        {/* Book title shown small above the chapter heading so the reader always knows
                            which book they're in, even after navigating mid-chapter. */}
                        {bookMeta.title && (
                          <div style={{fontFamily:"'Crimson Pro',serif",fontStyle:"italic",fontSize:13,color:"rgba(0,0,0,.45)",marginBottom:4,letterSpacing:.3}}>
                            {bookLabel(bookMeta)}
                          </div>
                        )}
                        <div className="lhdr">
                          {singlePageMode
                            ? <>Song {cidx+1} of {chapters.length} · click any word to define</>
                            : <>Chapter {cidx+1} of {chapters.length} · click any word to define</>}
                        </div>
                        {curChapter.heading && (
                          <div className="lch-heading" style={{display:"flex",alignItems:"center",gap:12,flexWrap:"wrap"}}>
                            <span>{curChapter.heading}</span>
                            {curChapter.youtubeUrl && (
                              <a href={curChapter.youtubeUrl} target="_blank" rel="noopener noreferrer"
                                title="Listen on YouTube"
                                style={{fontSize:12,color:"rgba(0,0,0,.7)",textDecoration:"none",padding:"4px 10px",border:"1px solid rgba(210,197,175,.25)",borderRadius:4,fontFamily:"'Inter',sans-serif"}}>
                                🎵 Listen on YouTube ↗
                              </a>
                            )}
                          </div>
                        )}
                        {proseEn && proseEn._note && pidx === 0 && (
                          <div className="bible-en" style={{margin:"0 0 18px",padding:"10px 14px",border:"1px solid rgba(196,149,90,.35)",borderRadius:10,background:"rgba(196,149,90,.06)",fontSize:"0.92em"}}>
                            {proseEn._note}
                          </div>
                        )}
                        <div className="ltxt">{renderLit(curChapter.text)}</div>
                      </div>
                    </div>

                    {/* Floating audio player — always visible at bottom of viewport
                        while reading. In TTS mode plays sentence-by-sentence via
                        Azure Dmitry. In Audiobook mode (when the book has an
                        audiobook for the current chapter) streams a real
                        recording, one file per chapter or act. */}
                    {audioSentences.length > 0 && (TTS_ENABLED || audiobookData) && (
                      <div className="faudio">
                        {/* No skip buttons: scrub with the seek bar, or click
                            any word in the text and choose "Play from here". */}
                        <button className={"faudio-btn faudio-play"} onClick={audioPlayPause}
                          disabled={audioFetching}
                          title={audioPlaying ? "Pause" : "Play"}>
                          {audioFetching ? "…" : (audioPlaying ? "⏸" : "▶")}
                        </button>
                        <span className="faudio-status">
                          {/* Audiobook mode has a scrubber and a clock, so the
                              sentence counter would just be a number that no
                              longer tracks anything. TTS mode still plays
                              sentence by sentence, so it keeps the counter. */}
                          {audiobookMode && audiobookData
                            ? <span className="faudio-narrator">🎧 {audiobookData.narrator || "Audiobook"}</span>
                            : <>Sentence {audioIdx + 1} / {audioSentences.length}</>}
                        </span>
                        {audiobookMode && audiobookData && (
                          <>
                            <input className="faudio-seek" type="range" min="0"
                              max={abDur || 0} step="0.1" value={abCur > (abDur || 0) ? (abDur || 0) : abCur}
                              title="Scrub"
                              onChange={function(e){
                                var t = parseFloat(e.target.value) || 0;
                                if (audiobookAudioRef.current) { try { audiobookAudioRef.current.currentTime = t; } catch(_e) {} }
                                setAbCur(t);
                              }} />
                            <span className="faudio-clock">{fmtClock(abCur)} / {fmtClock(abDur)}</span>
                          </>
                        )}
                        {TTS_ENABLED && audiobookData && (
                          <button className={"faudio-mode" + (audiobookMode ? " active" : "")}
                            onClick={function(){
                              // Toggle modes. Stop whatever's playing first; both
                              // playback paths share the audio bar UI but not the
                              // underlying audio element.
                              if (audioPlayingRef.current) {
                                if (audiobookModeRef.current) pauseAudiobook();
                                else if (audioElemRef.current) {
                                  try { audioElemRef.current.pause(); } catch(e) {}
                                }
                              }
                              clearSentenceHighlight();
                              setAudioPlaying(false); audioPlayingRef.current = false;
                              setAudiobookMode(!audiobookMode);
                            }}
                            title={audiobookMode ? "Switch to the built-in voice" : "Switch to audiobook narrator"}>
                            {audiobookMode ? "🎧" : "🤖"}
                          </button>
                        )}
                        <button className="faudio-speed"
                          onClick={function(){ setAudioSpeedIdx((audioSpeedIdx + 1) % SPEED_OPTIONS.length); }}
                          title={"Playback speed (TTS mode only). Current: " + SPEED_OPTIONS[audioSpeedIdx].label}
                          disabled={!TTS_ENABLED || (audiobookMode && !!audiobookData)}>
                          {SPEED_OPTIONS[audioSpeedIdx].label}
                        </button>
                      </div>
                    )}
                  </>
                )}

                {lview==="nav" && (
                  <div className="navpanel">
                    {(function(){
                      // Build a nav tree from chapter headings split on " — ": the last segment is
                      // the chapter label, earlier segments are collapsible tiers (1 seg = flat,
                      // 2 = Part>Chapter like Anna Karenina, 3 = Testament>Book>Chapter for the Bible).
                      var SEP = " — ";
                      var maxDepth = 1;
                      var navItems = chapters.map(function(ch, i){
                        var segs = (ch.heading || "").split(/\s+[\u2013—]\s+/);
                        if (segs.length > maxDepth) maxDepth = segs.length;
                        return { idx: i, segs: segs, ch: ch };
                      });
                      if (maxDepth <= 1) {
                        return chapters.map(function(ch, i){
                          return (
                            <div key={i} className={"lcard"+(i===cidx?" cur":"")} onClick={function(){ setLview("read"); navLit(i); }}>
                              <div className="lcn">{i+1}{i===cbm?" 📌":""}{i===cidx?" ◀":""}</div>
                              <div className="lchead">{ch.heading}</div>
                              <div className="lcp">{ch.text.slice(0,80)}…</div>
                            </div>
                          );
                        });
                      }
                      var navRoot = { children: {}, order: [], chapters: [], key: "" };
                      navItems.forEach(function(it){
                        var node = navRoot, kp = "";
                        var groupSegs = it.segs.slice(0, it.segs.length - 1);
                        for (var gsi = 0; gsi < groupSegs.length; gsi++){
                          var seg = groupSegs[gsi];
                          kp = kp ? kp + SEP + seg : seg;
                          if (!node.children[seg]) { node.children[seg] = { name: seg, key: kp, children: {}, order: [], chapters: [] }; node.order.push(seg); }
                          node = node.children[seg];
                        }
                        node.chapters.push({ idx: it.idx, name: it.segs[it.segs.length - 1], ch: it.ch });
                      });
                      var curSegs = ((chapters[cidx] && chapters[cidx].heading) || "").split(/\s+[\u2013—]\s+/);
                      var curKeys = {}; var ckp = "";
                      for (var cki = 0; cki < curSegs.length - 1; cki++){ ckp = ckp ? ckp + SEP + curSegs[cki] : curSegs[cki]; curKeys[ckp] = true; }
                      var navOpen = function(key){ return (expandedNav && (key in expandedNav)) ? expandedNav[key] : !!curKeys[key]; };
                      var navToggle = function(key){ var was = navOpen(key); var next = {}; for (var k in (expandedNav||{})) next[k] = expandedNav[k]; next[key] = !was; setExpandedNav(next); };
                      var navHasCur = function(node){
                        if (node.chapters.some(function(c){ return c.idx === cidx; })) return true;
                        return node.order.some(function(s){ return navHasCur(node.children[s]); });
                      };
                      var renderNode = function(node, depth){
                        var open = navOpen(node.key);
                        var cur = navHasCur(node);
                        return (
                          <div key={node.key}>
                            <div onClick={function(){ navToggle(node.key); }}
                              style={{ cursor:"pointer", padding:"10px 14px", marginTop: depth===0 ? "8px" : "4px", marginLeft:(depth*14)+"px", background: cur ? "rgba(255,200,120,0.12)" : "rgba(255,255,255,0.06)", borderRadius:"8px", display:"flex", alignItems:"center", justifyContent:"space-between", gap:"10px", fontWeight: depth===0 ? 700 : 600, fontSize: depth===0 ? "1.06em" : "1em", userSelect:"none" }}>
                              <span><span style={{display:"inline-block", width:"1.4em", opacity:0.7}}>{open ? "▾" : "▸"}</span>{node.name}</span>
                              <span style={{opacity:0.55, fontSize:"0.85em", fontWeight:400}}>{cur ? "· текущая" : ""}</span>
                            </div>
                            {open && node.order.map(function(s){ return renderNode(node.children[s], depth+1); })}
                            {open && node.chapters.map(function(c){
                              var i = c.idx;
                              return (
                                <div key={i} className={"lcard"+(i===cidx?" cur":"")} onClick={function(){ setLview("read"); navLit(i); }} style={{marginLeft:((depth+1)*14)+"px"}}>
                                  <div className="lcn">{i+1}{i===cbm?" 📌":""}{i===cidx?" ◀":""}</div>
                                  <div className="lchead">{c.name}</div>
                                </div>
                              );
                            })}
                          </div>
                        );
                      };
                      return navRoot.order.map(function(s){ return renderNode(navRoot.children[s], 0); });
                    })()}
                  </div>
                )}

                {lview==="search" && (
                  <>
                    <div className="lsbar">
                      <input type="text" placeholder={"Search " + (bookMeta.title || "book") + "…"} value={lsearch} onChange={function(e){ setLsearch(e.target.value); }}/>
                    </div>
                    <div className="navpanel">
                      {!lsearch && <div className="lem">Type to search the full text.</div>}
                      {lsearch && !lres.length && <div className="lem">No results for «{lsearch}»</div>}
                      {lres.map(function(i){
                        return (
                          <div key={i} className={"lcard"+(i===cidx?" cur":"")} onClick={function(){ setLsearch(""); setLview("read"); navLit(i); }}>
                            <div className="lcn">{i+1}{i===cbm?" 📌":""}</div>
                            <div className="lchead">{chapters[i].heading}</div>
                            <div className="lcp">{chapters[i].text.slice(0,100)}…</div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}

                {lview==="exercises" && exData && (exData.cases||[]).length > 0 && (
                  <div className="navpanel" style={{maxWidth:640,margin:"0 auto"}}>
                    {/* ── Category menu: Vocabulary / Grammar / Reading ──────── */}
                    {exCat === "menu" && (
                      <div style={{padding:"18px 8px"}}>
                        <div style={{textAlign:"center",marginBottom:20}}>
                          <div style={{fontSize:20,fontFamily:"'Playfair Display',serif",color:"#000",fontWeight:600}}>{(exData && exData.title) || "Exercises"}</div>
                          {exData && exData.source && <div style={{fontSize:13,color:"rgba(42,31,20,.5)",marginTop:4}}>{exData.source}</div>}
                        </div>
                        <div style={{display:"flex",flexDirection:"column",gap:14}}>
                          {/* Grammar (only when a prebuilt exercise set exists) */}
                          {exData && (<>
                          <button onClick={startCaseQuiz}
                            style={{background:"rgba(196,149,90,.12)",border:"1px solid rgba(196,149,90,.45)",color:"#000",padding:"18px 20px",borderRadius:12,cursor:"pointer",textAlign:"left",fontFamily:"'Crimson Pro',serif",transition:"all .15s"}}
                            onMouseOver={function(e){ e.currentTarget.style.background = "rgba(196,149,90,.2)"; }}
                            onMouseOut={function(e){ e.currentTarget.style.background = "rgba(196,149,90,.12)"; }}>
                            <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:6}}>
                              <span style={{fontSize:24}}>🔤</span>
                              <span style={{fontSize:18,fontWeight:600,color:"#000",fontFamily:"'Playfair Display',serif"}}>Grammar — Cases</span>
                            </div>
                            <p style={{fontSize:13,color:"rgba(42,31,20,.55)",margin:0,lineHeight:1.5}}>{(exData.cases||[]).length} questions. Pick the correct case form to fill each blank, with the English line for context.</p>
                          </button>
                          {/* Reading comprehension — DISABLED 2026-08. Generated comprehension
                              questions were unreliable, and the focus is synced audio+text reading.
                              Remove the `false &&` below to re-enable: startReadingQuiz, the
                              "reading-soon" panel and the shared quiz runner are all still intact. */}
                          {false && (function(){
                            var hasReading = exData.reading && exData.reading.length;
                            return (
                          <button onClick={hasReading ? startReadingQuiz : function(){ setExCat("reading-soon"); }}
                            style={{background:"rgba(90,133,86,.1)",border:"1px solid rgba(90,133,86,.35)",color:"#000",padding:"18px 20px",borderRadius:12,cursor:"pointer",textAlign:"left",fontFamily:"'Crimson Pro',serif",transition:"all .15s"}}
                            onMouseOver={function(e){ e.currentTarget.style.background = "rgba(90,133,86,.16)"; }}
                            onMouseOut={function(e){ e.currentTarget.style.background = "rgba(90,133,86,.1)"; }}>
                            <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:6}}>
                              <span style={{fontSize:24}}>📖</span>
                              <span style={{fontSize:18,fontWeight:600,color:"#2f5a2a",fontFamily:"'Playfair Display',serif"}}>Reading — Comprehension</span>
                              {!hasReading && <span style={{fontSize:11,color:"rgba(42,31,20,.4)",border:"1px solid rgba(42,31,20,.25)",borderRadius:20,padding:"2px 8px",fontFamily:"'Inter',sans-serif"}}>soon</span>}
                            </div>
                            <p style={{fontSize:13,color:"rgba(42,31,20,.55)",margin:0,lineHeight:1.5}}>{hasReading ? (exData.reading.length + " questions in English about what the passage says.") : "Questions about what the passage says. Coming next."}</p>
                          </button>
                            );
                          })()}
                          </>)}
                        </div>
                      </div>
                    )}

                    {/* ── Reading placeholder (only when no reading set exists) ── */}
                    {exCat === "reading-soon" && (
                      <div style={{padding:"40px 20px",textAlign:"center"}}>
                        <div style={{fontSize:40,marginBottom:12}}>📖</div>
                        <p style={{color:"rgba(42,31,20,.7)",fontSize:15,lineHeight:1.6,maxWidth:440,margin:"0 auto 24px"}}>Reading-comprehension exercises for this passage are coming soon.</p>
                        <button className="btn-g" style={{maxWidth:240}} onClick={function(){ setExCat("menu"); }}>← Back</button>
                      </div>
                    )}

                    {/* ── Quiz runner (grammar cases OR reading comprehension) ── */}
                    {(exCat === "grammar" || exCat === "reading") && (
                      <div style={{padding:"14px 4px"}}>
                        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
                          <button className="ab" onClick={function(){ setExCat("menu"); }}>← Back</button>
                          <span style={{fontSize:13,color:"rgba(42,31,20,.5)"}}>Score: {exScore} / {exIdx + (exSelected !== null ? 1 : 0)}</span>
                        </div>

                        {exIdx >= exQuestions.length ? (
                          // Results screen
                          <div style={{padding:"30px 20px",textAlign:"center"}}>
                            <div style={{fontSize:48,marginBottom:12}}>{exScore === exQuestions.length ? "🎉" : exScore >= exQuestions.length * 0.7 ? "👏" : "📚"}</div>
                            <h2 style={{fontFamily:"'Playfair Display',serif",fontSize:26,color:"#000",marginBottom:8}}>Done!</h2>
                            <p style={{fontSize:20,color:"#000",marginBottom:6}}>You got <strong style={{color:"#c4955a"}}>{exScore}</strong> of <strong>{exQuestions.length}</strong> correct.</p>
                            <p style={{fontSize:14,color:"rgba(42,31,20,.5)",marginBottom:28}}>{Math.round(exScore / exQuestions.length * 100)}%</p>
                            <div style={{display:"flex",gap:10,justifyContent:"center",flexWrap:"wrap"}}>
                              <button className="btn-p" style={{maxWidth:200}} onClick={exCat === "reading" ? startReadingQuiz : startCaseQuiz}>Try again</button>
                              <button className="btn-g" style={{maxWidth:200}} onClick={function(){ setExCat("menu"); }}>Back to exercises</button>
                            </div>
                          </div>
                        ) : (function(){
                          var q = exQuestions[exIdx];
                          var answered = exSelected !== null;
                          var wasRight = answered && exSelected === q.correct;
                          var isReading = exCat === "reading";
                          var parts = String(q.sentence || "").split("___");
                          return (
                            <div>
                              <div style={{fontSize:13,color:"rgba(42,31,20,.5)",marginBottom:14}}>Question {exIdx + 1} of {exQuestions.length}</div>

                              {isReading && (
                                <div style={{maxWidth:560,margin:"0 auto 24px"}}>
                                  {/* The Russian line to read (with a play button for the recording), then the English question below it. */}
                                  {q.ru && <div style={{display:"flex",alignItems:"flex-start",justifyContent:"center",gap:10,marginBottom:14}}>
                                    {exClipBtn("r"+exIdx, q.ru)}
                                    <div style={{fontSize:23,fontFamily:"'Crimson Pro',serif",color:"#000",textAlign:"center",lineHeight:1.55}}>{q.ru}</div>
                                  </div>}
                                  <div style={{fontSize:16,fontFamily:"'Inter',sans-serif",color:"rgba(42,31,20,.7)",textAlign:"center",lineHeight:1.5,fontWeight:600}}>{q.question}</div>
                                </div>
                              )}

                              {!isReading && (<>
                              {/* Sentence with the blank (filled with the correct form once answered) */}
                              <div style={{fontSize:26,fontFamily:"'Crimson Pro',serif",color:"#000",textAlign:"center",lineHeight:1.5,marginBottom:14}}>
                                {parts[0]}
                                <span style={{display:"inline-block",minWidth:70,textAlign:"center",fontWeight:700,color: answered ? "#2f5a2a" : "#a56a24",borderBottom:"2px solid rgba(196,149,90,.6)",padding:"0 6px"}}>
                                  {answered ? q.correct : "   "}
                                </span>
                                {parts[1] || ""}
                              </div>

                              {/* Play the recording of this sentence (blank filled with the answer). */}
                              {exClipWords && (
                                <div style={{textAlign:"center",marginBottom:14}}>
                                  {exClipBtn("g"+exIdx, (parts[0] || "") + q.correct + (parts[1] || ""))}
                                </div>
                              )}

                              {/* Lemma prompt + English translation */}
                              <div style={{textAlign:"center",marginBottom:22}}>
                                <div style={{fontSize:15,color:"rgba(42,31,20,.75)"}}>Put <strong style={{color:"#a56a24",fontSize:18}}>{q.lemma}</strong> in the correct case</div>
                                {q.translation && <div style={{fontSize:14,color:"rgba(42,31,20,.5)",fontStyle:"italic",marginTop:8}}>{q.translation}</div>}
                              </div>
                              </>)}

                              {/* Options */}
                              <div style={{display:"flex",flexDirection:"column",gap:10,maxWidth:520,margin:"0 auto"}}>
                                {q.options.map(function(opt, i) {
                                  var isCorrect = opt === q.correct;
                                  var isPicked  = opt === exSelected;
                                  var bg = "rgba(42,31,20,.05)", brd = "rgba(42,31,20,.16)", col = "#000";
                                  if (answered) {
                                    if (isCorrect)     { bg = "rgba(90,133,86,.18)"; brd = "rgba(90,133,86,.6)"; col = "#2f5a2a"; }
                                    else if (isPicked) { bg = "rgba(157,70,48,.18)"; brd = "rgba(157,70,48,.6)"; col = "#9d4630"; }
                                    else               { col = "rgba(42,31,20,.4)"; }
                                  }
                                  return (
                                    <button key={i} disabled={answered} onClick={function(){
                                      setExSelected(opt);
                                      if (isCorrect) setExScore(function(s){ return s + 1; });
                                    }} style={{background:bg,border:"1px solid "+brd,color:col,padding:"13px 18px",borderRadius:10,fontSize:18,fontFamily:"'Crimson Pro',serif",cursor: answered ? "default" : "pointer",textAlign:"left",transition:"all .15s"}}>
                                      <span style={{display:"inline-block",width:20,color:"rgba(42,31,20,.45)",fontFamily:"'Inter',sans-serif",fontSize:13}}>{String.fromCharCode(65 + i)}.</span>
                                      {opt}
                                    </button>
                                  );
                                })}
                              </div>

                              {/* Feedback: case name + explanation */}
                              {answered && (
                                <div style={{maxWidth:520,margin:"18px auto 0",background:"rgba(42,31,20,.05)",border:"1px solid rgba(42,31,20,.14)",borderRadius:10,padding:"14px 16px"}}>
                                  <div style={{fontSize:15,fontWeight:600,color: wasRight ? "#2f5a2a" : "#9d4630",marginBottom:6}}>
                                    {wasRight ? "✓ Correct" : "✗ Not quite"}{!isReading && q.case ? " — " + q.case : ""}
                                  </div>
                                  <div style={{fontSize:14,color:"rgba(42,31,20,.7)",lineHeight:1.55}}>{q.explain}</div>
                                </div>
                              )}

                              {answered && (
                                <div style={{marginTop:22,textAlign:"center"}}>
                                  <button className="btn-p" style={{maxWidth:260}} onClick={function(){
                                    setExIdx(function(i){ return i + 1; });
                                    setExSelected(null);
                                  }}>
                                    {exIdx + 1 < exQuestions.length ? "Next →" : "See results"}
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

          </div>
        )}

        {tab==="vocab" && (
          <div className="panel">
            {quizMode ? (
              // ── Quiz view ──────────────────────────────────────────────
              <>
                <div className="phdr">
                  <span className="pti">📝 Vocab Quiz</span>
                  <button className="ab" onClick={function(){ setQuizMode(false); setQuizMenu(true); }}>← Back</button>
                </div>
                {quizQuestions.length === 0 ? (
                  <div style={{padding:"40px 20px",textAlign:"center"}}>
                    <p style={{color:"rgba(0,0,0,.7)",fontSize:15,lineHeight:1.6,maxWidth:480,margin:"0 auto"}}>{quizSkipNote}</p>
                    <button className="btn-g" style={{marginTop:24,maxWidth:280}} onClick={function(){ setQuizMode(false); }}>Back to vocab list</button>
                  </div>
                ) : quizIdx >= quizQuestions.length ? (
                  // Final score screen
                  <div style={{padding:"40px 20px",textAlign:"center"}}>
                    <div style={{fontSize:48,marginBottom:12}}>{quizScore === quizQuestions.length ? "🎉" : quizScore >= quizQuestions.length * 0.7 ? "👏" : "📚"}</div>
                    <h2 style={{fontFamily:"'Playfair Display',serif",fontSize:26,color:"#c4955a",marginBottom:8}}>Quiz Complete!</h2>
                    <p style={{fontSize:20,color:"#000",marginBottom:6}}>You got <strong style={{color:"#c4955a"}}>{quizScore}</strong> of <strong>{quizQuestions.length}</strong> correct.</p>
                    <p style={{fontSize:14,color:"rgba(0,0,0,.5)",marginBottom:28}}>{Math.round(quizScore / quizQuestions.length * 100)}%</p>
                    {quizSkipNote && <p style={{fontSize:12,color:"rgba(0,0,0,.4)",fontStyle:"italic",marginBottom:20,maxWidth:440,margin:"0 auto 20px"}}>{quizSkipNote}</p>}
                    <div style={{display:"flex",gap:10,justifyContent:"center",flexWrap:"wrap"}}>
                      <button className="btn-p" style={{maxWidth:200}} onClick={startQuiz}>Retake quiz</button>
                      <button className="btn-g" style={{maxWidth:200}} onClick={function(){ setQuizMode(false); setQuizMenu(false); }}>Back to vocab list</button>
                    </div>
                  </div>
                ) : (
                  // Current question
                  <div style={{padding:"20px 4px"}}>
                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:18,fontSize:13,color:"rgba(0,0,0,.5)"}}>
                      <span>Question {quizIdx + 1} of {quizQuestions.length}</span>
                      <span>Score: {quizScore} / {quizIdx + (quizSelected !== null ? 1 : 0)}</span>
                    </div>
                    {/* The Russian word being quizzed */}
                    <div style={{textAlign:"center",marginBottom:8}}>
                      <span style={{fontSize:12,color:"rgba(0,0,0,.45)",textTransform:"uppercase",letterSpacing:1.5}}>{quizQuestions[quizIdx].pos}</span>
                    </div>
                    <div style={{fontSize:42,fontFamily:"'Playfair Display',serif",color:"#c4955a",textAlign:"center",marginBottom:30,fontWeight:600}}>
                      {quizQuestions[quizIdx].word}
                    </div>
                    {/* Multiple choice options */}
                    <div style={{display:"flex",flexDirection:"column",gap:10,maxWidth:560,margin:"0 auto"}}>
                      {quizQuestions[quizIdx].options.map(function(opt, i) {
                        var isCorrect = opt === quizQuestions[quizIdx].correct;
                        var isPicked  = opt === quizSelected;
                        var bg = "rgba(42,31,20,.04)", brd = "rgba(42,31,20,.16)", col = "#000";
                        if (quizSelected !== null) {
                          if (isCorrect)      { bg = "rgba(90,133,86,.18)";  brd = "rgba(90,133,86,.6)";  col = "#2f5a2a"; }
                          else if (isPicked)  { bg = "rgba(157,70,48,.18)";  brd = "rgba(157,70,48,.6)";  col = "#9d4630"; }
                          else                { col = "rgba(0,0,0,.4)"; }
                        }
                        return (
                          <button key={i} disabled={quizSelected !== null} onClick={function(){
                            setQuizSelected(opt);
                            if (isCorrect) setQuizScore(function(s){ return s + 1; });
                          }} style={{background:bg,border:"1px solid "+brd,color:col,padding:"14px 18px",borderRadius:10,fontSize:16,fontFamily:"'Crimson Pro',serif",cursor: quizSelected !== null ? "default" : "pointer", textAlign:"left", transition:"all .15s"}}>
                            <span style={{display:"inline-block",width:20,color:"rgba(0,0,0,.45)",fontFamily:"'Inter',sans-serif",fontSize:13}}>{String.fromCharCode(65 + i)}.</span>
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                    {quizSelected !== null && (
                      <div style={{marginTop:24,textAlign:"center"}}>
                        <button className="btn-p" style={{maxWidth:280}} onClick={function(){
                          setQuizIdx(function(i){ return i + 1; });
                          setQuizSelected(null);
                        }}>
                          {quizIdx + 1 < quizQuestions.length ? "Next →" : "See results"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : quizMenu ? (
              // ── Review choice menu (Multiple Choice vs Chat Practice) ──
              <>
                <div className="phdr">
                  <span className="pti">📝 Review Vocabulary</span>
                  <button className="ab" onClick={function(){ setQuizMenu(false); }}>← Back to list</button>
                </div>
                <div style={{padding:"24px 16px",display:"flex",flexDirection:"column",gap:14,maxWidth:560,margin:"0 auto"}}>
                  <p style={{color:"rgba(0,0,0,.65)",fontSize:14,textAlign:"center",margin:"0 0 8px"}}>How would you like to practice your {vocab.length} saved {vocab.length === 1 ? "word" : "words"}?</p>
                  {/* Multiple Choice Quiz option */}
                  <button onClick={startQuiz}
                    style={{background:"rgba(200,162,118,.08)",border:"1px solid rgba(200,162,118,.3)",color:"#000",padding:"18px 20px",borderRadius:12,cursor:"pointer",textAlign:"left",fontFamily:"'Crimson Pro',serif",transition:"all .15s"}}
                    onMouseOver={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.14)"; }}
                    onMouseOut={function(e){ e.currentTarget.style.background = "rgba(200,162,118,.08)"; }}>
                    <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:6}}>
                      <span style={{fontSize:24}}>📝</span>
                      <span style={{fontSize:18,fontWeight:600,color:"#c4955a",fontFamily:"'Playfair Display',serif"}}>Multiple Choice Quiz</span>
                    </div>
                    <p style={{fontSize:13,color:"rgba(0,0,0,.55)",margin:0,lineHeight:1.5}}>Quick recall test. Each question shows a Russian word with 4 English meaning options (from same-pos vocabulary).</p>
                  </button>
                  {/* Chat Practice (live AI conversation) removed — it called
                      Gemini/Anthropic and cost money. Multiple Choice Quiz above
                      is the free, static replacement. */}
                </div>
              </>
            ) : (
              // ── Normal vocab list view ─────────────────────────────────
              <>
                <div className="phdr">
                  <span className="pti">My Vocabulary</span>
                  <div style={{display:"flex",gap:8}}>
                    {vocab.length > 0 && <button className="ab" onClick={function(){ setQuizMenu(true); }} title="Quiz yourself or practice these words in chat">📝 Review vocab</button>}
                    <button className="ab" onClick={function(){ setNRu(""); setNEn(""); setShowWord(true); }}>+ Add word</button>
                  </div>
                </div>
                {vocab.length===0 ? <p className="empty">No words saved yet.<br/>Click any Russian word to define and save it.</p>
                  : (function(){
                      // Group vocab by part of speech. Words with no pos go last under "Other".
                      var groups = {}; var order = [];
                      vocab.forEach(function(v){
                        var key = (v.pos || "").trim() || "Other";
                        if (!groups[key]) { groups[key] = []; order.push(key); }
                        groups[key].push(v);
                      });
                      // Sort: named pos groups alphabetically, "Other" always last.
                      order.sort(function(a,b){
                        if (a==="Other") return 1; if (b==="Other") return -1;
                        return a.localeCompare(b);
                      });
                      var QMIN = 10;
                      var renderCard = function(v){
                        var posLine = [v.pos, v.aspect].filter(Boolean).join(" · ");
                        var stamp = formatVocabDate(v.created || v.id);
                        return (
                          <div key={v._key||v.id||v.ru} className="icard">
                            <div className="icont">
                              <span className="ipri">{v.ru}</span>
                              {posLine && <span className="ipos">{posLine}</span>}
                              {v.en && <span className="isec">{v.en}</span>}
                              {v.grammar && <span className="igr">{v.grammar}</span>}
                              {v.example && (
                                <div className="iex">
                                  «&nbsp;{v.example}&nbsp;»
                                  {v.exampleTranslation && <div className="iext">{v.exampleTranslation}</div>}
                                </div>
                              )}
                              <div style={{display:"flex",alignItems:"center",gap:10,marginTop:6,flexWrap:"wrap"}}>
                                {stamp && <span style={{fontSize:11,color:"rgba(0,0,0,.35)",fontStyle:"italic",fontFamily:"'Crimson Pro',serif"}}>Added {stamp}</span>}
                                {v.srcBook && (
                                  <button onClick={function(){ goToSource(v); }}
                                    title={"Open " + (v.srcTitle||"source") + (typeof v.srcChapter==="number" ? " — chapter " + (v.srcChapter+1) : "")}
                                    style={{fontSize:11,background:"none",border:"none",color:"#c4955a",cursor:"pointer",fontFamily:"'Inter',sans-serif",padding:0,textDecoration:"underline"}}>
                                    ↗ {v.srcTitle ? (v.srcTitle.length>22 ? v.srcTitle.slice(0,22)+"…" : v.srcTitle) : "source"}
                                  </button>
                                )}
                              </div>
                            </div>
                            <button className="rmb" title="Remove from vocabulary" onClick={function(){ setVocab(function(p){ return p.filter(function(x){ return (x._key||x.id||x.created) !== (v._key||v.id||v.created); }); }); }}>×</button>
                          </div>
                        );
                      };
                      return (
                        <div className="ilist">
                          {order.map(function(g){
                            var words = groups[g];
                            var collapsed = !!vocabCollapsed[g];
                            var canQuiz = words.filter(function(w){ return w.en; }).length >= QMIN;
                            return (
                              <div key={g} style={{marginBottom:18}}>
                                <div style={{display:"flex",alignItems:"center",gap:10,padding:"6px 2px",borderBottom:"1px solid rgba(210,197,175,.15)",marginBottom:8}}>
                                  <button onClick={function(){ setVocabCollapsed(function(pp){ var n=Object.assign({},pp); n[g]=!n[g]; return n; }); }}
                                    style={{background:"none",border:"none",color:"#000",cursor:"pointer",fontSize:14,fontWeight:600,fontFamily:"'Inter',sans-serif",display:"flex",alignItems:"center",gap:6,flex:1,textAlign:"left",padding:0}}>
                                    <span style={{fontSize:11,opacity:.6}}>{collapsed?"\u25b6":"\u25bc"}</span>
                                    <span style={{textTransform:"capitalize"}}>{g}</span>
                                    <span style={{opacity:.5,fontWeight:400}}>({words.length})</span>
                                  </button>
                                  {canQuiz && (
                                    <button onClick={function(){ startQuiz(g); }}
                                      style={{fontSize:12,background:"#c8a276",color:"#1a1612",border:"none",borderRadius:4,padding:"4px 12px",fontWeight:600,cursor:"pointer",fontFamily:"'Inter',sans-serif"}}>
                                      Quiz
                                    </button>
                                  )}
                                </div>
                                {!collapsed && words.map(renderCard)}
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
              </>
            )}
          </div>
        )}

        {tab==="grammar" && (
          <div className="panel">
            {/* Saved curriculum topics: cards that click to open the reference page.
                Empty by default — only appears once the user has bookmarked something. */}
            {savedTopics.length > 0 && curriculum && (
              <>
                <div className="phdr"><span className="pti">Saved Topics</span></div>
                <div className="ilist" style={{marginBottom:20}}>
                  {savedTopics.map(function(id) {
                    var topic = curriculum.topics.find(function(t){ return t.id === id; });
                    if (!topic) return null; // ID exists but topic was removed from curriculum
                    return (
                      <div key={id} className="icard" style={{cursor:"pointer"}}
                        onClick={function(){ setMode("grammar"); setGramTopicId(id); setStarted(false); setMsgs([]); stopTTS(); setTab("chat"); }}>
                        <div className="icont" style={{flex:1}}>
                          <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:2}}>
                            <span style={{fontSize:10,letterSpacing:1.5,padding:"2px 6px",border:"1px solid rgba(210,197,175,.25)",borderRadius:3,color:"rgba(0,0,0,.6)"}}>{topic.level}</span>
                            <span className="ipri" style={{fontSize:15,color:"#c4955a"}}>📚 {topic.title}</span>
                          </div>
                          {topic.subtitle && <span style={{fontSize:13,fontStyle:"italic",color:"rgba(0,0,0,.55)",fontFamily:"'Crimson Pro',serif"}}>{topic.subtitle}</span>}
                        </div>
                        <button className="rmb" title="Remove from Grammar tab" onClick={function(e){ e.stopPropagation(); rmTopic(id); }}>×</button>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            <div className="phdr"><span className="pti">Grammar Tips</span><button className="ab g" onClick={function(){ setNTip(""); setShowTip(true); }}>+ Add tip</button></div>
            {tips.length===0 ? <p className="empty">No tips saved yet.<br/>Click 📝 Save tip under any tutor message, or use 📚 Grammar to bookmark a curriculum topic.</p>
              : <div className="ilist">{tips.map(function(t){
                return (
                  <div key={t.id} className="icard">
                    <div className="icont"><span className="ipri" style={{fontSize:15}}>📝 {t.tip}</span></div>
                    <button className="rmb" onClick={function(){ setTips(function(p){ return p.filter(function(x){ return x.id!==t.id; }); }); }}>×</button>
                  </div>
                );
              })}</div>}
          </div>
        )}

        {showTopic && (
          <div className="mover" onClick={function(){ setShowTopic(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">{"📖 " + (bookMeta.title || "Reading")}</span>
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowTopic(false); }}>Cancel</button>
                <button className="mconf" onClick={function(){ setShowTopic(false); setStarted(false); setMode(""); setMsgs([]); stopTTS(); }}>← Back to start</button>
              </div>
            </div>
          </div>
        )}

        {showWord && (
          <div className="mover" onClick={function(){ setShowWord(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">Add Word</span>
              <input type="text" placeholder="Russian word" value={nRu} onChange={function(e){ setNRu(e.target.value); }}/>
              <input type="text" placeholder="English translation (optional)" value={nEn} onChange={function(e){ setNEn(e.target.value); }}/>
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowWord(false); }}>Cancel</button>
                <button className="mconf" onClick={function(){ if(nRu.trim()) addV(nRu.trim(),nEn.trim()); setShowWord(false); }}>Save</button>
              </div>
            </div>
          </div>
        )}

        {showTip && (
          <div className="mover" onClick={function(){ setShowTip(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">Add Grammar Tip</span>
              <input type="text" placeholder="e.g. Genitive case after negation" value={nTip} onChange={function(e){ setNTip(e.target.value); }}/>
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowTip(false); }}>Cancel</button>
                <button className="mconf g" onClick={function(){ if(nTip.trim()) addT(nTip.trim()); setShowTip(false); }}>Save</button>
              </div>
            </div>
          </div>
        )}

        {popup && (
          <div className="pover" onClick={function(){ setPopup(null); }}>
            <div className="pop" ref={popRef} style={{top:popXY.top,left:popXY.left,width:Math.min(280,window.innerWidth-32)}} onClick={function(e){ e.stopPropagation(); }}>
              <button className="pcl" onClick={function(){ setPopup(null); }}>×</button>

              {/* Header shows the canonical form once data has loaded.
                   Pre-load (or on error) we show what the user clicked. */}
              {(function() {
                var entry = formatVocabEntry(popup.data, popup.word);
                var headline = entry.ru || popup.word;
                var clicked = (popup.word || "").trim();
                var lemma = popup.data && popup.data.lemma;
                var showClickedHint = !!(lemma && clicked && lemma !== clicked && !(/\s\/\s/.test(headline)));
                return (
                  <>
                    <div className="pwrow">
                      <div className="pw">{headline}</div>
                      <button className={"psay" + (sayState === "playing" ? " on" : "")}
                              title="Pronounce"
                              aria-label={"Pronounce " + headline}
                              onClick={function(){ sayWord(popup.data, popup.word); }}>♪</button>
                    </div>
                    {sayState === "none" && (
                      <div style={{fontSize:11,color:"rgba(0,0,0,.4)",marginBottom:6,marginTop:-2}}>
                        No audio available for this word.
                      </div>
                    )}
                    {showClickedHint && (
                      <div style={{fontSize:11,color:"rgba(0,0,0,.4)",marginBottom:6,marginTop:-2}}>
                        you clicked: {clicked}
                      </div>
                    )}
                  </>
                );
              })()}

              {popup.loading && <div className="pload">Looking up…</div>}
              {popup.error && <div className="perr">{popup.error}</div>}

              {popup.noEntry && (
                <div className="ppos" style={{marginTop:6}}>
                  Not in the dictionary — likely a proper name or an older form.
                </div>
              )}

              {popup.noEntry && isAdmin && popup.trace && (
                <div style={{fontSize:"0.68em",opacity:0.45,marginTop:4,wordBreak:"break-word"}}>
                  {popup.trace.join(" · ")}
                </div>
              )}

              {popup.noEntry && isAdmin && !curate && (
                <button className="yobtn" style={{marginTop:8}}
                        onClick={function(){ startCurate(popup.noEntry); }}>
                  + Add to glossary
                </button>
              )}

              {popup.noEntry && isAdmin && curate && (
                <div style={{display:"flex",flexDirection:"column",gap:6,marginTop:8}}>
                  <div className="ppos">Glossary entry for «{curate.word}»</div>
                  <input className="gvin" autoFocus placeholder="English definition (required)"
                         value={curate.translation}
                         onChange={function(e){ curateField("translation", e.target.value); }} />
                  <input className="gvin" placeholder="Russian gloss / synonyms (optional)"
                         value={curate.definitionRu}
                         onChange={function(e){ curateField("definitionRu", e.target.value); }} />
                  <input className="gvin" placeholder="Register, e.g. блатной жаргон"
                         value={curate.register}
                         onChange={function(e){ curateField("register", e.target.value); }} />
                  <input className="gvin" placeholder="Example sentence (optional)"
                         value={curate.example}
                         onChange={function(e){ curateField("example", e.target.value); }} />
                  <input className="gvin" placeholder="Other forms that should hit this entry, comma separated"
                         value={curate.forms}
                         onChange={function(e){ curateField("forms", e.target.value); }} />
                  {curate.err && <div className="perr">{curate.err}</div>}
                  <div style={{display:"flex",gap:6}}>
                    <button className="psave" disabled={curate.busy} onClick={saveCurate}>
                      {curate.busy ? "Saving…" : "Save to glossary"}
                    </button>
                    <button className="yobtn" onClick={function(){ setCurate(null); }}>Cancel</button>
                  </div>
                </div>
              )}

              {popup.yo && (
                <div style={{display:"flex",flexDirection:"column",gap:4,marginTop:8}}>
                  <div className="ppos" style={{marginBottom:8}}>е or ё? Tap the right spelling:</div>
                  <button className="yobtn" onClick={function(){ defWithYo(popup.yo.orig); }}>{popup.yo.orig} (keep е)</button>
                  {popup.yo.vars.map(function(v,i){ return <button key={i} className="yobtn" onClick={function(){ defWithYo(v); }}>{v} (with ё)</button>; })}
                </div>
              )}

              {!popup.loading && !popup.error && !popup.yo && !popup.noEntry && popup.data && (
                <>
                  {popup.data.definitionSource === "mt" && (
                    <div className="pmt">
                      {popup.data.mtKind === "dictionary"
                        ? "No dictionary here had this word — this is a bilingual-dictionary match from a translation engine."
                        : "No dictionary anywhere had this word. This is a machine translation — treat it as a hint, not a definition."}
                    </div>
                  )}
                  <div className="ppos">{popup.data.partOfSpeech}{popup.data.aspect ? " · " + popup.data.aspect : ""}</div>
                  {popup.data.definitionRu && <div className="pdru">{popup.data.definitionRu}</div>}
                  <div className="ptr">{popup.data.translation}</div>
                  {popup.data.grammar && <div className="pgr">{popup.data.grammar}</div>}
                  {popup.data.example && <div className="pex">{popup.data.example}{popup.data.exampleTranslation&&<div className="pext">{popup.data.exampleTranslation}</div>}</div>}
                  {popup.data.definitionSource === "yandex" && <div style={{fontSize:"0.72em",opacity:0.55,marginTop:6}}><a href="https://yandex.com/dev/dictionary/" target="_blank" rel="noreferrer" style={{color:"inherit"}}>Powered by Yandex.Dictionary</a></div>}
                  {popup.data.definitionSource === "wiktionary" && <div style={{fontSize:"0.72em",opacity:0.55,marginTop:6}}><a href={popup.data.sourceUrl || "https://en.wiktionary.org/"} target="_blank" rel="noreferrer" style={{color:"inherit"}}>Wiktionary</a>{" \u00b7 "}<a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer" style={{color:"inherit"}}>CC BY-SA 4.0</a></div>}
                  {popup.data.definitionSource === "ruwiktionary" && <div style={{fontSize:"0.72em",opacity:0.55,marginTop:6}}><a href={popup.data.sourceUrl || "https://ru.wiktionary.org/"} target="_blank" rel="noreferrer" style={{color:"inherit"}}>\u0412\u0438\u043a\u0438\u0441\u043b\u043e\u0432\u0430\u0440\u044c</a>{" \u00b7 "}<a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer" style={{color:"inherit"}}>CC BY-SA 4.0</a></div>}
                  {popup.data.definitionSource === "mt" && <div style={{fontSize:"0.72em",opacity:0.55,marginTop:6}}>{popup.data.mtProvider || "Machine translation"}</div>}
                  {popup.data.definitionSource === "glossary" && <div style={{fontSize:"0.72em",opacity:0.55,marginTop:6}}>{popup.data.sourceUrl
                    ? <a href={popup.data.sourceUrl} target="_blank" rel="noreferrer" style={{color:"inherit"}}>{popup.data.sourceNote || (SITE_NAME_LATIN + " glossary")}</a>
                    : (popup.data.sourceNote || (SITE_NAME_LATIN + " glossary"))}{isAdmin && <span style={{opacity:0.7}}>{" \u00b7 curated"}</span>}</div>}
                </>
              )}

              {/* Save uses the formatted entry: nominative for nouns, infinitive (with aspect pair) for verbs.
                   Also persists pos/grammar/example into the vocab list. */}
              {(function() {
                var entry = formatVocabEntry(popup.data, popup.word);
                return (
                  <button className="psave" onClick={function(){
                    if (entry.ru) {
                      if (popup.srcOffset != null) entry.srcOffset = popup.srcOffset;
                      addV(entry);
                    }
                    setPopup(null);
                  }}>+ Save « {entry.ru || popup.word} » to vocabulary</button>
                );
              })()}
            </div>
          </div>
        )}
      </div>
      )}
    </>
  );
}
