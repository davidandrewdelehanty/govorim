// Shared GitHub Contents API helpers for admin endpoints that read/write files
// in the repo (which triggers a Vercel redeploy). Mirrors the ghGet/ghPut
// pattern used by upload-book.js / upload-song.js so behaviour is consistent.

function ghEnv() {
  const token  = process.env.GITHUB_TOKEN;
  const owner  = process.env.GITHUB_OWNER;
  const repo   = process.env.GITHUB_REPO;
  const branch = process.env.GITHUB_BRANCH || "main";
  if (!token || !owner || !repo) {
    throw new Error("Missing env vars. Need GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO on Vercel.");
  }
  return { token, owner, repo, branch };
}

// GET a file's decoded UTF-8 content + sha. Returns null on 404.
async function ghGet(path, opts) {
  const { token, owner, repo, branch } = opts || ghEnv();
  // Cache-bust so a scan right after a commit never re-reads a stale copy
  // (which made just-fixed discrepancies reappear).
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
              "/contents/" + encodeURIComponent(path).replace(/%2F/g, "/") +
              "?ref=" + encodeURIComponent(branch) + "&t=" + Date.now();
  const r = await fetch(url, {
    cache: "no-store",
    headers: {
      "Authorization": "Bearer " + token,
      "Accept":        "application/vnd.github+json",
      "User-Agent":    "govorim-transcript-tools",
      "If-None-Match":  "",
    },
  });
  if (r.status === 404) return null;
  if (!r.ok) {
    const t = await r.text();
    throw new Error("GitHub GET failed (" + r.status + ") for " + path + ": " + t.slice(0, 200));
  }
  const data = await r.json();
  return {
    sha: data.sha,
    content: Buffer.from(data.content || "", "base64").toString("utf-8"),
  };
}

// GET a binary file (e.g. EPUB) → { sha, buffer }. Falls back to the git blobs
// API when the contents API omits inline content (files > 1MB).
async function ghGetBinary(path, opts) {
  const env = opts || ghEnv();
  const { token, owner, repo, branch } = env;
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
              "/contents/" + encodeURIComponent(path).replace(/%2F/g, "/") +
              "?ref=" + encodeURIComponent(branch) + "&t=" + Date.now();
  const r = await fetch(url, {
    cache: "no-store",
    headers: { "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "govorim-transcript-tools" },
  });
  if (r.status === 404) return null;
  if (!r.ok) { const t = await r.text(); throw new Error("GitHub GET failed (" + r.status + ") for " + path + ": " + t.slice(0, 200)); }
  const data = await r.json();
  if (data.content) return { sha: data.sha, buffer: Buffer.from(data.content, "base64") };
  // large file: fetch the blob by sha
  const b = await fetch("https://api.github.com/repos/" + owner + "/" + repo + "/git/blobs/" + data.sha, {
    cache: "no-store",
    headers: { "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "govorim-transcript-tools" },
  });
  if (!b.ok) throw new Error("GitHub blob fetch failed (" + b.status + ")");
  const bd = await b.json();
  return { sha: data.sha, buffer: Buffer.from(bd.content || "", "base64") };
}

// PUT (create/update) a file. `content` may be a UTF-8 string or a Buffer.
async function ghPut(path, content, sha, message, opts) {
  const { token, owner, repo, branch } = opts || ghEnv();
  let base64Content;
  if (Buffer.isBuffer(content)) {
    base64Content = content.toString("base64");
  } else {
    base64Content = Buffer.from(String(content), "utf-8").toString("base64");
  }
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
              "/contents/" + encodeURIComponent(path).replace(/%2F/g, "/");
  const body = { message: message, content: base64Content, branch: branch };
  if (sha) body.sha = sha;
  const r = await fetch(url, {
    method: "PUT",
    headers: {
      "Authorization": "Bearer " + token,
      "Accept":        "application/vnd.github+json",
      "Content-Type":  "application/json",
      "User-Agent":    "govorim-transcript-tools",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error("GitHub PUT failed (" + r.status + ") for " + path + ": " + t.slice(0, 200));
  }
  return await r.json();
}

export { ghEnv, ghGet, ghGetBinary, ghPut };
