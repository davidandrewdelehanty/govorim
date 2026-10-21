#!/usr/bin/env python3
"""The FSI Russian FAST Course's recordings, cut to its lines.

Every Russian line of the course (tools/courses/fast_src.py) is looked for on
the course's tapes, in the word-level transcripts that
tools/pd_courses/transcribe_tapes.sh wrote (faster-whisper, one JSON per
tape). A line is found when a run of transcribed words reads like it; the
tape announces each dialogue («диалог номер три»), which is where its lines
are looked for first, and each line is taken from the tape's first, unpaused
reading of the dialogue. The result is tools/courses/fast_clips.json — one
entry per line that was found, with the tape and the seconds to cut — which
tools/courses/fast_course.py reads when the course is built.

    # 1. where every line is on the tapes (no audio needed, a few seconds):
    python3 tools/pd_courses/fast_build.py

    # 2. cut the clips (needs ffmpeg and the tapes) into _to_delete/pd/fsi-fast/clips/:
    python3 tools/pd_courses/fast_build.py --cut

    # 3. host them: rclone copy _to_delete/pd/fsi-fast/clips r2:govorim-audio/fast
    #    then build the courses as usual (python3 tools/courses/build_courses.py).

The tapes and transcripts are expected in _to_delete/pd/fsi-fast/audio and
_to_delete/pd/fsi-fast/words (fetch.sh, transcribe_tapes.sh); --audio and
--words name other folders."""
import argparse, difflib, io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "courses"))
import fast_src

OUT = os.path.join(ROOT, "tools", "courses", "fast_clips.json")
PAD_BEFORE, PAD_AFTER = 0.22, 0.38
TRIM = ("silenceremove=start_periods=1:start_threshold=-38dB:start_silence=0.15,"
        "areverse,silenceremove=start_periods=1:start_threshold=-38dB:start_silence=0.3,areverse,afade=t=in:d=0.03")

