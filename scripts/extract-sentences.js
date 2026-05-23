#!/usr/bin/env node
/**
 * extract-sentences.js — pull one Russian sentence per line from an FB2 file
 * (or per-chapter slices of it). Used as input to align-audiobook.py.
 *
 * Usage:
 *   node scripts/extract-sentences.js public/books/novel/gogol-nose.fb2
 *     → writes gogol-nose-ch1.txt, gogol-nose-ch2.txt, ... next to the FB2
 *
 *   node scripts/extract-sentences.js path/to/book.fb2 --chapter 0 > ch1.txt
 *     → prints just chapter 0's sentences to stdout
 *
 *   node scripts/extract-sentences.js path/to/book.fb2 --whole > all.txt
 *     → prints the whole book as one long stream of sentences (use for
 *       single-file audiobooks)
 *
 * The sentence parser mirrors App.jsx's parseSentences() — same abbreviation
 * list, same boundary rules — so what this emits is exactly what the app
 * tokenises at runtime. That keeps the runtime fragment-to-sentence match
 * reliable.
 *
 * Plain text files (.txt) are also accepted as input.
 */

const fs = require("fs");
const path = require("path");

// ── Russian abbreviations (keep in sync with App.jsx) ─────────────────────────
const RU_NON_TERMINAL_ABBR = new Set([
  "г", "т", "д", "п", "е", "ч", "с", "н",
  "тт", "вв", "гг", "сс", "пр", "ст", "до",
  "стр", "рис", "табл", "напр", "тов", "акад", "проф", "имп", "ген",
  "пол", "св", "ул", "пл", "пер", "просп", "обл", "млн", "млрд",
  "тыс", "руб", "коп", "сек", "мин", "см", "мм", "км", "кг", "вып",
  "изд", "гл", "им", "век", "напис", "опубл", "род", "ум",
  "mr", "mrs", "ms", "dr", "vs", "etc"
]);

