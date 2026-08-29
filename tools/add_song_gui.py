#!/usr/bin/env python3
"""Govorim — song upload GUI.

Run from WSL:  python3 tools/add_song_gui.py
Opens a form in your browser; each submit adds a song to public/music/music.json,
with an optional commit + push. Ctrl+C in the terminal (or the Quit link) stops it.
"""
import io, json, re, os, sys, html, subprocess, threading, urllib.parse
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
    "both":    "both \u2014 govorim and Samovar",
}

# "both" is an ADD-time choice only: it writes the same song into each
# catalogue and commits both files together. Editing and deleting always name
# one real catalogue, because the listing rows carry the file they came from.
def targets(which):
    return ["private", "public"] if which == "both" else [which]

def other(which):
    """The catalogue a song can be copied ACROSS to."""
    return "public" if which == "private" else "private"

def song_keys(which):
    """{(artist_key, lowercased title)} already in a catalogue."""
    try:
        data = load_music(which)
    except Exception:
        return set()
    return {(artist_key(a["artist"]), (sg.get("title") or "").strip().lower())
            for a in data for sg in (a.get("songs") or [])}

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

def counts(data):
    """(artists, songs) for the catalogue header."""
    return len(data), sum(len(a.get("songs") or []) for a in data)

COMMITTED_ONLY = ('<div class="ok">Committed. Run '
                  '<code>git push origin main</code> to publish.</div>')

def _git(cmds):
    """Run each command in turn, stopping at the first failure."""
    out = []
    for c in cmds:
        r = subprocess.run(c, cwd=REPO, capture_output=True, text=True)
        out.append("$ " + " ".join(c) + "\n" + r.stdout + r.stderr)
        if r.returncode != 0:
            # An empty commit is not a failure: it means the save changed
            # nothing, which is worth saying but not worth shouting about.
            if c[1] == "commit" and "nothing to commit" in (r.stdout + r.stderr):
                continue
            return False, "\n".join(out)
    return True, "\n".join(out)

# Committing and pushing are deliberately separate. A save that is only in the
# working tree is invisible to the site — that is the whole failure this
# guards against — so the commit ALWAYS runs, and only the push is optional.
# A push that fails then costs nothing: the work is already committed and one
# `git push` sends it.
def git_commit_paths(paths, message):
    return _git([["git", "add"] + list(paths), ["git", "commit", "-m", message]])

def git_push_only():
    return _git([["git", "push"]])

def git_publish(which, message, push=True):
    ok, out = git_commit_paths([MUSIC_REL[w] for w in targets(which)], message)
    if not ok or not push:
        return ok, out
    ok2, out2 = git_push_only()
    return ok2, out + "\n" + out2


def git_books_publish(message, push=True):
    """Commit and push private/books/index.json. One file, both sites: the
    catalogue is shared and each entry's own "public" flag decides whether
    Samovar shows it."""
    ok, out = git_commit_paths([BOOKS_REL], message)
    if not ok or not push:
        return ok, out
    ok2, out2 = git_push_only()
    return ok2, out + "\n" + out2

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

def yt_start(s):
    """Seconds from a link's own timestamp (&t=873, &t=14m33s). One recording
    can then serve a whole book: paste it against each chapter with the
    timestamp where that chapter begins."""
    t = str(s or "")
    m = re.search(r"[?&#](?:t|start)=(\d+)h(\d+)m(\d+)s", t)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m = re.search(r"[?&#](?:t|start)=(\d+)m(\d+)s", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"[?&#](?:t|start)=(\d+)s?\b", t)
    return int(m.group(1)) if m else 0


def parse_ts(s):
    """Seconds from a bare timestamp typed on its own: 14:33, 1:14:33, 873,
    14m33s. None when the text is not a timestamp at all."""
    t = str(s or "").strip()
    if not t:
        return None
    m = re.fullmatch(r"(?:(\d+):)?(\d{1,2}):(\d{2})", t)
    if m:
        return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(\d+)s?", t)
    if m and (m.group(1) or m.group(2) or t.endswith("s")):
        return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3))
    if re.fullmatch(r"\d{1,6}", t):
        return int(t)
    return None


def yt_id(s):
    m = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})', s) \
        or re.fullmatch(r'\s*([A-Za-z0-9_-]{11})\s*', s)
    return m.group(1) if m else None


# ── Chapter videos ───────────────────────────────────────────────────────
# A YouTube reading pinned to the top of one chapter of a real book (as
# opposed to a song, which lives in music.json). Mostly poetry — one video per
# poem in a collection — but any chapter of any book can carry one.
#
# Videos live on the book's own entry in private/books/index.json, under a
# "videos" map keyed by chapter index:
#
#     "videos": { "3": { "youtube": "dQw4w9WgXcQ", "heading": "Парус" } }
#
# The heading is stored alongside the index because the reader matches on it
# FIRST. The app's chapter splitter has median-length and subtitle rules that
# can renumber a book if its FB2 is ever re-cut, and a video silently moving
# to the wrong poem is worse than one that fails to show. The index is only
# the fallback, for chapters whose heading is blank or repeated.
BOOKS_REL = "private/books/index.json"
BOOKS_PATH = os.path.join(REPO, "private", "books", "index.json")

def load_books():
    return json.load(open(BOOKS_PATH, encoding="utf-8"))

