#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""How far the audio hunt has got, and how long it has left.

tail -f on the log tells you what is happening this second. This tells you
where the run is: the hunt rewrites tools/hunt-results.json after every book,
so counting it is exact and works just as well if the log was lost or the run
was restarted.

    python3 tools/hunt_progress.py              # one line and out
    python3 tools/hunt_progress.py --watch      # every 30s, with a rate
    python3 tools/hunt_progress.py --watch 10 --misses

The rate is measured over the watching, not over the whole run, so it settles
on what the hunt is doing now rather than averaging in the hour it spent on
books it had already answered.
"""
import argparse
import io
import json
import os
import time

WANTED = "tools/hunt-wanted.json"
RESULTS = "tools/hunt-results.json"
VTT = "tools/vtt"
LOG = "tools/hunt.log"


def load(path, default):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return default


def snapshot():
    wanted = load(WANTED, [])
    want = {w.get("file") for w in wanted if isinstance(w, dict)}
    results = load(RESULTS, [])
    done = [r for r in results if r.get("file") in want]
    picked = [r for r in done if r.get("pick")]
    capt = [r for r in picked if (r.get("pick") or {}).get("ru_orig")]
    vtts = 0
    try:
        vtts = len([f for f in os.listdir(VTT) if f.endswith(".ru.vtt")])
    except Exception:
        pass
    return {"want": len(want), "done": len(done), "picked": len(picked),
            "captioned": len(capt), "bare": len(picked) - len(capt),
            "missed": len(done) - len(picked), "vtt": vtts}


def last_line():
    try:
        with io.open(LOG, encoding="utf-8", errors="replace") as f:
            tail = f.readlines()[-40:]
    except Exception:
        return ""
    for line in reversed(tail):
        line = line.strip()
        if line.startswith("[") or line.startswith("captions"):
            return line[:96]
    return (tail[-1].strip()[:96] if tail else "")


def bar(done, want, width=32):
    n = int(width * done / want) if want else 0
    return "[" + "#" * n + "·" * (width - n) + "]"


def line(s):
    pct = (100.0 * s["done"] / s["want"]) if s["want"] else 0
    return ("%s %4d/%-4d %5.1f%%   picked %4d (%d captioned, %d without)   "
            "nothing %4d   transcripts on disk %d"
            % (bar(s["done"], s["want"]), s["done"], s["want"], pct,
               s["picked"], s["captioned"], s["bare"], s["missed"], s["vtt"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", nargs="?", type=int, const=30, default=0,
                    metavar="SECONDS", help="keep watching, default every 30s")
    ap.add_argument("--misses", action="store_true",
                    help="also name the books nothing was found for")
    a = ap.parse_args()

    s = snapshot()
    print(line(s))
    if a.misses:
        want = {w.get("file") for w in load(WANTED, [])}
        miss = [r.get("file") for r in load(RESULTS, [])
                if r.get("file") in want and not r.get("pick")]
        print("\nnothing found for %d:" % len(miss))
        for f in miss:
            print("   " + os.path.basename(f))
    if not a.watch:
        return

    t0, d0 = time.time(), s["done"]
    while True:
        time.sleep(a.watch)
        s = time.time(), snapshot()
        now, s = s
        rate = (s["done"] - d0) / max((now - t0) / 60.0, 1e-9)      # books a minute
        left = s["want"] - s["done"]
        eta = ""
        if rate > 0.01 and left:
            mins = left / rate
            eta = "   ~%dh %02dm left at %.1f/min" % (mins // 60, mins % 60, rate)
        elif left == 0:
            eta = "   done"
        print(line(s) + eta)
        if last_line():
            print("      " + last_line())
        if left == 0:
            return


if __name__ == "__main__":
    main()