// Same boundary detection logic as App.jsx's parseSentences().
function parseSentences(text) {
  if (!text) return [];
  const sentences = [];
  const lines = text.split(/\n+/);
  for (let li = 0; li < lines.length; li++) {
    const line = lines[li].trim();
    if (!line) continue;
    let sentStart = 0;
    let pos = 0;
    while (pos < line.length) {
      const ch = line[pos];
      if (ch === "." || ch === "!" || ch === "?" || ch === "…") {
        let endTerm = pos;
        while (endTerm + 1 < line.length && /[.!?…]/.test(line[endTerm + 1])) endTerm++;
        const nextIdx = endTerm + 1;
        let isBoundary = false;
        if (nextIdx >= line.length) {
          isBoundary = true;
        } else if (!/\s/.test(line[nextIdx])) {
          isBoundary = false;
        } else {
          let k = nextIdx;
          while (k < line.length && /\s/.test(line[k])) k++;
          if (k >= line.length) {
            isBoundary = true;
          } else if (/[А-ЯЁA-Z«"„(\[—–]/.test(line[k])) {
            let wEnd = endTerm;
            while (wEnd > 0 && /[.!?…]/.test(line[wEnd - 1])) wEnd--;
            let wStart = wEnd - 1;
            while (wStart >= 0 && /[а-яёА-ЯЁa-zA-Z]/.test(line[wStart])) wStart--;
            wStart++;
            const wordBefore = line.slice(wStart, wEnd);
            const isInitial = wordBefore.length === 1 && /[А-ЯЁA-Z]/.test(wordBefore);
            const isAbbrev = wordBefore.length > 0 && RU_NON_TERMINAL_ABBR.has(wordBefore.toLowerCase());
            isBoundary = !(isInitial || isAbbrev);
          } else {
            isBoundary = false;
          }
        }
        if (isBoundary) {
          const sentText = line.slice(sentStart, endTerm + 1).trim();
          if (sentText) sentences.push(sentText);
          let sw = endTerm + 1;
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
      const lastSent = line.slice(sentStart).trim();
      if (lastSent) sentences.push(lastSent);
    }
  }
  return sentences;
}

// ── FB2 parser ───────────────────────────────────────────────────────────────
// Strips XML/HTML markup, keeps paragraph breaks, separates by <section>
// (chapter). A minimal implementation — relies on FB2's straightforward
// structure rather than a full XML library.
function stripXml(s) {
  return s
    .replace(/<\/p>/gi, "\n")
    .replace(/<\/?(?:emphasis|strong|em|b|i|u|sub|sup|stanza|v|cite|epigraph|subtitle|text-author|date)\b[^>]*>/gi, "")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(parseInt(n, 10)))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCharCode(parseInt(n, 16)))
    .replace(/[ \t]+/g, " ")
    .replace(/[ \t]*\n[ \t]*/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function parseFb2(xml) {
  // Find <body> ... </body>. (Skip <body name="notes"> etc.)
  const bodyMatch = xml.match(/<body(?:[^>]*)>([\s\S]*?)<\/body>/i);
  if (!bodyMatch) {
    // Maybe it's already plain text — return as one chapter.
    return [{ title: "", text: stripXml(xml) }];
  }
  const body = bodyMatch[1];

  // Split into <section>s. FB2 nests sections — we treat top-level sections as
  // chapters and inline subsections into their parent for simplicity.
  const sections = [];
  let depth = 0;
  let currentStart = -1;
  const sectionTagRe = /<\/?section\b[^>]*>/gi;
  let m;
  while ((m = sectionTagRe.exec(body)) !== null) {
    const tag = m[0];
    if (/^<section\b/i.test(tag)) {
      if (depth === 0) currentStart = m.index + tag.length;
      depth++;
    } else if (/^<\/section/i.test(tag)) {
      depth--;
      if (depth === 0 && currentStart >= 0) {
        sections.push(body.slice(currentStart, m.index));
        currentStart = -1;
      }
    }
  }

  if (sections.length === 0) {
    return [{ title: "", text: stripXml(body) }];
  }

  return sections.map((sec, idx) => {
    // Extract the section's title (first <title> ... </title>).
    let title = "";
    const titleMatch = sec.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    if (titleMatch) {
      title = stripXml(titleMatch[1]).replace(/\s+/g, " ").trim();
      sec = sec.replace(titleMatch[0], "");
    } else {
      title = `Chapter ${idx + 1}`;
    }
    return { title, text: stripXml(sec) };
  });
}

// ── Main ─────────────────────────────────────────────────────────────────────
function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    console.error("Usage: node extract-sentences.js <file.fb2|file.txt> [--chapter N] [--whole]");
    console.error("       (no flags = writes one file per chapter next to input)");
    process.exit(2);
  }

  const inputPath = args[0];
  const chapterArg = args.indexOf("--chapter");
  const wantChapter = chapterArg >= 0 ? parseInt(args[chapterArg + 1], 10) : null;
  const wantWhole = args.includes("--whole");

  if (!fs.existsSync(inputPath)) {
    console.error(`ERROR: file not found: ${inputPath}`);
    process.exit(2);
  }

  const raw = fs.readFileSync(inputPath, "utf-8");
  const ext = path.extname(inputPath).toLowerCase();

  let chapters;
  if (ext === ".fb2" || ext === ".xml") {
    chapters = parseFb2(raw);
  } else {
    chapters = [{ title: "", text: raw }];
  }

  if (wantWhole) {
    const allSents = [];
    chapters.forEach(c => {
      if (c.title) allSents.push(`Глава. ${c.title}`);  // marker line so narrator's chapter announcement aligns
      allSents.push(...parseSentences(c.text));
    });
    process.stdout.write(allSents.join("\n") + "\n");
    console.error(`Wrote ${allSents.length} sentences to stdout.`);
    return;
  }

  if (wantChapter !== null) {
    const c = chapters[wantChapter];
    if (!c) {
      console.error(`ERROR: chapter ${wantChapter} not found (book has ${chapters.length}).`);
      process.exit(2);
    }
    const sents = parseSentences(c.text);
    process.stdout.write(sents.join("\n") + "\n");
    console.error(`Wrote ${sents.length} sentences from chapter ${wantChapter} ("${c.title}") to stdout.`);
    return;
  }

  // Default: write per-chapter files next to the input
  const base = inputPath.replace(/\.[^.]+$/, "");
  chapters.forEach((c, idx) => {
    const sents = parseSentences(c.text);
    if (sents.length === 0) {
      console.error(`Chapter ${idx + 1} ("${c.title}"): no sentences — skipped`);
      return;
    }
    const outPath = `${base}-ch${idx + 1}.txt`;
    fs.writeFileSync(outPath, sents.join("\n") + "\n", "utf-8");
    console.error(`Chapter ${idx + 1} ("${c.title}"): wrote ${sents.length} sentences → ${outPath}`);
  });
}

main();
