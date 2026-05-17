// POST /api/admin/upload-song — admin-only endpoint that adds a song to the
// library by committing files directly to the GitHub repo. Vercel auto-redeploys
// when the commit lands; the new song shows up in the picker after the deploy
// completes (~1-2 min).
//
// Body: { artist: string, title: string, lyrics: string }
//
// Storage model: one .txt file per artist, song-collection format that the
// existing parseTxt + Song Lyrics splitter understands:
//
//   1.
//   Group of Blood
//
//   [lyrics 1]
//
//   2.
//   Changes
//
//   [lyrics 2]
//
// New uploads APPEND to the artist's file (creating it if missing). The
// per-artist organization keeps the picker clean — one library entry per
// artist with all their songs as chapters/songs within.
//
// Required env vars (set on Vercel):
//   CLERK_SECRET_KEY   — already set
//   ADMIN_EMAIL        — already set
//   GITHUB_TOKEN       — fine-grained PAT with repo Contents write perm
//   GITHUB_OWNER       — repo owner (your GitHub username or org)
//   GITHUB_REPO        — repo name
// Optional:
//   GITHUB_BRANCH      — branch to commit to (defaults to "main")

import { requireAdmin } from "./_helpers.js";

// Transliteration for Cyrillic → Latin so artist names become URL-safe
// filenames. (russian-to-english conventional mapping; not perfect but good
// enough for filenames — Виктор Цой → viktor-tsoy).
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

// Get a file from GitHub via the Contents API. Returns { sha, content } on
// success, null if the file doesn't exist (404). Throws on other errors.
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
  // GitHub returns content base64-encoded with newlines every 60 chars
  const content = Buffer.from(data.content || "", "base64").toString("utf-8");
  return { sha: data.sha, content: content };
}

// Create or update a file via the Contents API. `sha` is required when updating
// an existing file (it's the file's previous sha). Pass null for new files.
async function ghPut(owner, repo, branch, path, content, sha, message, token) {
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
              "/contents/" + encodeURIComponent(path).replace(/%2F/g, "/");
  const body = {
    message: message,
    content: Buffer.from(content, "utf-8").toString("base64"),
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

  // ---- Admin auth (reuses the shared helper) ────────────────────────────
  const a = await requireAdmin(req, res);
  if (!a) return; // helper already wrote the error response

  // ---- Required env vars ─────────────────────────────────────────────────
  const token  = process.env.GITHUB_TOKEN;
  const owner  = process.env.GITHUB_OWNER;
  const repo   = process.env.GITHUB_REPO;
  const branch = process.env.GITHUB_BRANCH || "main";
  if (!token || !owner || !repo) {
    return res.status(500).json({
      error: "Missing env vars. Need GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO on Vercel.",
    });
  }

  // ---- Body validation ───────────────────────────────────────────────────
  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const artist = (body && typeof body.artist === "string" ? body.artist : "").trim();
  const title  = (body && typeof body.title  === "string" ? body.title  : "").trim();
  const lyrics = (body && typeof body.lyrics === "string" ? body.lyrics : "").trim();

  if (!artist) return res.status(400).json({ error: "Artist required" });
  if (!title)  return res.status(400).json({ error: "Song title required" });
  if (lyrics.length < 20) return res.status(400).json({ error: "Lyrics too short (min 20 chars)" });
  if (lyrics.length > 30000) return res.status(400).json({ error: "Lyrics too long (max 30k chars)" });

  // Light sanity check: at least some Cyrillic.
  const cyrCount = (lyrics.match(/[а-яёА-ЯЁ]/g) || []).length;
  if (cyrCount < 10) {
    return res.status(400).json({ error: "Lyrics don't look like Russian (need at least 10 Cyrillic letters)" });
  }

  const artistSlug = slugify(artist);
  if (!artistSlug) {
    return res.status(400).json({ error: "Couldn't generate filename from artist name. Use Latin or Cyrillic letters." });
  }

  const songFilePath  = "public/books/lyrics/" + artistSlug + ".txt";
  const indexFilePath = "public/books/index.json";

  console.log("[upload-song] admin=" + a.email + " artist=" + artistSlug + " title=" + title.slice(0, 40));

  try {
    // 1. Read existing artist file if any. Use it to determine next song number.
    const existing = await ghGet(owner, repo, branch, songFilePath, token);

    let nextNum = 1;
    let newFileContent;
    if (existing) {
      // Find the highest "N." marker so we append with the next number
      const markers = existing.content.match(/^\d{1,3}\.?\s*$/gm) || [];
      if (markers.length) {
        const nums = markers.map(function(m){ return parseInt(m, 10); }).filter(function(n){ return !isNaN(n); });
        if (nums.length) nextNum = Math.max.apply(Math, nums) + 1;
      }
      // Append the new song with a separating blank line
      newFileContent = existing.content.replace(/\s+$/, "") +
        "\n\n" + nextNum + ".\n" + title + "\n\n" + lyrics + "\n";
    } else {
      // First song from this artist — create a fresh file
      newFileContent = "1.\n" + title + "\n\n" + lyrics + "\n";
    }

    // 2. Commit the song file (create-or-update)
    await ghPut(
      owner, repo, branch, songFilePath, newFileContent,
      existing ? existing.sha : null,
      'Add song "' + title.slice(0, 60) + '" by ' + artist,
      token
    );

    // 3. If this artist is new, also add an entry to public/books/index.json.
    //    (If they're not new, the existing entry already points to the same file.)
    let updatedIndex = false;
    if (!existing) {
      const idx = await ghGet(owner, repo, branch, indexFilePath, token);
      let arr = [];
      let idxSha = null;
      if (idx) {
        try { arr = JSON.parse(idx.content); } catch { arr = []; }
        idxSha = idx.sha;
      }
      if (!Array.isArray(arr)) arr = [];
      // Defensive: skip if somehow already in the index
      const alreadyIn = arr.some(function(b){ return b && b.filename === "lyrics/" + artistSlug + ".txt"; });
      if (!alreadyIn) {
        arr.push({
          filename: "lyrics/" + artistSlug + ".txt",
          title:    artist,                  // shown in picker as "Artist Name"
          author:   artist,
          category: "Song Lyrics",
          splitByNumberedSections: true,    // tells loadFile to split by numbered markers
        });
        await ghPut(
          owner, repo, branch, indexFilePath,
          JSON.stringify(arr, null, 2) + "\n",
          idxSha,
          "Add " + artist + " to song library",
          token
        );
        updatedIndex = true;
      }
    }

    return res.status(200).json({
      ok:           true,
      artist:       artist,
      artistSlug:   artistSlug,
      songNumber:   nextNum,
      isNewArtist:  !existing,
      indexUpdated: updatedIndex,
      message:      'Song "' + title + '" committed' + (updatedIndex ? " + library index updated" : "") +
                    ". Vercel will redeploy in ~1-2 min — your new song appears after that.",
    });

  } catch (err) {
    console.error("[upload-song] failed:", err && err.message ? err.message : err);
    return res.status(500).json({ error: (err && err.message) || "Upload failed" });
  }
}
