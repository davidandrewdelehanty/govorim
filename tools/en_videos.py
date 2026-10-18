#!/usr/bin/env python3
"""English recordings for the English column — the same idea as the Russian
`videos`, for a book's parallel English (parallelEn).

For each book with an English column it hunts YouTube for an English reading
of the English text (a LibriVox upload, usually), pulls the English captions,
finds where each chapter's English opens in them, and writes

  index.json  →  entry.videosEn = {"<chapter>": {youtube, start, end}, ...}
  public/books/audio-sync-en/<parallelEn>/<NN>.json  →  {paragraph key: seconds}

The reader shows that video in the docked player when the English pane is the
one on screen, and puts a ▶ beside each English paragraph it could place.

Long books are often uploaded in parts, so several videos may share a book:
each chapter takes the video whose transcript holds its opening best, and a
chapter no candidate holds simply has no English video.

As with the Russian: nothing trusts the uploader's title or chapter list.
A chapter is attached only where its own opening sentence is found, in order,
in the transcript.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/en_videos.py --slug anna-karenina            # one book
    python3 tools/en_videos.py --all --max-books 20            # a batch
    python3 tools/en_videos.py --slug X --force                # hunt again

Needs yt-dlp and a way out to YouTube (WSL). Searches, probes and captions are
cached in tools/en-hunt.json and tools/vtt/<id>.en.vtt, so re-running is cheap.
"""
import argparse, difflib, glob, io, json, os, re, statistics, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "tools")
from vtt_tokens import load as load_vtt
from reader_chapters import reader_chapters

MANIFEST = "private/books/index.json"
CACHE = "tools/en-hunt.json"
VTT = "tools/vtt/%s.en.vtt"
SYNC = "public/books/audio-sync-en/%s"
BLOCKED = "tools/hunt-blocked.txt"
RATE_LO, RATE_HI = 0.25, 0.70          # seconds per English word: a reading, not a summary
CH_MIN = 0.72                          # a chapter opening must match this well
SEARCH_N = 20
PROBE_MAX = 16


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("’", "'"))


def words(text):
    t = re.sub(r"[_*]", " ", str(text))
    return [x for x in (norm(w) for w in t.split()) if x]


