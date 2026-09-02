#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""play_acts.py — where each act's first spoken line falls in a recording.

A play cannot be timed the way prose is. An act opens with ДЕЙСТВУЮЩИЕ ЛИЦА,
a cast list and a stage direction, none of which a performance says aloud, and
the act itself begins before anybody speaks — with music, applause, a curtain.
So this does NOT propose a start. It finds the first line that IS spoken and
hands a person the moment before it, which is the only place the real boundary
can be judged from.

    python3 tools/play_acts.py --slug groza-spektakl
"""
import argparse, importlib.util, io, json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_s = importlib.util.spec_from_file_location("av", os.path.join(HERE, "align_video.py"))
av = importlib.util.module_from_spec(_s); _s.loader.exec_module(av)

# "КАБАНОВА. Если хочешь мать послушать..." — a name, then the line.
SPEECH = re.compile(r"^([А-ЯЁ][А-ЯЁа-яёё\- ]{0,38})(\s*\([^)]{1,120}\))?\s*[.:]\s+(.{12,})$")
CAST = re.compile(r"^(действующие\s+лица|лица|действие|картина)", re.I)


def strip_ns(t): return t.split("}", 1)[-1]


def speaker_names(paras):
    """Names actually used as speaker labels, learned from the play itself.

    A single paragraph beginning "Улица. Ворота дома Кабановых..." is a scene
    heading, not Улица speaking. The reader's own play formatter separates the
    two by counting: a real character is labelled many times over, a scene
    heading once. Same rule here.
    """
    from collections import Counter
    c = Counter()
    for t in paras:
        mm = SPEECH.match(t)
        if mm:
            c[mm.group(1).strip().lower()] += 1
    return {n for n, k in c.items() if k >= 3}


def act_first_lines(path):
    raw = open(path, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)[\"']", raw)
    text = raw.decode((m.group(1).decode() if m else "utf-8"), errors="replace")
    root = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip())
    allp = [re.sub(r"\s+", " ", " ".join(x.strip() for x in el.itertext() if x.strip())).strip()
            for el in root.iter() if strip_ns(el.tag) == "p"]
    names = speaker_names(allp)
    out = []

    def walk(sec):
        subs = [c for c in sec if strip_ns(c.tag) == "section"]
        if subs:
            for c in subs: walk(c)
            return
        te = next((c for c in sec if strip_ns(c.tag) == "title"), None)
        line = None
        for el in sec:
            if el is te or strip_ns(el.tag) != "p":
                continue
            t = re.sub(r"\s+", " ", " ".join(x.strip() for x in el.itertext() if x.strip())).strip()
            if not t or CAST.match(t):
                continue
            mm = SPEECH.match(t)
            if mm and len(mm.group(3).split()) >= 4 and mm.group(1).strip().lower() in names:
                line = (mm.group(1).strip(), mm.group(3))
                break
        out.append(line)

    for b in [el for el in root.iter() if strip_ns(el.tag) == "body"
              and el.get("name") not in ("notes", "comments")]:
        for sec in [c for c in b if strip_ns(c.tag) == "section"]:
            walk(sec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--window", type=float, default=900.0)
    ap.add_argument("--lead", type=int, default=25, help="seconds before the line to start listening")
    ap.add_argument("--silence", type=float, default=22.0,
                    help="a caption gap this long is a candidate act boundary")
    args = ap.parse_args()

    man = json.load(io.open(os.path.join(ROOT, "private", "books", "index.json"), encoding="utf-8"))
    e = next(x for x in man if x.get("slug") == args.slug)
    lines = act_first_lines(os.path.join(ROOT, "public", "books", e["filename"]))
    videos = e.get("videos") or {}
    cache = {}
    print("== %s" % e.get("title"))
    for k in sorted(videos, key=int):
        seg = videos[k]
        if not isinstance(seg, dict) or not seg.get("youtube"):
            continue
        vid = seg["youtube"]
        if vid not in cache:
            p = os.path.join(HERE, "captions", vid + ".ru.vtt")
            if not os.path.exists(p):
                print("  ch%s: no captions" % k); continue
            cache[vid] = av.parse_vtt(p)
        words = cache[vid]
        gaps = [(words[j]["b"] - words[j - 1]["b"], words[j - 1]["b"], words[j]["b"])
                for j in range(1, len(words)) if words[j]["b"] - words[j - 1]["b"] >= args.silence]
        ci = int(k)
        line = lines[ci] if ci < len(lines) else None
        cur = seg.get("start")
        tag = " [manual]" if seg.get("manual") else ""
        if not line:
            print("  ch%-3s %-22s start=%-9s no spoken line found%s"
                  % (k, seg.get("heading", "")[:22], av.clock(cur or 0), tag)); continue
        probe = av.cbt.words_of(line[1])[:16]
        import bisect
        times = [w["b"] for w in words]
        anchor = float(cur or 0)
        lo = bisect.bisect_left(times, anchor - args.window)
        hi = bisect.bisect_right(times, anchor + args.window)
        i, sc = av.cbt.best_match(words, probe, lo, max(lo, hi))
        t = words[i]["b"] if i >= 0 else None
        print("  ch%-3s %-22s start=%-9s first line at %-9s (score %.2f)%s"
              % (k, seg.get("heading", "")[:22], av.clock(cur or 0),
                 av.clock(t) if t else "?", sc, tag))
        print("        %s: %s" % (line[0], line[1][:88]))
        if t:
            print("        listen: https://youtu.be/%s?t=%d" % (vid, max(0, int(t) - args.lead)))
        # An act begins before anyone speaks — with music, a curtain, applause.
        # The captions go quiet there, so the longest silence before the first
        # spoken line is the best mechanical estimate of the boundary. On Гроза
        # every act boundary from the video's comments sat on one of these, the
        # 72-second gap at 1:49:17 included.
        if t:
            cands = [g for g in gaps if g[2] <= t + 5 and g[2] > t - 300]
            if cands:
                g = max(cands, key=lambda g: g[0])
                print("        silence %s..%s (%.0fs) -> act likely starts %s"
                      % (av.clock(g[1]), av.clock(g[2]), g[0], av.clock(g[2])))
                print("        listen: https://youtu.be/%s?t=%d" % (vid, max(0, int(g[1]) - 5)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
