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
import { isPublicSite } from "../lib/site.js";

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

  // On the public deployment a book must opt IN. An entry with no "public"
  // flag is private, so adding a book can never publish it by accident -- the
  // failure mode of a default-true flag is the one that matters here.
  //
  // Note this only hides the entry. The files it points at are static assets,
  // so they are removed from the public build entirely by
  // scripts/prune-public.mjs; filtering a list does not unpublish a file.
  const publicSite = isPublicSite();

  const books = [];
  for (const entry of list) {
    if (entry && entry.restricted) {
      // Restricted books are admin-only on the private site and simply do not
      // exist on the public one.
      if (isAdmin && !publicSite) books.push(gateEntry(entry));
      continue;
    }
    if (publicSite && !(entry && entry.public === true)) continue;
    // Audio is opted in separately from the text. Most public books are
    // text-only, so the audiobook block is dropped rather than left pointing at
    // recordings the public build never ships.
    if (publicSite && entry.audiobook && entry.publicAudio !== true) {
      const noAudio = Object.assign({}, entry);
      delete noAudio.audiobook;
      books.push(noAudio);
      continue;
    }
    books.push(entry);
  }

  // Never cache at the edge: the response depends on the session cookie, and
  // a shared cache would hand one visitor's catalogue to the next one.
  res.setHeader("Cache-Control", "private, no-store");
  res.status(200).json(books);
}
