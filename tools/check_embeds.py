#!/usr/bin/env python3
"""Sweep every YouTube video the site embeds and find the ones that won't play
inside the page.

Run from WSL (it needs the network; nothing else does):
    python3 tools/check_embeds.py              # the whole catalogue + music
    python3 tools/check_embeds.py --ids P84Jlrdg5dY uIz2Mpcen-A   # spot-check
    python3 tools/check_embeds.py --max-age 0  # re-ask about every video, even ones that played before
    python3 tools/check_embeds.py --fix        # also take dead videos out of the catalogue
    python3 tools/check_embeds.py --from-browser tools/embed-browser.json   # merge real-player results

Videos YouTube answers with a bot check stay "unknown". Those are settled by
tools/embed_browser_check.js, which loads each one in a real embedded player on
samovar.live (paste it into the browser console there) and saves
embed-browser.json; --from-browser merges that file into the cache without
touching the network: a player that started is "ok", player error 150/101
(owner forbids embedding, or age-restricted) is "embed_off", 100/2 is "gone".

Two independent signals per video, both from YouTube itself:
  * oEmbed — youtube.com/oembed answers 401 when the owner has switched
    embedding off, 404/400 when the video is gone. One tiny request.
  * the watch page's playabilityStatus — status (OK / LOGIN_REQUIRED /
    UNPLAYABLE / ERROR), the reason text, and playableInEmbed; plus
    isFamilySafe from the microformat, which is false for age-restricted
    videos (those never play embedded: YouTube demands a sign-in).

Results are cached in tools/embed-check.json, so a run cut short — or one that
YouTube starts rate-limiting — picks up where it stopped. Anything YouTube
answered with a bot check is recorded as "unknown" and is asked again next run.

A video that played last time is asked about again once its check is older
than --max-age days (default 14): owners switch embedding off, take videos
down and make them private long after we placed them.

Writes tools/embed-issues.csv: one row per problem video per place it is used
(book + chapter, or song). Nothing in the catalogue is changed unless --fix,
which removes every video that is gone, private, age-restricted or has
embedding off from its chapter (or song), so the reader shows text instead of
a broken player. A backup of the catalogue is written first.
"""
import argparse, csv, io, json, os, re, sys, time, threading
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

MANIFEST = "private/books/index.json"
MUSIC = "public/music/music.json"
CACHE = "tools/embed-check.json"
REPORT = "tools/embed-issues.csv"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
           "Cookie": "CONSENT=YES+1; SOCS=CAI"}
UNKNOWN = "tools/embed-unknown.json"
DEFINITE = {"ok", "embed_off", "age", "private", "gone", "unplayable"}


def uses():
    """{video id: [(kind, title, where)]} for every embed on the site."""
    out = {}
    for b in json.load(io.open(MANIFEST, encoding="utf-8")):
        vids = b.get("videos") or {}
        for k in sorted(vids, key=lambda x: int(x) if str(x).isdigit() else 0):
            v = vids[k]
            if isinstance(v, dict) and v.get("youtube"):
                out.setdefault(v["youtube"], []).append(
                    ("book", b.get("title") or b.get("filename"),
                     "ch %s %s" % (k, v.get("heading") or "")))
        # Song-collection entries list one YouTube URL per song.
        for i, url in enumerate(b.get("songs") or []):
            m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", str(url or ""))
            if m:
                out.setdefault(m.group(1), []).append(
                    ("song", b.get("title") or b.get("filename"), "song %d" % (i + 1)))
    for a in json.load(io.open(MUSIC, encoding="utf-8")):
        for s in a.get("songs") or []:
            if s.get("youtube"):
                out.setdefault(s["youtube"], []).append(("song", a["artist"], s["title"]))
    return out


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


def player_response(html):
    i = html.find("ytInitialPlayerResponse")
    while i != -1:
        j = html.find("{", i)
        if j != -1 and j - i < 40:
            try:
                return json.JSONDecoder().raw_decode(html[j:])[0]
            except ValueError:
                pass
        i = html.find("ytInitialPlayerResponse", i + 1)
    return None


