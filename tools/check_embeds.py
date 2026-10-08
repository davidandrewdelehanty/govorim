#!/usr/bin/env python3
"""Sweep every YouTube video the site embeds and find the ones that won't play
inside the page.

Run from WSL (it needs the network; nothing else does):
    python3 tools/check_embeds.py              # the whole catalogue + music
    python3 tools/check_embeds.py --ids P84Jlrdg5dY uIz2Mpcen-A   # spot-check

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

Writes tools/embed-issues.csv: one row per problem video per place it is used
(book + chapter, or song). Nothing in the catalogue is changed.
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
    a = ap.parse_args()

    if a.ids:
        for vid in a.ids:
            print(json.dumps(check(vid), ensure_ascii=False))
        return 0

    u = uses()
    cache = {}
    if os.path.exists(CACHE) and not a.recheck:
        cache = json.load(io.open(CACHE, encoding="utf-8"))
    todo = [v for v in u if cache.get(v, {}).get("verdict") not in DEFINITE]
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
