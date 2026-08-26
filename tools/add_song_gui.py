#!/usr/bin/env python3
"""Govorim — song upload GUI.

Run from WSL:  python3 tools/add_song_gui.py
Opens a form in your browser; each submit adds a song to public/music/music.json,
with an optional commit + push. Ctrl+C in the terminal (or the Quit link) stops it.
"""
import json, re, os, sys, html, subprocess, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from email.parser import BytesParser
from email.policy import default as email_default

# Override with GOVORIM_REPO when running from anywhere but the usual WSL path.
REPO = os.environ.get("GOVORIM_REPO", "/mnt/c/Users/david/projects/govorim-app")
# Two catalogues. govorim's music.json holds material that may not be
# republished; the public site (Samovar) reads music.public.json and nothing
# else. Picking the wrong one is the mistake this selector exists to prevent,
# so the form always shows which catalogue is being written.
MUSIC_FILES = {
    "private": os.path.join(REPO, "public", "music", "music.json"),
    "public":  os.path.join(REPO, "public", "music", "music.public.json"),
}
MUSIC_LABELS = {
    "private": "govorim (private)",
    "public":  "Samovar (public \u2014 public-domain songs only)",
}

MUSIC_REL = {
    "private": "public/music/music.json",
    "public":  "public/music/music.public.json",
}

# Launch with --public to open straight on the Samovar catalogue. The dropdown
# still switches either way; this only sets what the form opens on, so the
# common case doesn't depend on remembering to change it.
DEFAULT_CATALOGUE = "public" if "--public" in sys.argv else "private"

def music_path(which):
    return MUSIC_FILES.get(which, MUSIC_FILES["private"])
PORT = 8765

def load_music(which="private"):
    path = music_path(which)
    if not os.path.isfile(path):
        return []
    return json.load(open(path, encoding="utf-8"))

def save_music(which, data):
    json.dump(data, open(music_path(which), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

# Artists whose name has more than one spelling in the wild. Key = normalised
# form (lowercase, punctuation and spacing stripped), value = the spelling the
# app should show. Add a line here whenever a second rendering turns up; the
# merge is automatic from then on, so the Music tab never grows twin listings.
ARTIST_ALIASES = {
    u"noizemc": u"Noize MC",
    u"нойзмс": u"Noize MC",     # Нойз МС — all Cyrillic
    u"нойзмc": u"Noize MC",      # Нойз МC — Cyrillic М, Latin C
    u"нойзmc": u"Noize MC",       # Нойз MC — Latin MC
    u"нойзэмси": u"Noize MC",   # Нойз Эм Си
}

def norm_artist(s):
    """Fold case, ё/е, spacing and punctuation so lookups are forgiving."""
    s = (s or u"").strip().lower().replace(u"ё", u"е")
    return re.sub(r"[\s.,'’«»\"-]+", u"", s)

def canon_artist(s):
    """The spelling to store: the official one when we know an alias for it."""
    return ARTIST_ALIASES.get(norm_artist(s), (s or u"").strip())

def artist_key(s):
    """Match key that folds aliases on BOTH sides, so an entry already saved
    under an old spelling still matches a submission under the new one."""
    return norm_artist(canon_artist(s))

def yt_id(s):
    m = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})', s) \
        or re.fullmatch(r'\s*([A-Za-z0-9_-]{11})\s*', s)
    return m.group(1) if m else None

STYLE = """
<style>
 body{background:#1a1611;color:#e8ddcb;font-family:Georgia,serif;max-width:640px;
      margin:40px auto;padding:0 16px}
 h1{color:#c4955a;font-size:1.5em;font-weight:600}
 label{display:block;margin:14px 0 4px;color:#c4955a;font-size:.95em}
 input[type=text],textarea{width:100%;box-sizing:border-box;background:#26211a;
      color:#e8ddcb;border:1px solid #4a3f30;border-radius:6px;padding:9px;
      font-family:inherit;font-size:1em}
 textarea{min-height:220px;white-space:pre}
 input[type=file]{margin-top:4px;color:#a89880}
 .row{display:flex;gap:14px;align-items:center;margin-top:18px}
 button{background:#c4955a;color:#1a1611;border:none;border-radius:6px;
      padding:10px 22px;font-size:1em;font-family:inherit;font-weight:600;cursor:pointer}
 button:hover{background:#d5a86b}
 .chk{color:#a89880;font-size:.95em}
 .ok{background:#20301e;border:1px solid #4a6b44;border-radius:6px;padding:12px 16px;margin:16px 0}
 .err{background:#3a2020;border:1px solid #7a4444;border-radius:6px;padding:12px 16px;margin:16px 0}
 pre{background:#26211a;border-radius:6px;padding:10px;overflow-x:auto;font-size:.85em;color:#a89880}
 a{color:#c4955a}
 .quit{float:right;font-size:.85em}
 .hint{color:#7a6d58;font-size:.85em;margin-top:2px}
</style>
"""

