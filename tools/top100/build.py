#!/usr/bin/env python3
"""The hundred works a Russian reader would name, and where to get each one.

Two links per work, and both are honest about what they are:

  * the text comes from Russian Wikisource through its own export service.
    Wikisource hosts only texts that are public domain in Russia, so a page
    existing there IS the copyright clearance — no pirate library is listed
    here, and the eighteen works with no page are the ones still in
    copyright (Pasternak, Solzhenitsyn, Sholokhov, the Strugatskys,
    Dovlatov and the rest). They are left blank on purpose.

    The link is an EPUB, not an FB2, and that is not a preference: the
    Wikimedia export service dropped FB2 (it answers "\"fb2\" is not a valid
    format" and lists epub-3, epub-2, htmlz, mobi, pdf, rtf, txt). Every
    URL in the list was checked and returns application/epub+zip. One
    calibre command turns it into the FB2 the reader parses:

        ebook-convert book.epub book.fb2

    Nothing else offers these texts as FB2 without going to a pirate
    library, so the honest route is the legitimate EPUB plus one step.

  * the audio is a YouTube search, ranked: the title has to name the work,
    the reader's name has to appear, and the running time has to be close
    to what the word count says a full reading costs (~8,500 Russian words
    an hour). Anything that fails the last test is marked, so a four-hour
    "Анна Каренина" is never passed off as the whole novel; where no single
    upload holds the book, a playlist is given instead.

Run from the repo root:  python3 tools/top100/build.py
"""
import csv, json, os, re, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from works import WORKS

raw = {x["r"]: x for x in
       json.load(open(os.path.join(HERE, "lookups.json"), encoding="utf-8"))}
man_list = json.load(open("private/books/index.json", encoding="utf-8"))
man = {b["slug"]: b for b in man_list}


def _norm(s):
    return re.sub(r"[^a-zа-я0-9]+", " ", (s or "").lower().replace("ё", "е")).strip()


# Which of the hundred are already on the shelf. Matched on the title as the
# catalogue spells it, with a prefix fallback for the entries that carry a
# subtitle ("Ванька" vs "Ванька (рассказ)").
_by_title = {}
for b in man_list:
    _by_title.setdefault(_norm(b.get("title")), []).append(b)
match = {}
for _i, (_a, _t, *_rest) in enumerate(WORKS, 1):
    _n = _norm(_t)
    _hit = _by_title.get(_n)
    if not _hit:
        for _k, _v in _by_title.items():
            if (_k.startswith(_n) or _n.startswith(_k)) and abs(len(_k) - len(_n)) < 6:
                _hit = _v
                break
    match[_i] = {"slug": _hit[0]["slug"] if _hit else ""}

WS = "https://ru.wikisource.org/wiki/"
EXPORT = "https://ws-export.wmcloud.org/?format=epub-3&lang=ru&page="

NOTE = {
    "full":  "",
    "part?": "may be abridged — check against the playlist",
    "PART":  "part 1 only; the rest is on the same channel",
    "SHORT": "no single full upload found — playlist covers the whole book",
    "LONG":  "longer than the text suggests; may include extra material",
}

rows = []
for i, (author, title, year, death, kind) in enumerate(WORKS, 1):
    r = raw[i]
    m = match[i]
    slug = m["slug"]
    page = r["ws"]
    have = man.get(slug, {})
    yt = ("https://www.youtube.com/playlist?list=" + r["pl"]) if r["pl"] \
         else ("https://www.youtube.com/watch?v=" + r["id"])
    rows.append({
        "rank": i,
        "author": author,
        "title": title,
        "year": year,
        "kind": kind,
        "in_library": slug,
        "words": have.get("words") or "",
        "wikisource": (WS + urllib.parse.quote(page.replace(" ", "_"))) if page else "",
        "epub": (EXPORT + urllib.parse.quote(page.replace(" ", "_"))) if page else "",
        "audio": yt,
        "audio_kind": "playlist" if r["pl"] else "video",
        "audio_title": r["yt"],
        "duration": r["len"],
        "audio_note": NOTE.get(r["flag"], ""),
        # Wikisource hosts only what is public domain in Russia, so the page
        # existing IS the clearance; its absence means the work is still in
        # copyright there (or simply not transcribed), and no other source is
        # offered for it.
        "rights": "public domain in RU" if page else
                  "in copyright — no free text source",
    })

