// POST /api/admin/upload-book — admin-only endpoint that adds a non-song book
// (novel, play, short story, poetry) to the library via GitHub commit.
//
// Body (JSON):
//   {
//     filename: "tolstoy-anna.epub",   // original filename, used for extension
//     title:    "Анна Каренина",
//     author:   "Лев Толстой",
//     category: "Works" | "Poetry",
//     fileBase64: "<base64-encoded file bytes>"
//   }
//
// Stores at: public/books/<category-folder>/<slug>.<ext>
// Adds an entry to public/books/index.json.
//
// Uses the same GitHub env vars as upload-song.js (GITHUB_TOKEN, GITHUB_OWNER,
// GITHUB_REPO, GITHUB_BRANCH).

import { requireAdmin } from "./_helpers.js";

const CYR_MAP = {
  "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh",
  "з":"z","и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o",
  "п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"kh","ц":"ts",
  "ч":"ch","ш":"sh","щ":"shch","ы":"y","э":"e","ю":"yu","я":"ya",
  "ь":"","ъ":"",
  "А":"a","Б":"b","В":"v","Г":"g","Д":"d","Е":"e","Ё":"yo","Ж":"zh",
  "З":"z","И":"i","Й":"y","К":"k","Л":"l","М":"m","Н":"n","О":"o",
  "П":"p","Р":"r","С":"s","Т":"t","У":"u","Ф":"f","Х":"kh","Ц":"ts",
  "Ч":"ch","Ш":"sh","Щ":"shch","Ы":"y","Э":"e","Ю":"yu","Я":"ya",
  "Ь":"","Ъ":"",
};