def save_books(data):
    json.dump(data, open(BOOKS_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

def book_id(b):
    """Stable handle for a catalogue entry — slug where there is one."""
    return b.get("slug") or b.get("filename") or (b.get("title") or "")

def book_sites(b):
    """Where this book already appears. Videos follow the book, so there is no
    separate publish target for them: one index.json serves both sites and the
    entry's own "public" flag decides whether Samovar sees it."""
    return "Govorim + Samovar" if b.get("public") is True else "Govorim only"

# Leaf <section> titles in document order — a picking aid, not the reader's own
# split. Exact agreement is not required precisely because the heading, not the
# number, is what binds the video to the chapter.
SEC_OPEN = re.compile(r"<section\b[^>]*>", re.I)
SEC_CLOSE = re.compile(r"</section\s*>", re.I)
TITLE_BLK = re.compile(r"<title\b[^>]*>(.*?)</title\s*>", re.I | re.S)
TAGS = re.compile(r"<[^>]+>")

def chapter_headings(b):
    """[(index, heading)] for a book, or [] when the FB2 cannot be read."""
    fn = b.get("filename") or ""
    for tree in ("public", "private"):
        path = os.path.join(REPO, tree, "books", fn)
        if os.path.isfile(path):
            break
    else:
        return []
    try:
        raw = io.open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    raw = re.sub(r"<binary[\s\S]*?</binary>", "", raw)
    # Walk the section tags, remembering where each opened; a section that
    # closes with nothing opened inside it is a leaf.
    out, stack = [], []
    for m in re.finditer(r"<section\b[^>]*>|</section\s*>", raw, re.I):
        if m.group(0).lower().startswith("</"):
            if not stack:
                continue
            start, had_child = stack.pop()
            if stack:
                stack[-1] = (stack[-1][0], True)
            if had_child:
                continue
            body = raw[start:m.start()]
            t = TITLE_BLK.search(body)
            head = ""
            if t:
                head = TAGS.sub(" ", t.group(1))
                head = re.sub(r"\s+", " ", head).strip()
            out.append(head)
        else:
            if stack:
                stack[-1] = (stack[-1][0], True)
            stack.append((m.end(), False))
    return list(enumerate(out))

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
 h2{color:#c4955a;font-size:1.15em;font-weight:600;margin:38px 0 2px;
    border-top:1px solid #3a3226;padding-top:22px}
 .count{color:#7a6d58;font-size:.72em;font-weight:400;font-family:monospace}
 .empty{color:#7a6d58;font-style:italic;margin-top:10px}
 .art{margin-top:18px}
 .art-name{color:#e8ddcb;font-weight:600;font-size:1.02em;
     border-bottom:1px solid #3a3226;padding-bottom:5px;margin-bottom:2px}
 .song{display:flex;align-items:baseline;gap:10px;padding:7px 0;
     border-bottom:1px solid #262019}
 .song:last-child{border-bottom:none}
 .s-title{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .s-meta{color:#7a6d58;font-size:.78em;font-family:monospace;flex-shrink:0}
 .song form{margin:0;flex-shrink:0}
 .del{background:none;border:1px solid #7a4444;color:#c07a6a;
     padding:3px 11px;font-size:.8em;font-weight:400;border-radius:5px}
 .del:hover{background:#3a2020;color:#e0a090}
 .edit{background:none;border:1px solid #4a3f30;color:#a89880;
     padding:3px 11px;font-size:.8em;font-weight:400;border-radius:5px}
 .edit:hover{background:#26211a;color:#e8ddcb;border-color:#c4955a}
 .editing{background:#241f16;border:1px solid #c4955a;border-radius:6px;
     padding:14px 18px;margin:16px 0;color:#c4955a}
 .editing b{color:#e8ddcb}
 .copybox{margin:0 6px 0 0;flex-shrink:0}
 .copyspacer{display:inline-block;width:13px;height:1px}
 .copybar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;
     background:#20251c;border:1px solid #3f5136;border-radius:6px;padding:11px 14px;margin-top:12px}
 .copybar button{background:#5a8556;color:#eaf3e8;font-size:.85em;padding:6px 14px}
 .copybar button:hover{background:#6c9b67}
 .copybar .lbl{color:#9db396;font-size:.85em}
 .copybar .none{color:#7a6d58;font-size:.85em;font-style:italic}
 .selall{background:none;border:1px solid #4a3f30;color:#a89880;font-size:.8em;padding:4px 10px}
 .confirm{background:#3a2020;border:1px solid #7a4444;border-radius:6px;padding:18px 20px;margin:18px 0}
 .confirm b{color:#e8ddcb}
 .cancel{background:none;border:1px solid #4a3f30;color:#a89880}
 .cancel:hover{background:#26211a;color:#e8ddcb}
</style>
"""

def catalogue_html(which):
    """The catalogue(s) as they stand. With "both" selected each file is listed
    separately, so every edit/delete button still names one real catalogue."""
    if which == "both":
        return "".join(catalogue_html(w) for w in targets(which))
    try:
        data = load_music(which)
    except Exception as e:
        return '<h2>Current catalogue</h2><div class="err">Couldn\'t read %s: %s</div>' % (
            html.escape(os.path.basename(music_path(which))), html.escape(str(e)))

    n_art, n_song = counts(data)
    head = '<h2>Current catalogue <span class="count">%s &middot; %d artist%s &middot; %d song%s</span></h2>' % (
        html.escape(os.path.basename(music_path(which))),
        n_art, "" if n_art == 1 else "s",
        n_song, "" if n_song == 1 else "s")

    if not data:
        return head + '<div class="empty">Nothing in this catalogue yet.</div>'

    dest = other(which)
    have_there = song_keys(dest)
    formid = "copy-" + which
    missing = 0

    out = [head]
    for a in sorted(data, key=lambda x: (x.get("artist") or "").lower()):
        songs = a.get("songs") or []
        out.append('<div class="art"><div class="art-name">%s <span class="count">%d</span></div>'
                   % (html.escape(a.get("artist") or "—"), len(songs)))
        for sg in songs:
            lines = len((sg.get("lyrics") or "").strip().splitlines())
            key = (artist_key(a.get("artist") or ""), (sg.get("title") or "").strip().lower())
            if key in have_there:
                box = '<span class="copybox copyspacer"></span>'
            else:
                missing += 1
                box = ('<input class="copybox cb-%s" type="checkbox" form="%s" name="copy" '
                       'value="%s" title="copy to %s">'
                       % (which, formid,
                          html.escape((a.get("artist") or "") + "|||" + (sg.get("title") or "")),
                          html.escape(MUSIC_LABELS[dest])))
            out.append(
                '<div class="song">'
                + box +
                '<span class="s-title">%s</span>'
                '<span class="s-meta">%s &middot; %d line%s</span>'
                '<form method="post" action="/edit" enctype="multipart/form-data">'
                '<input type="hidden" name="catalogue" value="%s">'
                '<input type="hidden" name="artist" value="%s">'
                '<input type="hidden" name="title" value="%s">'
                '<button type="submit" class="edit">edit</button>'
                '</form>'
                '<form method="post" action="/delete" enctype="multipart/form-data">'
                '<input type="hidden" name="catalogue" value="%s">'
                '<input type="hidden" name="artist" value="%s">'
                '<input type="hidden" name="title" value="%s">'
                '<button type="submit" class="del">delete</button>'
                '</form></div>'
                % (html.escape(sg.get("title") or "—"),
                   html.escape(sg.get("youtube") or "no id"),
                   lines, "" if lines == 1 else "s",
                   html.escape(which),
                   html.escape(a.get("artist") or ""),
                   html.escape(sg.get("title") or ""),
                   html.escape(which),
                   html.escape(a.get("artist") or ""),
                   html.escape(sg.get("title") or "")))
        out.append('</div>')

    # Copying across catalogues. The form sits OUTSIDE the song rows and the
    # checkboxes point at it by id — the rows already carry their own
    # edit/delete forms, and HTML forms cannot nest.
    out.append('<form class="copybar" id="%s" method="post" action="/copy" '
               'enctype="multipart/form-data">' % formid)
    out.append('<input type="hidden" name="catalogue" value="%s">' % html.escape(which))
    if missing:
        # No "<" in the handler: it sits in an HTML attribute.
        out.append('<button type="button" class="selall" onclick="'
                   "var b=document.getElementsByClassName('cb-%s');"
                   "for(var i=b.length;i--;)b[i].checked=!b[i].checked;"
                   '">select all</button>' % which)
        out.append('<span class="lbl">%d song%s not in %s</span>'
                   % (missing, "" if missing == 1 else "s", html.escape(MUSIC_LABELS[dest])))
        out.append('<button type="submit">Copy checked \u2192 %s</button>'
                   % html.escape("govorim" if dest == "private" else "Samovar"))
    else:
        out.append('<span class="none">Every song here is already in %s.</span>'
                   % html.escape(MUSIC_LABELS[dest]))
    out.append('</form>')
    return "".join(out)

def edit_page(which, orig_artist, orig_title, song, msg=""):
    """The add form, pre-filled, writing back over one existing song."""
    artists = ""
    try:
        artists = "".join('<option value="%s">' % html.escape(a["artist"])
                          for a in load_music(which))
    except Exception:
        pass
    return """<!doctype html><meta charset="utf-8"><title>Govorim \u2014 edit song</title>%s
<a class="quit" href="/quit">quit</a>
<h1>Edit a song</h1>%s
<div class="editing">Editing <b>%s \u2014 %s</b> in <b>%s</b>.
Change the artist to move the song to a different one.</div>
<form method="post" action="/edit/save" enctype="multipart/form-data">
 <input type="hidden" name="catalogue" value="%s">
 <input type="hidden" name="orig_artist" value="%s">
 <input type="hidden" name="orig_title" value="%s">
 <label>Artist</label>
 <input type="text" name="artist" list="artists" value="%s" required>
 <datalist id="artists">%s</datalist>
 <label>Song title</label>
 <input type="text" name="title" value="%s" required>
 <label>YouTube link (or bare video ID)</label>
 <input type="text" name="youtube" value="%s" required>
 <label>Lyrics</label>
 <textarea name="lyrics" required>%s</textarea>
 <label>\u2026or replace them from a .txt file</label>
 <input type="file" name="lyricsfile" accept=".txt">
 <div class="row">
  <button type="submit">Save changes</button>
  <a href="/?catalogue=%s"><button type="button" class="cancel">Cancel</button></a>
 </div>
</form>""" % (STYLE, msg,
              html.escape(orig_artist), html.escape(orig_title),
              html.escape(MUSIC_LABELS[which]),
              html.escape(which),
              html.escape(orig_artist), html.escape(orig_title),
              html.escape(song.get("artist_shown") or orig_artist),
              artists,
              html.escape(song.get("title") or ""),
              html.escape(song.get("youtube") or ""),
              html.escape(song.get("lyrics") or ""),
              html.escape(which))

def confirm_page(which, artist, title, lines):
    """Deleting is not undoable, so it takes a second click."""
    return """<!doctype html><meta charset="utf-8"><title>Govorim — delete song</title>%s
<a class="quit" href="/quit">quit</a>
<h1>Delete a song</h1>
<div class="confirm">
 <p>Remove <b>%s &mdash; %s</b> (%d line%s of lyrics) from <b>%s</b>?</p>
 <p>This rewrites the catalogue file. There's no undo inside this tool &mdash;
 recovery means <code>git checkout</code> on the file.</p>
</div>
<form method="post" action="/delete/confirm" enctype="multipart/form-data">
 <input type="hidden" name="catalogue" value="%s">
 <input type="hidden" name="artist" value="%s">
 <input type="hidden" name="title" value="%s">
 <div class="row">
  <button type="submit" class="del">Delete it</button>
  <a href="/?catalogue=%s"><button type="button" class="cancel">Cancel</button></a>
 </div>
</form>""" % (STYLE, html.escape(artist), html.escape(title),
              lines, "" if lines == 1 else "s",
              html.escape(MUSIC_LABELS[which]),
              html.escape(which), html.escape(artist), html.escape(title),
              html.escape(which))

def form_page(msg="", which="private"):
    artists = ""
    try:
        seen, opts = set(), []
        for w in targets(which):
            for a in load_music(w):
                if a["artist"] not in seen:
                    seen.add(a["artist"])
                    opts.append('<option value="%s">' % html.escape(a["artist"]))
        artists = "".join(opts)
    except Exception:
        pass
    options = "".join(
        '<option value="%s"%s>%s</option>' % (k, " selected" if k == which else "", MUSIC_LABELS[k])
        for k in ("private", "public", "both")
    )
    return """<!doctype html><meta charset="utf-8"><title>Govorim — add song</title>%s
<a class="quit" href="/quit">quit</a>
<h1>Add a song</h1>
<p class="hint"><a href="/videos" style="color:#c4955a">Chapter videos →</a> — attach a YouTube reading to a chapter of any book</p>%s
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
 </div>
</form>
%s""" % (STYLE, msg, options, artists, catalogue_html(which))


def videos_index_page(msg=""):
    """Every catalogue book, plus a jump list of the ones already carrying
    videos — the second is what you actually use day to day, so it goes on
    top."""
    try:
        books = load_books()
    except Exception as e:
        return """<!doctype html><meta charset="utf-8"><title>Govorim — videos</title>%s
<a class="quit" href="/quit">quit</a><h1>Chapter videos</h1>
<div class="err">Could not read %s — %s</div>""" % (STYLE, BOOKS_REL, html.escape(str(e)))

    loaded = [b for b in books if (b.get("videos") or {})]
    loaded.sort(key=lambda b: (b.get("author") or "", b.get("title") or ""))

    if loaded:
        rows = "".join(
            '<option value="%s">%s — %s (%d)</option>' % (
                html.escape(book_id(b)),
                html.escape(b.get("author") or "?"),
                html.escape(b.get("title") or "?"),
                len(b.get("videos") or {}))
            for b in loaded)
        jump = """<form method="post" action="/videos/book">
 <label>Books with videos</label>
 <select name="book" onchange="this.form.submit()">
  <option value="">%d loaded — pick one to edit…</option>%s</select>
</form>""" % (len(loaded), rows)
    else:
        jump = '<div class="hint">No book has a video yet.</div>'

    allrows = "".join(
        '<option value="%s">%s — %s</option>' % (
            html.escape(book_id(b)),
            html.escape(b.get("author") or "?"),
            html.escape(b.get("title") or "?"))
        for b in sorted(books, key=lambda x: ((x.get("author") or ""), (x.get("title") or ""))))

    return """<!doctype html><meta charset="utf-8"><title>Govorim — chapter videos</title>%s
<a class="quit" href="/quit">quit</a>
<h1>Chapter videos</h1>%s
<p class="hint"><a href="/" style="color:#c4955a">← back to songs</a></p>
%s
<form method="post" action="/videos/book">
 <label>All works (%d)</label>
 <select name="book"><option value="">choose a book…</option>%s</select>
 <div class="row"><button type="submit">Open</button></div>
</form>""" % (STYLE, msg, jump, len(books), allrows)


def book_videos_page(bid, msg=""):
    books = load_books()
    b = next((x for x in books if book_id(x) == bid), None)
    if b is None:
        return videos_index_page('<div class="err">No book called %s.</div>' % html.escape(bid))

    chapters = chapter_headings(b)
    vids = b.get("videos") or {}
    by_head = {}
    for k, v in vids.items():
        if isinstance(v, dict) and v.get("heading"):
            by_head[v["heading"].strip().lower()] = v.get("youtube") or ""

    # When every chapter already points at the same recording, show it once in
    # the whole-work box instead of repeating it down every row.
    ids = set((v.get("youtube") if isinstance(v, dict) else v) or "" for v in vids.values())
    whole = ids.pop() if len(ids) == 1 else ""

    if not chapters:
        body = '<div class="err">Could not read the chapters out of %s.</div>' % html.escape(b.get("filename") or "?")
    else:
        rows = []
        for i, head in chapters:
            v = vids.get(str(i))
            if v is None and head:
                for vv in vids.values():
                    if isinstance(vv, dict) and (vv.get("heading") or "").strip().lower() == head.strip().lower():
                        v = vv
                        break
            vid = (v.get("youtube") if isinstance(v, dict) else v) or ""
            secs = int(v["start"]) if (isinstance(v, dict) and v.get("start")) else 0
            if whole and vid == whole:
                cur = ("%d:%02d" % (secs // 60, secs % 60)) if secs else ""
            elif vid:
                cur = vid + ("&t=%d" % secs if secs else "")
            else:
                cur = ""
            label = head or "(no heading)"
            rows.append(
                '<label>%d &nbsp; %s</label>'
                '<input type="text" name="v_%d" value="%s" placeholder="link, or just a time like 14:33 when using the video above">'
                '<input type="hidden" name="h_%d" value="%s">'
                % (i, html.escape(label), i, html.escape(cur), i, html.escape(head or "")))
        body = "".join(rows)

    return """<!doctype html><meta charset="utf-8"><title>Govorim — %s</title>%s
<a class="quit" href="/quit">quit</a>
<h1>%s</h1>%s
<p class="hint">%s &nbsp;·&nbsp; %s &nbsp;·&nbsp; <a href="/videos" style="color:#c4955a">← all works</a></p>
<div class="hint">Each chapter is its own page, and its video sits at the top of
 it. Clear a box to remove one.</div>
<div class="hint">One long reading of the whole work? Put it in the box below,
 then give each chapter just the time it starts at &mdash; <code>14:33</code>,
 <code>1:02:10</code>, or plain seconds. A chapter with a full link of its own
 keeps it.</div>
<form method="post" action="/videos/save">
 <input type="hidden" name="book" value="%s">
 <label>Video for the whole work &mdash; optional</label>
 <input type="text" name="wholevid" value="%s" placeholder="YouTube link or ID that every chapter below shares">
 %s
 <div class="row">
  <button type="submit">Save videos</button>
 </div>
</form>""" % (html.escape(b.get("title") or "?"), STYLE,
              html.escape(b.get("title") or "?"), msg,
              html.escape(b.get("author") or "?"), html.escape(book_sites(b)),
              html.escape(bid), html.escape(whole), body)

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
        if (self.path or "").startswith("/videos"):
            return self._send(videos_index_page())
        which = DEFAULT_CATALOGUE
        if "catalogue=public" in (self.path or ""):
            which = "public"
        elif "catalogue=private" in (self.path or ""):
            which = "private"
        self._send(form_page("", which))

    def _parse(self):
        """Fields from either a multipart form (the add form, which carries a
        file) or a plain urlencoded one."""
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        ctype = self.headers.get("Content-Type", "")
        # `multi` keeps EVERY value for a repeated name — the copy form sends
        # one "copy" field per ticked song, and a plain dict would keep only
        # the last one.
        fields, multi, filebytes = {}, {}, None
        if "multipart/" in ctype:
            msg = BytesParser(policy=email_default).parsebytes(
                b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body)
            for part in (msg.iter_parts() if msg.is_multipart() else []):
                name = part.get_param("name", header="content-disposition")
                if not name:
                    continue
                if part.get_filename():
                    if name == "lyricsfile":
                        filebytes = part.get_payload(decode=True)
                else:
                    payload = part.get_payload(decode=True) or b""
                    val = payload.decode("utf-8", errors="replace")
                    fields[name] = val
                    multi.setdefault(name, []).append(val)
        else:
            for k, v in urllib.parse.parse_qsl(body.decode("utf-8", errors="replace"),
                                               keep_blank_values=True):
                fields[k] = v
                multi.setdefault(k, []).append(v)
        return fields, multi, filebytes

    def _which(self, fields):
        w = (fields.get("catalogue") or DEFAULT_CATALOGUE).strip()
        return w if (w in MUSIC_FILES or w == "both") else "private"

    def _find(self, data, artist, title):
        """Locate an (artist entry, song) pair by exact stored spelling."""
        entry = next((a for a in data if (a.get("artist") or "") == artist), None)
        if entry is None:
            return None, None
        song = next((sg for sg in (entry.get("songs") or [])
                     if (sg.get("title") or "") == title), None)
        return entry, song

    def do_POST(self):
        fields, multi, filebytes = self._parse()
        if self.path.startswith("/videos/save"):
            return self.act_videos_save(fields)
        if self.path.startswith("/videos/book"):
            bid = (fields.get("book") or "").strip()
            return self._send(videos_index_page() if not bid else book_videos_page(bid))
        if self.path.startswith("/copy"):
            return self.act_copy(fields, multi)
        if self.path.startswith("/delete/confirm"):
            return self.act_delete(fields)
        if self.path.startswith("/delete"):
            return self.ask_delete(fields)
        if self.path.startswith("/edit/save"):
            return self.act_edit(fields, filebytes)
        if self.path.startswith("/edit"):
            return self.ask_edit(fields)
        return self.act_add(fields, filebytes)


    def act_videos_save(self, fields):
        """Write the video map back onto one book's catalogue entry.

        Only chapters with a usable id are stored, so clearing a box removes
        that video; a paste that is not recognisably YouTube is reported rather
        than silently dropped, because a typo that quietly does nothing is the
        worst outcome here."""
        bid = (fields.get("book") or "").strip()
        try:
            books = load_books()
        except Exception as e:
            return self._send(videos_index_page('<div class="err">%s</div>' % html.escape(str(e))))
        b = next((x for x in books if book_id(x) == bid), None)
        if b is None:
            return self._send(videos_index_page('<div class="err">No book called %s.</div>' % html.escape(bid)))

        # One recording can serve a whole work: name it once, then give each
        # chapter only the time it starts at. A chapter carrying a full link of
        # its own still wins.
        whole = yt_id(fields.get("wholevid") or "")
        videos, bad = {}, []
        for k, v in fields.items():
            if not k.startswith("v_"):
                continue
            raw = (v or "").strip()
            if not raw:
                continue
            idx = k[2:]
            vid, secs = yt_id(raw), yt_start(raw)
            if not vid:
                ts = parse_ts(raw)
                if ts is not None and whole:
                    vid, secs = whole, ts
                else:
                    bad.append(raw)
                    continue
            videos[idx] = {"youtube": vid, "heading": (fields.get("h_" + idx) or "").strip()}
            if secs:
                videos[idx]["start"] = secs

        if bad:
            return self._send(book_videos_page(
                bid, '<div class="err">Not a YouTube link: %s</div>'
                     % html.escape(", ".join(bad[:4]))))

        if videos:
            b["videos"] = videos
        else:
            b.pop("videos", None)
        save_books(books)

        note = "%d video%s on %s" % (len(videos), "" if len(videos) == 1 else "s",
                                     b.get("title") or bid)
        msg = '<div class="ok">Saved — %s (%s).</div>' % (html.escape(note),
                                                          html.escape(book_sites(b)))
        # The commit is not optional. A video that lives only in the working
        # tree never reaches the site, and `git push` reports nothing to do —
        # which is exactly the trap this used to set. Only the push is a choice.
        want_push = False
        ok, log = git_books_publish("Chapter videos: " + note, push=want_push)
        if ok:
            msg += ('<div class="ok">Committed and pushed — live after Vercel redeploys.</div>'
                    if want_push else
                    '<div class="ok">Committed. Run <code>git push origin main</code> to publish.</div>')
        else:
            msg += ('<div class="err">git step failed — the video IS saved in %s, '
                    'but it is not published yet:<pre>%s</pre></div>'
                    % (html.escape(BOOKS_REL), html.escape(log)))
        return self._send(book_videos_page(bid, msg))

    def ask_edit(self, fields):
        which = self._which(fields)
        artist = fields.get("artist", "").strip()
        title = fields.get("title", "").strip()
        try:
            data = load_music(which)
        except Exception as e:
            return self._send(form_page(
                '<div class="err">Couldn\'t read the catalogue: %s</div>'
                % html.escape(str(e)), which))
        entry, song = self._find(data, artist, title)
        if song is None:
            return self._send(form_page(
                '<div class="err">Couldn\'t find \u00ab%s\u00bb by %s \u2014 the catalogue may have '
                'changed since this page was loaded. Reload and try again.</div>'
                % (html.escape(title), html.escape(artist)), which))
        self._send(edit_page(which, artist, title, song))

    def act_edit(self, fields, filebytes):
        which = self._which(fields)
        orig_artist = fields.get("orig_artist", "").strip()
        orig_title = fields.get("orig_title", "").strip()
        artist = fields.get("artist", "").strip()
        title = fields.get("title", "").strip()
        yt = fields.get("youtube", "").strip()
        lyrics = fields.get("lyrics", "").strip()
        push = False

        if filebytes:
            lyrics = filebytes.decode("utf-8-sig", errors="replace").strip()
        lyrics = lyrics.replace("\r\n", "\n")

        try:
            data = load_music(which)
        except Exception as e:
            return self._send(form_page(
                '<div class="err">Couldn\'t read the catalogue: %s</div>'
                % html.escape(str(e)), which))

        old_entry, song = self._find(data, orig_artist, orig_title)
        if song is None:
            return self._send(form_page(
                '<div class="err">\u00ab%s\u00bb by %s is no longer in the catalogue \u2014 '
                'nothing was changed.</div>'
                % (html.escape(orig_title), html.escape(orig_artist)), which))

        def back(m):
            shown = dict(song)
            shown["title"] = title or song.get("title")
            shown["youtube"] = yt or song.get("youtube")
            shown["lyrics"] = lyrics or song.get("lyrics")
            shown["artist_shown"] = artist or orig_artist
            self._send(edit_page(which, orig_artist, orig_title, shown,
                                 '<div class="err">%s</div>' % html.escape(m)))

        if not (artist and title and yt):
            return back("Artist, title and YouTube link are all required.")
        if not lyrics:
            return back("Lyrics can't be empty. To remove the song entirely, use delete.")
        vid = yt_id(yt)
        if not vid:
            return back("Couldn't extract a YouTube video ID from: " + yt)

        artist = canon_artist(artist)
        dest = next((a for a in data if artist_key(a["artist"]) == artist_key(artist)), None)
        moving = dest is not old_entry

        clash = next((sg for sg in ((dest or {}).get("songs") or [])
                      if sg is not song and (sg.get("title") or "").strip().lower() == title.lower()), None)
        if clash is not None:
            return back("\u00ab%s\u00bb already exists for %s \u2014 not overwriting." % (title, dest["artist"]))

        song["title"] = title
        song["youtube"] = vid
        song["lyrics"] = lyrics

        dropped = False
        if moving:
            old_entry["songs"] = [sg for sg in old_entry["songs"] if sg is not song]
            if dest is None:
                dest = {"artist": artist, "songs": []}
                data.append(dest)
            elif canon_artist(dest["artist"]) != dest["artist"]:
                dest["artist"] = canon_artist(dest["artist"])
            dest["songs"].append(song)
            if not old_entry["songs"]:
                data = [a for a in data if a is not old_entry]
                dropped = True
        save_music(which, data)

        changes = []
        if artist_key(orig_artist) != artist_key(artist):
            changes.append("artist \u2192 %s" % html.escape(dest["artist"]))
        if orig_title != title:
            changes.append("title \u2192 %s" % html.escape(title))
        msg = '<div class="ok">Saved <b>%s \u2014 %s</b>%s.%s</div>' % (
            html.escape(dest["artist"] if moving else old_entry["artist"]),
            html.escape(title),
            (" (" + ", ".join(changes) + ")") if changes else "",
            (" %s had no songs left, so the artist was removed." % html.escape(orig_artist)) if dropped else "")

        site = "Samovar" if which == "public" else "Govorim"
        ok, out = git_publish(which, "%s music: edit %s \u2014 %s" % (site, artist, title), push=push)
        if ok:
            msg += ('<div class="ok">Committed and pushed \u2014 live after Vercel redeploys.</div>'
                    if push else COMMITTED_ONLY)
        else:
            msg += ('<div class="err">git step failed \u2014 the change IS saved in %s, '
                    'but it is not published yet.</div>'
                    % html.escape(os.path.basename(music_path(which))))
        msg += "<pre>%s</pre>" % html.escape(out)
        self._send(form_page(msg, which))

    def act_copy(self, fields, multi):
        """Copy ticked songs into the other catalogue, leaving the source alone."""
        which = self._which(fields)
        if which == "both":
            return self._send(form_page(
                '<div class="err">Pick one catalogue to copy FROM.</div>', which))
        dest = other(which)
        picks = multi.get("copy") or []
        push = False
        if not picks:
            return self._send(form_page(
                '<div class="err">Nothing ticked \u2014 tick the songs to copy first.</div>', which))
        try:
            src_data = load_music(which)
            dst_data = load_music(dest)
        except Exception as e:
            return self._send(form_page(
                '<div class="err">Couldn\'t read a catalogue: %s</div>' % html.escape(str(e)), which))

        added, skipped, gone = [], [], []
        for pick in picks:
            artist, _, title = pick.partition("|||")
            artist, title = artist.strip(), title.strip()
            entry, song = None, None
            for a in src_data:
                if artist_key(a["artist"]) == artist_key(artist):
                    entry = a
                    song = next((sg for sg in (a.get("songs") or [])
                                 if (sg.get("title") or "").strip() == title), None)
                    break
            if song is None:
                gone.append("%s \u2014 %s" % (artist, title)); continue
            want = canon_artist(entry["artist"])
            dst_entry = next((a for a in dst_data if artist_key(a["artist"]) == artist_key(want)), None)
            if dst_entry is not None and any(
                    (sg.get("title") or "").strip().lower() == title.lower()
                    for sg in dst_entry["songs"]):
                skipped.append("%s \u2014 %s" % (want, title)); continue
            if dst_entry is None:
                dst_entry = {"artist": want, "songs": []}
                dst_data.append(dst_entry)
            dst_entry["songs"].append({"title": song.get("title"),
                                       "youtube": song.get("youtube"),
                                       "lyrics": song.get("lyrics")})
            added.append("%s \u2014 %s" % (want, title))

        if added:
            save_music(dest, dst_data)

        msg = ""
        if added:
            msg += ('<div class="ok">Copied %d song%s into <b>%s</b>:<br>%s</div>'
                    % (len(added), "" if len(added) == 1 else "s",
                       html.escape(os.path.basename(music_path(dest))),
                       "<br>".join(html.escape(x) for x in added)))
        if skipped:
            msg += ('<div class="ok">Already there, left alone: %s</div>'
                    % "<br>".join(html.escape(x) for x in skipped))
        if gone:
            msg += ('<div class="err">No longer in the source catalogue: %s</div>'
                    % "<br>".join(html.escape(x) for x in gone))

        if added:
            site = "Govorim" if dest == "private" else "Samovar"
            label = added[0] if len(added) == 1 else "%d songs" % len(added)
            ok, out = git_publish(dest, "%s music: copy %s from %s"
                                  % (site, label,
                                     "Samovar" if which == "public" else "govorim"), push=push)
            if ok:
                msg += ('<div class="ok">Committed and pushed \u2014 live after Vercel redeploys.</div>'
                        if push else COMMITTED_ONLY)
            else:
                msg += ('<div class="err">git step failed \u2014 the songs ARE saved in %s, '
                        'but they are not published yet.</div>'
                        % html.escape(os.path.basename(music_path(dest))))
            msg += "<pre>%s</pre>" % html.escape(out)
        self._send(form_page(msg, which))

    def ask_delete(self, fields):
        which = self._which(fields)
        artist = fields.get("artist", "").strip()
        title = fields.get("title", "").strip()
        try:
            data = load_music(which)
        except Exception as e:
            return self._send(form_page(
                '<div class="err">Couldn\'t read the catalogue: %s</div>'
                % html.escape(str(e)), which))
        entry, song = self._find(data, artist, title)
        if song is None:
            return self._send(form_page(
                '<div class="err">Couldn\'t find \u00ab%s\u00bb by %s \u2014 the catalogue may have '
                'changed since this page was loaded. Reload and try again.</div>'
                % (html.escape(title), html.escape(artist)), which))
        lines = len((song.get("lyrics") or "").strip().splitlines())
        self._send(confirm_page(which, artist, title, lines))

    def act_delete(self, fields):
        which = self._which(fields)
        artist = fields.get("artist", "").strip()
        title = fields.get("title", "").strip()
        push = False
        try:
            data = load_music(which)
        except Exception as e:
            return self._send(form_page(
                '<div class="err">Couldn\'t read the catalogue: %s</div>'
                % html.escape(str(e)), which))
        entry, song = self._find(data, artist, title)
        if song is None:
            return self._send(form_page(
                '<div class="err">\u00ab%s\u00bb is no longer listed under %s \u2014 nothing was changed.</div>'
                % (html.escape(title), html.escape(artist)), which))

        entry["songs"] = [sg for sg in entry["songs"] if sg is not song]
        dropped = not entry["songs"]
        if dropped:
            data = [a for a in data if a is not entry]
        save_music(which, data)

        msg = '<div class="ok">Deleted <b>%s \u2014 %s</b>.%s</div>' % (
            html.escape(artist), html.escape(title),
            (" That was the last song by %s, so the artist was removed too."
             % html.escape(artist)) if dropped else "")

        site = "Samovar" if which == "public" else "Govorim"
        ok, out = git_publish(which, "%s music: remove %s \u2014 %s" % (site, artist, title), push=push)
        if ok:
            msg += ('<div class="ok">Committed and pushed \u2014 gone after Vercel redeploys.</div>'
                    if push else COMMITTED_ONLY)
        else:
            msg += ('<div class="err">git step failed \u2014 the song IS removed from %s, '
                    'but it is not published yet.</div>'
                    % html.escape(os.path.basename(music_path(which))))
        msg += "<pre>%s</pre>" % html.escape(out)
        self._send(form_page(msg, which))

    def act_add(self, fields, filebytes):
        which = self._which(fields)
        artist = fields.get("artist", "").strip()
        title = fields.get("title", "").strip()
        yt = fields.get("youtube", "").strip()
        lyrics = fields.get("lyrics", "").strip()
        push = False

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

        artist = canon_artist(artist)
        # Read every target BEFORE writing any, and refuse the whole add if the
        # song is already in one of them — a half-published song is worse than
        # a rejected one.
        loaded = []
        for w in targets(which):
            try:
                data = load_music(w)
            except Exception as e:
                return fail("Couldn't read %s: %s" % (os.path.basename(music_path(w)), e))
            entry = next((a for a in data if artist_key(a["artist"]) == artist_key(artist)), None)
            if entry is not None and any(
                    sg["title"].strip().lower() == title.lower() for sg in entry["songs"]):
                return fail("«%s» already exists for %s in %s — not overwriting."
                            % (title, entry["artist"], MUSIC_LABELS[w]))
            loaded.append((w, data, entry))

        shown = artist
        for w, data, entry in loaded:
            if entry is None:
                entry = {"artist": artist, "songs": []}
                data.append(entry)
            elif canon_artist(entry["artist"]) != entry["artist"]:
                # An entry saved under an older spelling is renamed to the official one.
                entry["artist"] = canon_artist(entry["artist"])
            entry["songs"].append({"title": title, "youtube": vid, "lyrics": lyrics})
            save_music(w, data)
            shown = entry["artist"]

        where = " and ".join(os.path.basename(music_path(w)) for w in targets(which))
        msg = '<div class="ok">Added <b>%s — %s</b> (video %s) to %s.</div>' % (
            html.escape(shown), html.escape(title), vid, html.escape(where))

        site = ("Govorim + Samovar" if which == "both"
                else "Samovar" if which == "public" else "Govorim")
        ok, out = git_publish(which, "%s music: add %s \u2014 %s" % (site, artist, title), push=push)
        if ok:
            msg += ('<div class="ok">Committed and pushed \u2014 live after Vercel redeploys.</div>'
                    if push else COMMITTED_ONLY)
        else:
            msg += ('<div class="err">git step failed \u2014 the song IS saved in %s, '
                    'but it is not published yet.</div>' % html.escape(where))
        msg += "<pre>%s</pre>" % html.escape(out)

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