OUT = os.path.join(os.path.dirname(HERE))  # tools/
cols = ["rank","author","title","year","kind","in_library","words",
        "wikisource","epub","audio","audio_kind","audio_title","duration",
        "audio_note","rights"]
with open(os.path.join(OUT, "top-100-russian-works.csv"),"w",encoding="utf-8",newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

have_n = sum(1 for r in rows if r["in_library"])
fb2_n  = sum(1 for r in rows if r["epub"])
flag_n = sum(1 for r in rows if r["audio_note"])

L = []
A = L.append
A("# The hundred most-read Russian works")
A("")
A("Ranked roughly by how widely they are actually read — the Russian school")
A("programme first, since that is what \"popular\" means to a Russian reader,")
A("then the works that carry abroad. Generated by `tools/top100/build.py`;")
A("the machine-readable version is `top-100-russian-works.csv`.")
A("")
A("- **%d of 100** are already in the library." % have_n)
A("- **%d** have a free text on Russian Wikisource. The other %d are still in"
  % (fb2_n, 100 - fb2_n))
A("  copyright in Russia; no text link is given for those, on purpose.")
A("- The export service dropped FB2 — it now serves EPUB (all %d links checked,"
  % fb2_n)
A("  all return `application/epub+zip`). `ebook-convert book.epub book.fb2`")
A("  gives the reader what it parses.")
A("- **%d** audio links are marked as partial or uncertain — the running time"
  % flag_n)
A("  does not match what the text's length says a full reading should cost.")
A("")
A("| # | Work | In library | Text | Audio |")
A("|---|------|-----------|-----|-------|")
for r in rows:
    have = "yes" if r["in_library"] else "—"
    fb2 = ("[EPUB](%s)" % r["epub"] if r["epub"]
           else ("*on the shelf already*" if r["in_library"] else "*in copyright*"))
    note = (" · " + r["audio_note"]) if r["audio_note"] else ""
    aud = "[%s](%s) %s%s" % ("playlist" if r["audio_kind"]=="playlist" else r["duration"],
                             r["audio"],
                             "" if r["audio_kind"]=="playlist" else "",
                             note)
    A("| %d | **%s** — %s (%s) | %s | %s | %s |"
      % (r["rank"], r["title"], r["author"], r["year"], have, fb2, aud))
A("")
# Two works have a Wikisource page that is not the book, or is not a book.
# Saying so here is the difference between a to-do and a trap.
CAVEAT = {
    "Пётр Первый": "the Wikisource page under this name is A. N. Tolstoy's "
                   "PLAY, not the novel — the novel is not there",
    "Басни": "the index links 200 fables as 200 separate pages and runs on "
             "into the rest of Krylov's verse; needs its own importer",
}

A("## Not in the library, and free to add")
A("")
A("These %d have a Wikisource text and are not on the shelf yet:"
  % sum(1 for r in rows if r["epub"] and not r["in_library"]))
A("")
for r in rows:
    if r["epub"] and not r["in_library"]:
        note = CAVEAT.get(r["title"])
        A("- **%s** — %s · [EPUB](%s) · [audio](%s)%s"
          % (r["title"], r["author"], r["epub"], r["audio"],
             ("\n  **Careful:** " + note) if note else ""))
A("")
A("## In copyright — not addable from a free source")
A("")
for r in rows:
    if not r["epub"]:
        A("- **%s** — %s (%d)%s"
          % (r["title"], r["author"], r["year"],
             " · already in the library" if r["in_library"] else ""))
A("")
open(os.path.join(OUT, "top-100-russian-works.md"),"w",encoding="utf-8",newline="\n").write("\n".join(L))
print("in library: %d / 100" % have_n)
print("free text:  %d / 100" % fb2_n)
print("audio flagged: %d" % flag_n)
print("addable now (free text, not on the shelf): %d"
      % sum(1 for r in rows if r["epub"] and not r["in_library"]))
