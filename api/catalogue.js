// The book catalogue, filtered by who is asking.
//
// The manifest moved out of public/ (where anyone could fetch it) into
// private/books/index.json, which is bundled into this function but never
// served as a static asset. Entries marked "restricted": true are stripped
// for everyone except the admin -- so a restricted book's title, author and
// chapter list do not leak to a signed-out visitor, and neither does the
// existence of the book.
//
// Restricted entries are returned to the admin with their file paths
// rewritten to /api/media?path=..., which is the only route that will serve
// those files (see api/media.js).

import fs from "node:fs";
import path from "node:path";
import { currentUser } from "../lib/auth.js";

function manifestPath() {
  return path.join(process.cwd(), "private", "books", "index.json");
}

function mediaUrl(relPath) {
  return "/api/media?path=" + encodeURIComponent(relPath);
}

// Rewrite the paths a restricted entry points at, so the client fetches
// them through the gate rather than from /books/ where they no longer are.
function gateEntry(entry) {
  const out = Object.assign({}, entry, { restricted: true });
  if (out.filename) out.fileUrl = mediaUrl(out.filename);
  if (out.audiobook && Array.isArray(out.audiobook.chapters)) {
    out.audiobook = Object.assign({}, out.audiobook, {
      chapterUrls: out.audiobook.chapters.map(mediaUrl),
    });
  }
  return out;
}

export default function handler(req, res) {
  let list;
  try {
    list = JSON.parse(fs.readFileSync(manifestPath(), "utf8"));
  } catch (e) {
    return res.status(500).json({ error: "Catalogue unavailable: " + (e.message || e) });
  }
  if (!Array.isArray(list)) return res.status(500).json({ error: "Catalogue is malformed" });

  const user = currentUser(req);
  // The library is gated: no account, no catalogue. Registration is instant
  // (api/auth.js signup issues a session straight away), so this is a door,
  // not a waiting room.
  if (!user) {
    res.setHeader("Cache-Control", "private, no-store");
    return res.status(401).json({ error: "An account is required to browse the library." });
  }
  const isAdmin = !!(user && user.isAdmin);

  const books = [];
  for (const entry of list) {
    if (entry && entry.restricted) {
      if (isAdmin) books.push(gateEntry(entry));
      continue;
    }
    books.push(entry);
  }

  // Never cache at the edge: the response depends on the session cookie, and
  // a shared cache would hand one visitor's catalogue to the next one.
  res.setHeader("Cache-Control", "private, no-store");
  res.status(200).json(books);
}