function slugify(text) {
  if (!text) return "";
  return String(text)
    .split("")
    .map(function(c){ return CYR_MAP[c] !== undefined ? CYR_MAP[c] : c; })
    .join("")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

// Categories the picker supports. Song Lyrics is NOT in this list — use the
// upload-song endpoint for those, since they need different formatting.
// "Works" is the unified prose-and-drama category (novels, short stories,
// plays all merged). Legacy "Novel", "Short Stories", and "Plays" are kept
// as aliases that map to the same folder, so older clients keep working.
const CATEGORY_TO_FOLDER = {
  "Works":         "novel",
  "Novel":         "novel",          // legacy alias
  "Short Stories": "novel",          // legacy alias — files merged here
  "Plays":         "novel",          // legacy alias — files merged here
  "Poetry":        "poetry",
};
const ALLOWED_EXTS = ["epub", "fb2", "txt", "html", "htm", "xhtml"];

async function ghGet(owner, repo, branch, path, token) {
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
              "/contents/" + encodeURIComponent(path).replace(/%2F/g, "/") +
              "?ref=" + encodeURIComponent(branch);
  const r = await fetch(url, {
    headers: {
      "Authorization": "Bearer " + token,
      "Accept":        "application/vnd.github+json",
      "User-Agent":    "govorim-upload",
    },
  });
  if (r.status === 404) return null;
  if (!r.ok) {
    const t = await r.text();
    throw new Error("GitHub GET failed (" + r.status + "): " + t.slice(0, 200));
  }
  const data = await r.json();
  return { sha: data.sha, content: Buffer.from(data.content || "", "base64").toString("utf-8") };
}

// Commit a file. `content` may be either a UTF-8 string (text files / JSON)
// or a Buffer (binary files like EPUB). Binary skips the utf-8 encoding step.
async function ghPut(owner, repo, branch, path, content, sha, message, token) {
  let base64Content;
  if (Buffer.isBuffer(content)) {
    base64Content = content.toString("base64");
  } else {
    base64Content = Buffer.from(String(content), "utf-8").toString("base64");
  }
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
              "/contents/" + encodeURIComponent(path).replace(/%2F/g, "/");
  const body = {
    message: message,
    content: base64Content,
    branch:  branch,
  };
  if (sha) body.sha = sha;
  const r = await fetch(url, {
    method: "PUT",
    headers: {
      "Authorization": "Bearer " + token,
      "Accept":        "application/vnd.github+json",
      "Content-Type":  "application/json",
      "User-Agent":    "govorim-upload",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error("GitHub PUT failed (" + r.status + "): " + t.slice(0, 200));
  }
  return await r.json();
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const a = await requireAdmin(req, res);
  if (!a) return;

  const token  = process.env.GITHUB_TOKEN;
  const owner  = process.env.GITHUB_OWNER;
  const repo   = process.env.GITHUB_REPO;
  const branch = process.env.GITHUB_BRANCH || "main";
  if (!token || !owner || !repo) {
    return res.status(500).json({
      error: "Missing env vars. Need GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO on Vercel.",
    });
  }

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const filename   = (body && typeof body.filename   === "string" ? body.filename   : "").trim();
  const title      = (body && typeof body.title      === "string" ? body.title      : "").trim();
  const author     = (body && typeof body.author     === "string" ? body.author     : "").trim();
  const category   = (body && typeof body.category   === "string" ? body.category   : "").trim();
  const fileBase64 = (body && typeof body.fileBase64 === "string" ? body.fileBase64 : "");

  if (!filename)   return res.status(400).json({ error: "filename required" });
  if (!title)      return res.status(400).json({ error: "title required" });
  if (!category)   return res.status(400).json({ error: "category required" });
  if (!fileBase64) return res.status(400).json({ error: "fileBase64 required" });

  const folder = CATEGORY_TO_FOLDER[category];
  if (!folder) {
    return res.status(400).json({ error: "Invalid category. Use one of: " + Object.keys(CATEGORY_TO_FOLDER).join(", ") });
  }

  // Extract extension from filename
  const m = filename.toLowerCase().match(/\.([a-z0-9]+)$/);
  let ext = m ? m[1] : "";
  // Handle .fb2.zip → store as fb2.zip; treat as fb2 extension family
  if (filename.toLowerCase().endsWith(".fb2.zip")) ext = "fb2.zip";
  if (!ext || (ALLOWED_EXTS.indexOf(ext) === -1 && ext !== "fb2.zip")) {
    return res.status(400).json({ error: "Unsupported file type. Use EPUB, FB2, TXT, or HTML." });
  }

  // Decode + size-check the file
  let fileBuf;
  try {
    fileBuf = Buffer.from(fileBase64, "base64");
  } catch (e) {
    return res.status(400).json({ error: "Could not decode file: " + (e.message || e) });
  }
  // GitHub Contents API recommends ≤50MB; we enforce 20MB to keep deploys snappy.
  if (fileBuf.length === 0) {
    return res.status(400).json({ error: "Empty file" });
  }
  if (fileBuf.length > 20 * 1024 * 1024) {
    return res.status(400).json({ error: "File too large (max 20MB)" });
  }

  const titleSlug = slugify(title) || slugify(filename.replace(/\.[^.]+$/, ""));
  if (!titleSlug) {
    return res.status(400).json({ error: "Couldn't generate filename from title" });
  }

  const bookPath  = "public/books/" + folder + "/" + titleSlug + "." + ext;
  const indexPath = "public/books/index.json";

  console.log("[upload-book] admin=" + a.email + " path=" + bookPath + " bytes=" + fileBuf.length);

  try {
    // Refuse to overwrite an existing book — otherwise we'd silently replace
    // someone's content. Admin should rename or delete-then-reupload manually.
    const existing = await ghGet(owner, repo, branch, bookPath, token);
    if (existing) {
      return res.status(409).json({ error: "A book already exists at " + bookPath + ". Rename the title or delete the old file first." });
    }

    // 1. Commit the binary file
    await ghPut(
      owner, repo, branch, bookPath, fileBuf, null,
      'Add book "' + title.slice(0, 60) + '"' + (author ? " by " + author : ""),
      token
    );

    // 2. Update the manifest
    const idx = await ghGet(owner, repo, branch, indexPath, token);
    let arr = [];
    let idxSha = null;
    if (idx) {
      try { arr = JSON.parse(idx.content); } catch { arr = []; }
      idxSha = idx.sha;
    }
    if (!Array.isArray(arr)) arr = [];

    const newEntry = {
      filename: folder + "/" + titleSlug + "." + ext,
      title:    title,
      category: category,
    };
    if (author) newEntry.author = author;
    arr.push(newEntry);

    await ghPut(
      owner, repo, branch, indexPath,
      JSON.stringify(arr, null, 2) + "\n",
      idxSha,
      "Add " + title + " to library",
      token
    );

    return res.status(200).json({
      ok:      true,
      path:    bookPath,
      title:   title,
      message: 'Book "' + title + '" committed. Vercel redeploys in ~1-2 min — book appears in picker after that.',
    });

  } catch (err) {
    console.error("[upload-book] failed:", err && err.message ? err.message : err);
    return res.status(500).json({ error: (err && err.message) || "Upload failed" });
  }
}