def check(vid):
    r = {"id": vid, "checked": time.strftime("%Y-%m-%d %H:%M")}
    code, _ = get("https://www.youtube.com/oembed?format=json&url="
                  "https://www.youtube.com/watch?v=" + vid)
    r["oembed"] = code

    code, html = get("https://www.youtube.com/watch?v=%s&hl=en&bpctr=9999999999" % vid)
    pr = player_response(html) if code == 200 else None
    ps = (pr or {}).get("playabilityStatus") or {}
    mf = ((pr or {}).get("microformat") or {}).get("playerMicroformatRenderer") or {}
    r["status"] = ps.get("status")
    r["reason"] = (ps.get("reason") or "").strip()
    r["embeddable"] = ps.get("playableInEmbed")
    r["family_safe"] = mf.get("isFamilySafe")
    r["title"] = mf.get("title", {}).get("simpleText") or \
        ((pr or {}).get("videoDetails") or {}).get("title")
    reason = r["reason"].lower()

    if "not a bot" in reason or (pr is None and r["oembed"] == 200):
        r["verdict"] = "unknown"          # bot check / fetch failure: ask again
    elif r["oembed"] in (400, 404) or r["status"] == "ERROR":
        r["verdict"] = "gone"
    elif "private" in reason:
        r["verdict"] = "private"
    elif "age" in reason or r["family_safe"] is False:
        r["verdict"] = "age"
    elif r["oembed"] == 401 or r["embeddable"] is False:
        r["verdict"] = "embed_off"
    elif r["status"] == "UNPLAYABLE":
        r["verdict"] = "unplayable"
    elif r["status"] == "OK":
        r["verdict"] = "ok"
    else:
        r["verdict"] = "unknown"
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", help="check just these ids (not cached)")
    ap.add_argument("--recheck", action="store_true", help="ignore the cache")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-age", type=float, default=14,
                    help="re-ask about videos that played if their check is older than this many days")
    ap.add_argument("--fix", action="store_true",
                    help="remove dead videos from the catalogue (backup written first)")
    ap.add_argument("--from-browser", metavar="JSON",
                    help="merge {id: 'ok'|'err150'|...} from embed_browser_check.js; no network")
    a = ap.parse_args()

    if a.ids:
        for vid in a.ids:
            print(json.dumps(check(vid), ensure_ascii=False))
        return 0

    u = uses()
    cache = {}
    if os.path.exists(CACHE) and not a.recheck:
        cache = json.load(io.open(CACHE, encoding="utf-8"))
    def stale(r):
        try:
            age = (time.time() - time.mktime(time.strptime(r.get("checked", ""), "%Y-%m-%d %H:%M"))) / 86400
        except ValueError:
            return True
        return age > a.max_age
    # Settled answers are kept, except that a video which played is asked about
    # again once its check is old: that is the one answer that goes stale.
    todo = [v for v in u if cache.get(v, {}).get("verdict") not in DEFINITE
            or (cache[v]["verdict"] == "ok" and stale(cache[v]))]
    if a.from_browser:
        got = json.load(io.open(a.from_browser, encoding="utf-8"))
        BV = {"ok": "ok", "okr": "ok", "ok3": "ok", "err150": "embed_off", "err101": "embed_off",
              "err100": "gone", "err2": "gone"}
        now, n = time.strftime("%Y-%m-%d %H:%M"), {}
        for vid, res in got.items():
            v = BV.get(res)
            if not v:
                continue                      # timeout / err5: still unknown
            r = dict(cache.get(vid) or {"id": vid})
            r.update(verdict=v, checked=now,
                     reason=("" if v == "ok" else "embedded player: error " + res[3:]),
                     via="browser")
            cache[vid] = r
            n[v] = n.get(v, 0) + 1
        print("merged from browser:", "  ".join("%s %d" % kv for kv in sorted(n.items())))
        todo = []
    print("%d videos in use, %d cached, %d to check" % (len(u), len(u) - len(todo), len(todo)))

    lock = threading.Lock()
    done = [0]

    def save():
        tmp = CACHE + ".tmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=1))
        os.replace(tmp, CACHE)

    bots = [0]
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(check, v): v for v in todo}
        for f in as_completed(futs):
            r = f.result()
            with lock:
                cache[r["id"]] = r
                done[0] += 1
                if r["verdict"] != "ok":
                    print("  %-11s %-10s %s" % (r["id"], r["verdict"], r["reason"][:70]), flush=True)
                if "not a bot" in r["reason"].lower():
                    bots[0] += 1
                if done[0] % 50 == 0:
                    save()
                    print("[%d/%d]" % (done[0], len(todo)), flush=True)
            if bots[0] >= 10:
                print("\nYouTube is asking for a bot check — stopping. "
                      "Wait a while and run again; finished checks are kept.")
                ex.shutdown(wait=False, cancel_futures=True)
                break
    save()

    rows = []
    for vid, places in u.items():
        r = cache.get(vid) or {"verdict": "unknown"}
        if r["verdict"] == "ok":
            continue
        for p in places:
            rows.append([r["verdict"], p[0], p[1], p[2], vid,
                         "https://youtu.be/" + vid, r.get("reason", ""), r.get("title") or ""])
    order = {"embed_off": 0, "age": 1, "private": 2, "gone": 3, "unplayable": 4, "unknown": 5}
    rows.sort(key=lambda x: (order.get(x[0], 9), x[1], x[2], x[3]))
    with io.open(REPORT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["verdict", "kind", "book/artist", "chapter/song", "id", "url", "reason", "video title"])
        w.writerows(rows)

    tally = {}
    for vid in u:
        v = (cache.get(vid) or {}).get("verdict", "unknown")
        tally[v] = tally.get(v, 0) + 1
    print("\n" + "  ".join("%s %d" % kv for kv in sorted(tally.items())))
    print("problem rows → %s" % REPORT)
    unk = sorted(v for v in u if (cache.get(v) or {}).get("verdict", "unknown") not in DEFINITE)
    io.open(UNKNOWN, "w", encoding="utf-8").write(json.dumps(unk) + "\n")
    if unk:
        print("%d unknown → %s (settle them with tools/embed_browser_check.js)" % (len(unk), UNKNOWN))

    if a.fix:
        dead = {vid for vid in u if (cache.get(vid) or {}).get("verdict") in
                ("embed_off", "age", "private", "gone", "unplayable")}
        if not dead:
            print("--fix: nothing to remove"); return 0
        raw = io.open(MANIFEST, encoding="utf-8").read()
        bak = MANIFEST + ".bak-embeds-" + time.strftime("%Y%m%d%H%M")
        io.open(bak, "w", encoding="utf-8").write(raw)
        idx = json.loads(raw)
        removed = 0
        for b in idx:
            vids = b.get("videos")
            if isinstance(vids, dict):
                for k in [k for k, v in vids.items() if isinstance(v, dict) and v.get("youtube") in dead]:
                    del vids[k]; removed += 1
                if not vids:
                    b.pop("videos", None)
            if isinstance(b.get("songs"), list):
                for i, url in enumerate(b["songs"]):
                    m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", str(url or ""))
                    if m and m.group(1) in dead:
                        b["songs"][i] = None; removed += 1
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
        print("--fix: removed %d chapter/song video(s) using %d dead id(s); backup %s" % (removed, len(dead), bak))
        print("       (music videos in %s are listed in the report but not edited)" % MUSIC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
