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
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
              "/contents/" + encodeURIComponent(path).replace(/%2F/g, "/") +
              "?ref=" + encodeURIComponent(branch);
  const r = await fetch(url, {
    headers: {
      "Authorization": "Bearer " + token,
      "Accept":        "application/vnd.github+json",
      "User-Agent":    "govorim-transcript-tools",
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

export { ghEnv, ghGet, ghPut };