def yt(args, timeout=180):
    try:
        return subprocess.run(["yt-dlp"] + args, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def search(q):
    try:
        d = json.loads(yt(["--skip-download", "--flat-playlist", "-J", "ytsearch%d:%s" % (SEARCH_N, q)]))
    except Exception:
        return []
    return [e for e in (d.get("entries") or []) if e and e.get("id")]


def probe(vid):
    try:
        j = json.loads(yt(["--skip-download", "-J", "https://www.youtube.com/watch?v=" + vid], 120))
    except Exception:
        return None
    if not isinstance(j, dict):
        return None
    ac = j.get("automatic_captions") or {}
    subs = j.get("subtitles") or {}
    lang = (j.get("language") or "").lower()
    # 'en-orig' is YouTube's own transcription of English speech; a bare 'en'
    # on a video in another language is a machine translation of its captions.
    en = ("en-orig" in ac) or any(k.startswith("en") for k in subs) or (lang.startswith("en") and "en" in ac)
    return {"id": vid, "dur": j.get("duration") or 0, "embed": bool(j.get("playable_in_embed")),
            "en": en, "title": (j.get("title") or "")[:100]}


def title_ok(want, got):
    w = [x for x in words(want) if len(x) > 2 and x not in ("the", "and", "part", "book")]
    g = set(words(got))
    if not w:
        return False
    return sum(1 for x in w if x in g) / len(w) >= 0.75


def en_chapters(dirname):
    """[(cidx, [(key, paragraph text), ...]), ...] from the English files."""
    out = []
    for f in sorted(glob.glob("public/books/%s/[0-9][0-9]*.json" % dirname)):
        m = re.search(r"(\d+)\.json$", f)
        try:
            j = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        paras = []
        for k in sorted((k for k in j if re.fullmatch(r"-?\d+", k)), key=int):
            first = str(j[k]).split("\n\n")[0].strip()
            if first:
                paras.append((k, first))
        out.append((int(m.group(1)) - 1, paras))
    return [c for c in out if c[1]]


def probes(paras, n=4):
    out = []
    for _, p in paras[:n + 3]:
        w = words(p)
        if len(w) >= 7:
            out.append(w[:14])
        if len(out) >= n:
            break
    return out


class Transcript:
    def __init__(self, vid):
        self.vid = vid
        self.toks = load_vtt(VTT % vid)
        self.times = [t for t, _ in self.toks]
        self.w = [norm(x) for _, x in self.toks]
        self.where = {}
        for i, x in enumerate(self.w):
            if x:
                self.where.setdefault(x, []).append(i)
        self.end = self.times[-1] if self.times else 0

    def find(self, op, lo=0, hi=None):
        """Best place for word list `op` at or after token lo: (score, index)."""
        hi = len(self.w) if hi is None else hi
        cands = set()
        for k in range(min(3, len(op))):
            for j in self.where.get(op[k], ()):
                if lo <= j - k < hi:
                    cands.add(j - k)
        best = (0.0, None)
        for j in sorted(cands):
            if j + len(op) > len(self.w):
                continue
            r = difflib.SequenceMatcher(None, self.w[j:j + len(op)], op, autojunk=False).ratio()
            if r > best[0]:
                best = (r, j)
                if r > 0.97:
                    break
        return best


def found_in(tr, chs):
    """{chapter: (start token, score)} for every chapter opening found in this
    transcript, searched forward so the order is the book's own."""
    out, cur = {}, 0
    for cidx, paras in chs:
        best = (0.0, None)
        for op in probes(paras):
            b = tr.find(op, cur)
            if b[0] > best[0]:
                best = b
            if best[0] >= 0.85:
                break
        if best[1] is not None and best[0] >= CH_MIN:
            cur = best[1] + 5
            out[cidx] = (best[1], best[0])
    return out


def place(chs, trs):
    """chapter -> (video, start token, end time).

    One reading per stretch of the book: the video holding the most chapters
    is taken first, then whichever holds most of what is left, and so on —
    so a book is not stitched together from a different narrator every
    chapter, which is what taking each chapter's best match on its own did.
    A chapter ends where the next chapter found in the SAME video begins
    (whoever reads that next chapter on the page), or at the video's end.
    """
    per = {tr.vid: (tr, found_in(tr, chs)) for tr in trs}
    left = {c for c, _ in chs}
    got = {}
    while left and per:
        vid, cover = max(((v, sum(sc for c, (_, sc) in f.items() if c in left))
                          for v, (_, f) in per.items()), key=lambda x: x[1])
        if cover <= 0:
            break
        tr, f = per.pop(vid)
        order = sorted(f, key=lambda c: f[c][0])
        for i, c in enumerate(order):
            if c not in left:
                continue
            j = f[c][0]
            t1 = tr.times[f[order[i + 1]][0]] if i + 1 < len(order) else tr.end
            got[c] = (tr, j, t1)
            left.discard(c)
    return got


def para_sync(paras, tr, t_lo, t_hi):
    lo = next((i for i, t in enumerate(tr.times) if t >= t_lo - 1), 0)
    hi = next((i for i, t in enumerate(tr.times) if t >= t_hi), len(tr.times))
    m, cur = {}, lo
    for k, p in paras:
        w = words(p)
        if len(w) < 5:
            continue
        op = w[:12]
        s, j = tr.find(op, cur, hi)
        if j is not None and s >= 0.6:
            m[k] = round(tr.times[j], 1)
            cur = j + len(op) // 2
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true", help="search YouTube again")
    ap.add_argument("--replace", action="store_true",
                    help="place again from the cached candidates and captions, without searching")
    ap.add_argument("--max-books", type=int, default=0)
    ap.add_argument("--english-books", action="store_true",
                    help="the Read in English library's own books (lang en): their recording is the book's "
                         "main video (`videos`, jump points in audio-sync/), not an English column's")
    a = ap.parse_args()
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    blocked = set()
    if os.path.exists(BLOCKED):
        blocked = {l.split("#")[0].strip() for l in io.open(BLOCKED, encoding="utf-8")} - {""}
    if a.english_books:
        books = [b for b in idx if b.get("lang") == "en" and b.get("filename") and
                 (a.all or b.get("slug") in a.slug) and (a.force or a.replace or not b.get("videos"))]
    else:
        books = [b for b in idx if b.get("parallelEn") and b.get("enTitle") and
                 (a.all or b.get("slug") in a.slug) and (a.force or a.replace or not b.get("videosEn"))]
    if a.max_books:
        books = books[:a.max_books]
    if not books:
        print("nothing to do (no matching book with an English column, or all already have videosEn)")
        return
    os.makedirs("tools/vtt", exist_ok=True)
    done = 0
    for bi, b in enumerate(books, 1):
        s = b["slug"]
        if a.english_books:
            # The book IS the English: its chapters as the reader cuts them,
            # each paragraph keyed by its index — what the jump buttons read.
            rc, _ = reader_chapters(os.path.join("public/books", b["filename"]))
            chs = [(ci, [(str(pi), p) for pi, p in enumerate(c["paras"]) if p.strip()]) for ci, c in enumerate(rc)]
            chs = [c for c in chs if c[1]]
            heads = {ci: c["heading"] for ci, c in enumerate(rc)}
        else:
            chs = en_chapters(b["parallelEn"])
        total = sum(len(" ".join(p for _, p in ps).split()) for _, ps in chs)
        title = re.sub(r"\s*[,:(].*$", "", b["enTitle"]).strip() or b["enTitle"]
        au = re.sub(r"\s*\(.*\)", "", b.get("enAuthor") or "").split()
        au = au[-1] if au else ""
        print("[%d/%d] %s — %s (%s) · %d chapters, %d words" % (bi, len(books), s, title, au, len(chs), total), flush=True)
        if not chs or total < 300:
            print("   no English text to match"); continue
        def hunt(queries, have):
            seen, found = set(have), []
            for q in queries:
                for e in search(q):
                    vid = e["id"]
                    if vid in seen or vid in blocked:
                        continue
                    seen.add(vid)
                    d = e.get("duration") or 0
                    if d and (d < 120 or d > total * RATE_HI * 1.5):
                        continue
                    if not title_ok(title, e.get("title") or ""):
                        continue
                    found.append(vid)
            probed = []
            for vid in found[:PROBE_MAX]:
                p = probe(vid)
                if p and p["embed"] and p["en"] and p["dur"]:
                    probed.append(p)
            return probed

        def transcripts(cands):
            out = []
            for c in cands:
                if not os.path.exists(VTT % c["id"]):
                    yt(["--write-auto-sub", "--write-sub", "--sub-lang", "en-orig,en", "--sub-format", "vtt",
                        "--skip-download", "--quiet", "-o", "tools/vtt/%(id)s", "https://youtu.be/" + c["id"]], 300)
                    for alt in ("tools/vtt/%s.en-orig.vtt" % c["id"], "tools/vtt/%s.en-US.vtt" % c["id"],
                                "tools/vtt/%s.en-GB.vtt" % c["id"]):
                        if os.path.exists(alt) and not os.path.exists(VTT % c["id"]):
                            os.replace(alt, VTT % c["id"])
                if os.path.exists(VTT % c["id"]):
                    tr = Transcript(c["id"])
                    if len(tr.w) > 200:
                        out.append(tr)
            return out

        ent = cache.get(s) if not a.force else None
        if not ent:
            ent = {"cands": hunt(("%s %s audiobook" % (title, au), "%s audiobook full" % title,
                                  "%s %s librivox" % (title, au)), ()), "at": int(time.time())}
            cache[s] = ent
            io.open(CACHE, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=1))
        if not ent["cands"]:
            print("   no embeddable English reading with English captions found"); continue
        trs = transcripts(ent["cands"])
        if not trs:
            print("   no transcripts came down"); continue
        # A long book is usually uploaded in parts, and the first search finds
        # some parts and not others. When chapters are still missing, look
        # for the parts by number, once per book.
        got = place(chs, trs)
        if len(got) < len(chs) * 0.9 and not ent.get("parts"):
            print("   %d/%d chapters found — looking for the other parts" % (len(got), len(chs)), flush=True)
            more = hunt(["%s audiobook part %d" % (title, k) for k in range(1, 9)],
                        [c["id"] for c in ent["cands"]])
            ent["cands"] = ent["cands"] + more
            ent["parts"] = True
            io.open(CACHE, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=1))
            if more:
                trs = trs + transcripts(more)
        got = place(chs, trs)
        if not got:
            print("   %d candidate(s), no chapter opening found in any of them" % len(trs)); continue
        # chapter spans: up to the next placed chapter in the same video
        wc = {c: len(" ".join(p for _, p in ps).split()) for c, ps in chs}
        paras_of = dict(chs)
        v, rates, odd = {}, [], 0
        for c in sorted(got):
            tr, j, t1 = got[c]
            t0 = tr.times[j]
            r = (t1 - t0) / max(wc.get(c, 1), 1)
            # A span far too short or too long for its words is a misplaced
            # start or end: that chapter goes without rather than play wrong.
            if wc.get(c, 0) >= 150 and not (0.2 <= r <= 1.0):
                odd += 1
                continue
            v[c] = {"youtube": tr.vid, "start": max(0, int(t0) - 1), "end": int(t1) + 1}
            rates.append(r)
        if odd:
            print("   %d chapter(s) dropped: their span does not fit their length" % odd)
        if not v:
            print("   nothing placed with a believable span"); continue
        if rates:
            r = statistics.median(rates)
            if r < RATE_LO or r > RATE_HI:
                print("   !! %.2f s/word is not a reading of this text — refused" % r); continue
        sync_dir = ("public/books/audio-sync/%s" % os.path.basename(b["filename"]).rsplit(".", 1)[0]
                    if a.english_books else SYNC % b["parallelEn"])
        os.makedirs(sync_dir, exist_ok=True)
        synced = 0
        for c, x in v.items():
            tr = next(t for t in trs if t.vid == x["youtube"])
            m = para_sync(paras_of[c], tr, x["start"], x["end"])
            if len(m) * 4 >= len(paras_of[c]):
                json.dump(m, io.open(os.path.join(sync_dir, "%02d.json" % c), "w", encoding="utf-8"))
                synced += 1
        out = {}
        for c in sorted(v):
            x = dict(v[c])
            if x["start"] == 0:
                del x["start"]
            if a.english_books:
                x["heading"] = heads.get(c, "")
            out[str(c)] = x
        done += 1
        print("   placed %d/%d chapters in %d video(s); jump points for %d" % (
            len(v), len(chs), len({x["youtube"] for x in v.values()}), synced), flush=True)
        # Re-read the catalogue and change only this book: other scripts may
        # have written it while this one ran, and a stale copy would undo them.
        fresh = json.load(io.open(MANIFEST, encoding="utf-8"))
        for e in fresh:
            if e.get("slug") == s:
                e["videos" if a.english_books else "videosEn"] = out
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(fresh, ensure_ascii=False, indent=2) + "\n")
    print("\n%d of %d book(s) given English videos" % (done, len(books)))


if __name__ == "__main__":
    main()