def form_page(msg="", which="private"):
    artists = ""
    try:
        artists = "".join('<option value="%s">' % html.escape(a["artist"]) for a in load_music(which))
    except Exception:
        pass
    options = "".join(
        '<option value="%s"%s>%s</option>' % (k, " selected" if k == which else "", MUSIC_LABELS[k])
        for k in ("private", "public")
    )
    return """<!doctype html><meta charset="utf-8"><title>Govorim — add song</title>%s
<a class="quit" href="/quit">quit</a>
<h1>Add a song</h1>%s
<form method="post" action="/add" enctype="multipart/form-data">
 <label>Catalogue</label>
 <select name="catalogue" onchange="location.search='?catalogue='+this.value">%s</select>
 <div class="hint">Samovar is public \u2014 only songs whose lyrics are public domain</div>
 <label>Artist</label>
 <input type="text" name="artist" list="artists" required>
 <datalist id="artists">%s</datalist>
 <div class="hint">pick an existing artist or type a new one</div>
 <label>Song title</label>
 <input type="text" name="title" required>
 <label>YouTube link (or bare video ID)</label>
 <input type="text" name="youtube" required>
 <label>Lyrics — paste here…</label>
 <textarea name="lyrics" placeholder="Paste the lyrics…"></textarea>
 <label>…or choose a .txt file instead</label>
 <input type="file" name="lyricsfile" accept=".txt">
 <div class="row">
  <button type="submit">Add song</button>
  <label class="chk"><input type="checkbox" name="push" checked> commit &amp; push after adding</label>
 </div>
</form>""" % (STYLE, msg, options, artists)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, body, code=200):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/quit":
            self._send("%s<h1>Stopped.</h1><p>You can close this tab.</p>" % STYLE)
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        which = DEFAULT_CATALOGUE
        if "catalogue=public" in (self.path or ""):
            which = "public"
        elif "catalogue=private" in (self.path or ""):
            which = "private"
        self._send(form_page("", which))

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        ctype = self.headers.get("Content-Type", "")
        msg = BytesParser(policy=email_default).parsebytes(
            b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body)
        fields, filebytes = {}, None
        for part in (msg.iter_parts() if msg.is_multipart() else []):
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            if part.get_filename():
                if name == "lyricsfile":
                    filebytes = part.get_payload(decode=True)
            else:
                payload = part.get_payload(decode=True) or b""
                fields[name] = payload.decode("utf-8", errors="replace")

        which = fields.get("catalogue", DEFAULT_CATALOGUE).strip()
        if which not in MUSIC_FILES:
            which = "private"
        artist = fields.get("artist", "").strip()
        title = fields.get("title", "").strip()
        yt = fields.get("youtube", "").strip()
        lyrics = fields.get("lyrics", "").strip()
        push = "push" in fields

        if not lyrics and filebytes:
            lyrics = filebytes.decode("utf-8-sig", errors="replace").strip()
        lyrics = lyrics.replace("\r\n", "\n")

        def fail(m):
            self._send(form_page('<div class="err">%s</div>' % html.escape(m), which))

        if not (artist and title and yt):
            return fail("Artist, title, and YouTube link are all required.")
        if not lyrics:
            return fail("No lyrics — paste them in the box or choose a .txt file.")
        vid = yt_id(yt)
        if not vid:
            return fail("Couldn't extract a YouTube video ID from: " + yt)

        try:
            data = load_music(which)
        except Exception as e:
            return fail("Couldn't read music.json: %s" % e)

        artist = canon_artist(artist)
        entry = next((a for a in data if artist_key(a["artist"]) == artist_key(artist)), None)
        if entry is None:
            entry = {"artist": artist, "songs": []}
            data.append(entry)
        elif canon_artist(entry["artist"]) != entry["artist"]:
            # An entry saved under an older spelling is renamed to the official one.
            entry["artist"] = canon_artist(entry["artist"])
        if any(s["title"].strip().lower() == title.lower() for s in entry["songs"]):
            return fail("«%s» already exists for %s — not overwriting." % (title, entry["artist"]))

        entry["songs"].append({"title": title, "youtube": vid, "lyrics": lyrics})
        save_music(which, data)

        msg = '<div class="ok">Added <b>%s — %s</b> (video %s).</div>' % (
            html.escape(entry["artist"]), html.escape(title), vid)

        if push:
            site = "Samovar" if which == "public" else "Govorim"
            cmds = [["git", "add", MUSIC_REL[which]],
                    ["git", "commit", "-m", "%s music: add %s — %s" % (site, artist, title)],
                    ["git", "push"]]
            out = []
            for c in cmds:
                r = subprocess.run(c, cwd=REPO, capture_output=True, text=True)
                out.append("$ " + " ".join(c) + "\n" + r.stdout + r.stderr)
                if r.returncode != 0:
                    msg += ('<div class="err">git step failed — the song IS saved in %s, '
                            'but you\'ll need to push manually.</div>'
                            % html.escape(os.path.basename(music_path(which))))
                    break
            else:
                msg += '<div class="ok">Committed and pushed — live after Vercel redeploys.</div>'
            msg += "<pre>%s</pre>" % html.escape("\n".join(out))
        else:
            msg += '<div class="ok">Saved to %s (not committed).</div>' % html.escape(os.path.basename(music_path(which)))

        self._send(form_page(msg, which))

def open_browser(url):
    for cmd in (["wslview", url],
                ["powershell.exe", "-NoProfile", "-Command", "Start-Process '%s'" % url],
                ["cmd.exe", "/c", "start", url]):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
    print("Open %s in your browser." % url)

if __name__ == "__main__":
    target = music_path(DEFAULT_CATALOGUE)
    # Samovar's catalogue starts empty, so create it rather than refusing to run.
    if not os.path.isfile(target):
        if DEFAULT_CATALOGUE == "public":
            os.makedirs(os.path.dirname(target), exist_ok=True)
            json.dump([], open(target, "w", encoding="utf-8"))
            print("Created %s" % target)
        else:
            sys.exit("music.json not found at %s" % target)
    url = "http://127.0.0.1:%d/?catalogue=%s" % (PORT, DEFAULT_CATALOGUE)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    srv.daemon_threads = True
    print("%s song uploader — %s  (Ctrl+C to stop)"
          % (MUSIC_LABELS[DEFAULT_CATALOGUE], url))
    open_browser(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