# Where each lesson is on the tapes: (tape number, from second, to second).
# Found by reading the transcripts for the announcements («lesson 7 shopping»).
WINDOWS = {
    2: [(2, 0, 552)], 3: [(2, 552, 1101)], 4: [(2, 1101, 99999)],
    5: [(3, 0, 1044)], 6: [(3, 1044, 99999)], 7: [(4, 0, 99999)],
    8: [(5, 0, 1500)], 9: [(5, 1500, 99999), (6, 0, 708)],
    10: [(6, 708, 99999), (7, 0, 552)], 11: [(7, 552, 99999), (8, 0, 99999)],
}
NUMS = {"один": 1, "одна": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8,
        "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12}


def norm(s):
    s = s.lower().replace("ё", "е")
    s = re.sub(r"\([^)]*\)", " ", s)          # «612 (шестьсот двенадцать)»: the digits are what is heard
    s = re.sub(r"[^a-zа-я0-9\s]", " ", s)
    return s.split()


UNITS = {"ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6,
         "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
         "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18,
         "девятнадцать": 19, "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
         "семьдесят": 70, "восемьдесят": 80, "девяносто": 90, "сто": 100, "двести": 200, "триста": 300,
         "четыреста": 400, "пятьсот": 500, "шестьсот": 600, "семьсот": 700, "восемьсот": 800, "девятьсот": 900}
THOUSANDS = {"тысяча": 1000, "тысячи": 1000, "тысяч": 1000}


def digits(toks):
    """The same tokens with each run of numeral words as its figure, the way
    the transcript writes numbers: «двадцать один» → «21»."""
    out, run, i = [], [], 0
    while i <= len(toks):
        w = toks[i] if i < len(toks) else None
        if w is not None and (w in UNITS or (w in THOUSANDS and run)):
            run.append(w); i += 1
            continue
        if run:
            total, cur = 0, 0
            for r in run:
                if r in THOUSANDS:
                    total += (cur or 1) * 1000; cur = 0
                else:
                    cur += UNITS[r]
            out.append(str(total + cur))
            run = []
        if w is not None:
            out.append(w)
        i += 1
    return out


def timeline(words_dir, lesson):
    """The lesson's stretch of tape as one list of words."""
    out = []
    for t, a, b in WINDOWS[lesson]:
        f = os.path.join(words_dir, "FSI Russian FAST - Tape %d.small.words.json" % t)
        if not os.path.exists(f):
            raise SystemExit("missing transcript: " + f)
        for w in json.load(io.open(f, encoding="utf-8"))["words"]:
            if a <= w["start"] < b:
                toks = norm(w["text"])
                out.append({"tape": t, "start": w["start"], "end": w["end"], "w": toks[0] if toks else ""})
    return out


def find(tl, toks, pos, reach):
    """The run of words in tl[pos:pos+reach] most like toks (in words, or with
    its numbers as figures): (score, i, j)."""
    if not toks:
        return 0, pos, pos
    forms = [toks]
    d = digits(toks)
    if d != toks:
        forms.append(d)
    best = (0, pos, pos)
    for form in forms:
        n = len(form)
        target = " ".join(form)
        for i in range(pos, min(len(tl), pos + reach)):
            for ln in range(max(1, n - 2), n + 3):
                j = i + ln
                if j > len(tl):
                    break
                cand = " ".join(x["w"] for x in tl[i:j])
                r = difflib.SequenceMatcher(None, target, cand).ratio()
                if r > best[0]:
                    best = (r, i, j)
            if best[0] > 0.97:
                break
    return best


def anchors(tl):
    """Where the tape announces each dialogue: {(kind, n, v): [indexes]}."""
    out = {}
    for k, x in enumerate(tl):
        if x["w"] not in ("диалог", "диалога", "дайлаг", "диалок"):
            continue
        n = after = None
        for q in range(k + 1, min(k + 4, len(tl))):
            w = tl[q]["w"]
            if w.isdigit() or w in NUMS:
                n = int(w) if w.isdigit() else NUMS[w]
                after = q + 1              # the lines start after «номер три»
                break
        if n is None:
            continue
        prev = [tl[q]["w"] for q in range(max(0, k - 3), k)]
        if any(p.startswith("вариант") or p == "верендов" for p in prev):
            v = None
            for q in range(max(0, k - 2), k):
                w = tl[q]["w"]
                vv = int(w) if w.isdigit() else NUMS.get(w)
                if vv and 1 <= vv <= 3:
                    v = vv
            key = ("variant", n, v)
        else:
            key = ("dialog", n, None)
        out.setdefault(key, []).append(after)
    return out


def accept(toks, score):
    if len(toks) == 1:
        return score >= 0.9
    if len(toks) == 2:
        return score >= 0.8
    return score >= 0.7


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=os.path.join(ROOT, "_to_delete", "pd", "fsi-fast", "audio"))
    ap.add_argument("--words", default=os.path.join(ROOT, "_to_delete", "pd", "fsi-fast", "words"))
    ap.add_argument("--clips", default=os.path.join(ROOT, "_to_delete", "pd", "fsi-fast", "clips"))
    ap.add_argument("--cut", action="store_true", help="cut the clips with ffmpeg")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)

    clips = {}
    report = []

    def group(tl, pos, items, reach, far, anchor=None):
        """Align a run of lines that follow one another on the tape: a list of
        (clip id, text). Found from `anchor`, or from where its first two lines
        are heard one after the other (within `far` words of pos); then each
        next line within `reach` words. Returns (found, pos after the run)."""
        items = [(cid, norm(t), t) for cid, t in items if norm(t)]
        if not items:
            return 0, pos
        start = anchor
        if start is None:
            # one of the first lines, with the next close behind it (the
            # transcript may have missed the very first)
            for lead in range(min(4, len(items))):
                p = pos
                while p < len(tl) and p < pos + far:
                    sc, i, j = find(tl, items[lead][1], p, pos + far - p)
                    if not accept(items[lead][1], sc):
                        break
                    if lead + 1 >= len(items):
                        start = i; break
                    sc2, i2, j2 = find(tl, items[lead + 1][1], j, reach)
                    if accept(items[lead + 1][1], sc2):
                        start = i; break
                    p = i + 1
                if start is not None:
                    break
            if start is None:
                for cid, toks, text in items:
                    report.append("  not found: %s" % text)
                return 0, pos
        p = start
        found = 0
        for cid, toks, text in items:
            sc, i, j = find(tl, toks, p, reach)
            if accept(toks, sc):
                clips[cid] = {"tape": tl[i]["tape"], "start": round(max(0, tl[i]["start"] - PAD_BEFORE), 2),
                              "end": round(tl[j - 1]["end"] + PAD_AFTER, 2),
                              "heard": " ".join(x["w"] for x in tl[i:j]), "score": round(sc, 2)}
                p = j
                found += 1
            else:
                report.append("  not found (%.2f): %s  ~  %s" % (sc, text, " ".join(x["w"] for x in tl[i:j])))
        return found, p

    for les in fast_src.LESSONS:
        n = les["n"]
        tl = timeline(a.words, n)
        anc = anchors(tl)
        pos = 0
        found = total = 0
        # the sentence sets of a lesson (geography; greetings) come first on the tape
        for si, st in enumerate(les.get("sets") or []):
            items = [("l%02d-s%d-%02d" % (n, si + 1, li + 1), line.split("|")[1]) for li, line in enumerate(st["lines"])]
            f, pos = group(tl, pos, items, 25, 700)
            found += f; total += len(items)
        for d in les.get("dialogs") or []:
            key = (d["kind"], d["n"], d.get("v"))
            cands = list(anc.get(key) or [])
            if d["kind"] == "variant":
                for k2, v2 in anc.items():
                    if k2[0] == "variant" and k2[1] == d["n"] and k2 != key:
                        cands += v2
            after = sorted(k for k in cands if k >= pos)
            at = after[0] if after else None
            did = "l%02d-%s%d%s" % (n, "d" if d["kind"] == "dialog" else "v", d["n"], ("-%d" % d["v"]) if d.get("v") else "")
            items = []
            for ti, turn in enumerate(d["turns"]):
                who, ru, en = turn.split("|", 2)
                if who == "-" and not en:
                    continue                      # a stage direction, not spoken
                items.append(("%s-%02d" % (did, ti + 1), ru))
            f, pos = group(tl, pos, items, 60, 1500, anchor=at)
            found += f; total += len(items)
        # the useful words and expressions, read once each, in the book's order
        items = [("l%02d-w%02d" % (n, wi + 1), ru) for wi, (ru, en) in enumerate(les.get("words") or [])]
        f, pos = group(tl, pos, items, 30, 2000)
        found += f; total += len(items)
        items = [("l%02d-n%02d" % (n, wi + 1), ru) for wi, (ru, en) in enumerate(les.get("numbers") or [])]
        f, pos = group(tl, pos, items, 20, 600)
        found += f; total += len(items)
        print("Lesson %2d %-20s %3d of %3d lines found on the tapes" % (n, les["ru"], found, total))
    if a.verbose:
        for r in report:
            print(r)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(clips, ensure_ascii=False, indent=0, sort_keys=True))
    print("%d clips -> %s" % (len(clips), OUT))

    if a.cut:
        os.makedirs(a.clips, exist_ok=True)
        done = 0
        for cid, c in sorted(clips.items()):
            out = os.path.join(a.clips, cid + ".mp3")
            if os.path.exists(out) and os.path.getsize(out) > 1000:
                continue
            src = os.path.join(a.audio, "FSI Russian FAST - Tape %d.mp3" % c["tape"])
            # The transcript's word times run a little early, so the span is
            # cut with room on both sides and the silence trimmed back to a
            # breath: 0.15 s before the first word, 0.3 s after the last.
            cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(c["start"]), "-to", str(c["end"]), "-i", src,
                   "-ac", "1", "-ar", "22050", "-b:a", "48k", "-af", TRIM, out]
            subprocess.run(cmd, check=True)
            done += 1
        print("%d clips cut into %s (%d already there)" % (done, a.clips, len(clips) - done))


if __name__ == "__main__":
    main(sys.argv[1:])
