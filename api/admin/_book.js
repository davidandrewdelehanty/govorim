// Loads a book (FB2 or EPUB) from GitHub and returns a parsed { paras } shape
// the alignment/tokenizer works on. FB2 also returns raw (for write-back edits);
// EPUB is read-only for now (isEpub:true) — its transcript JSON can still be
// scanned and fixed, but FB2-style text insert/remove isn't supported yet.

import { ghGet, ghGetBinary } from "./_gh.js";
import { parseFb2 } from "./_talign.js";
import { parseEpub } from "./_epub.js";

function isEpubPath(p) { return /\.epub$/i.test(String(p || "")); }

async function loadParsedBook(bookPath) {
  if (isEpubPath(bookPath)) {
    const got = await ghGetBinary(bookPath);
    if (!got) return null;
    return { sha: got.sha, parsed: parseEpub(got.buffer), raw: null, isEpub: true };
  }
  const got = await ghGet(bookPath);
  if (!got) return null;
  return { sha: got.sha, parsed: parseFb2(got.content), raw: got.content, isEpub: false };
}

export { loadParsedBook, isEpubPath };
