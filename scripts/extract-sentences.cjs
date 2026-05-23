#!/usr/bin/env node
/**
 * extract-sentences.cjs — pull one Russian sentence per line from an FB2 file.
 * Splits by:
 *   1. nested <section> tags (deepest leaf becomes a chapter), AND
 *   2. <subtitle> markers within leaf sections (treats subtitles as chapter starts)
 *
 * Naming:
 *   - subtitle-delimited chapters within a part section: <base>-p<N>-ch<M>.txt
 *   - flat chapters without parts: <base>-ch<N>.txt
 */
const fs = require("fs");
const path = require("path");

const RU_NON_TERMINAL_ABBR = new Set([
  "г", "т", "д", "п", "е", "ч", "с", "н",
  "тт", "вв", "гг", "сс", "пр", "ст", "до",
  "стр", "рис", "табл", "напр", "тов", "акад", "проф", "имп", "ген",
  "пол", "св", "ул", "пл", "пер", "просп", "обл", "млн", "млрд",
  "тыс", "руб", "коп", "сек", "мин", "см", "мм", "км", "кг", "вып",
  "изд", "гл", "им", "век", "напис", "опубл", "род", "ум",
  "mr", "mrs", "ms", "dr", "vs", "etc"
]);

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

function stripXml(s) {
  return s
    .replace(/<\/p>/gi, "\n")
    .replace(/<\/?(?:emphasis|strong|em|b|i|u|sub|sup|stanza|v|cite|epigraph|text-author|date)\b[^>]*>/gi, "")
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

function findDirectSections(content) {
  const sections = [];
  let depth = 0;
  let currentStart = -1;
  const sectionTagRe = /<\/?section\b[^>]*>/gi;
  let m;
  while ((m = sectionTagRe.exec(content)) !== null) {
    const tag = m[0];
    if (/^<section\b/i.test(tag)) {
      if (depth === 0) currentStart = m.index + tag.length;
      depth++;
    } else if (/^<\/section/i.test(tag)) {
      depth--;
      if (depth === 0 && currentStart >= 0) {
        sections.push(content.slice(currentStart, m.index));
        currentStart = -1;
      }
    }
  }
  return sections;
}

function hasNestedSection(content) {
  return /<section\b/i.test(content);
}

function extractTitle(sec) {
  const titleMatch = sec.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (titleMatch) {
    return stripXml(titleMatch[1]).replace(/\s+/g, " ").trim();
  }
  return "";
}

function splitBySubtitles(sectionContent) {
  // Returns array of {title, text} per subtitle-delimited chapter, OR null
  // if there are fewer than 2 subtitle markers.
  const subtitleRe = /<subtitle[^>]*>([\s\S]*?)<\/subtitle>/gi;
  const subtitles = [];
  let m;
  while ((m = subtitleRe.exec(sectionContent)) !== null) {
    subtitles.push({
      start: m.index,
      end: m.index + m[0].length,
      title: stripXml(m[1]).replace(/\s+/g, " ").trim(),
    });
  }
  if (subtitles.length < 2) return null;

  const chapters = [];
  for (let i = 0; i < subtitles.length; i++) {
    const contentStart = subtitles[i].end;
    const contentEnd = i + 1 < subtitles.length ? subtitles[i + 1].start : sectionContent.length;
    // Include subtitle text as the chapter's first line so sentence counts match
    // App.jsx (which includes subtitle elements via querySelectorAll).
    const text = subtitles[i].title + "\n" + stripXml(sectionContent.slice(contentStart, contentEnd));
    chapters.push({ title: subtitles[i].title, text });
  }
  return chapters;
}

function parseFb2(xml) {
  const bodyMatch = xml.match(/<body(?:[^>]*)>([\s\S]*?)<\/body>/i);
  if (!bodyMatch) {
    return [{ path: [1], title: "", text: stripXml(xml) }];
  }
  const body = bodyMatch[1];

  const topLevelSections = findDirectSections(body);
  if (topLevelSections.length === 0) {
    return [{ path: [1], title: "", text: stripXml(body) }];
  }

  const chapters = [];

  function recurse(sectionContent, pathSoFar) {
    if (!hasNestedSection(sectionContent)) {
      // Leaf section: check for subtitle-delimited chapters within
      const subtitleSplits = splitBySubtitles(sectionContent);

      if (subtitleSplits) {
        // First subtitle-chapter also includes the leaf's own title (e.g.
        // "ЧАСТЬ ПЕРВАЯ") so the sentence count matches App.jsx flattening.
        const leafTitle = extractTitle(sectionContent);
        subtitleSplits.forEach((sub, idx) => {
          let chapterText = sub.text;
          if (idx === 0 && leafTitle) {
            chapterText = leafTitle + "\n" + chapterText;
          }
          chapters.push({
            path: [...pathSoFar, idx + 1],
            title: sub.title,
            text: chapterText,
          });
        });
      } else {
        // No subtitle markers — treat leaf as a single chapter
        const title = extractTitle(sectionContent);
        const cleaned = sectionContent.replace(/<title[^>]*>[\s\S]*?<\/title>/i, "");
        chapters.push({
          path: pathSoFar,
          title: title || `Chapter ${pathSoFar.join(".")}`,
          text: (title ? title + "\n" : "") + stripXml(cleaned),
        });
      }
      return;
    }
    // Has nested sections — recurse
    const nested = findDirectSections(sectionContent);
    nested.forEach((sub, idx) => {
      recurse(sub, [...pathSoFar, idx + 1]);
    });
  }

  topLevelSections.forEach((sec, idx) => {
    recurse(sec, [idx + 1]);
  });

  return chapters;
}

function chapterSuffix(chapterPath) {
  if (chapterPath.length === 1) return `ch${chapterPath[0]}`;
  return `p${chapterPath[0]}-ch${chapterPath[chapterPath.length - 1]}`;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    console.error("Usage: node extract-sentences.cjs <file.fb2|file.txt> [--part N] [--chapter N] [--whole]");
    process.exit(2);
  }

  const inputPath = args[0];
  const partArg = args.indexOf("--part");
  const chapterArg = args.indexOf("--chapter");
  const wantPart = partArg >= 0 ? parseInt(args[partArg + 1], 10) : null;
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
    chapters = [{ path: [1], title: "", text: raw }];
  }

  if (wantWhole) {
    const allSents = [];
    chapters.forEach(c => {
      allSents.push(...parseSentences(c.text));
    });
    process.stdout.write(allSents.join("\n") + "\n");
    console.error(`Wrote ${allSents.length} sentences to stdout.`);
    return;
  }

  let filtered = chapters;
  if (wantPart !== null) filtered = filtered.filter(c => c.path[0] === wantPart);
  if (wantChapter !== null) {
    if (wantPart !== null) {
      filtered = filtered.filter(c => c.path[c.path.length - 1] === wantChapter);
    } else {
      filtered = filtered.slice(wantChapter, wantChapter + 1);
    }
  }

  if (filtered.length === 0) {
    console.error(`No chapters matched. Book has ${chapters.length} total.`);
    chapters.slice(0, 8).forEach(c => console.error(`  ${c.path.join(".")} - "${c.title}"`));
    process.exit(2);
  }

  const base = inputPath.replace(/\.[^.]+$/, "");
  filtered.forEach(c => {
    const sents = parseSentences(c.text);
    if (sents.length === 0) {
      console.error(`Chapter ${c.path.join(".")} ("${c.title}"): no sentences — skipped`);
      return;
    }
    const suffix = chapterSuffix(c.path);
    const outPath = `${base}-${suffix}.txt`;
    fs.writeFileSync(outPath, sents.join("\n") + "\n", "utf-8");
    console.error(`Chapter ${c.path.join(".")} ("${c.title}"): wrote ${sents.length} sentences → ${path.basename(outPath)}`);
  });
}

main();
