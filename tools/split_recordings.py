#!/usr/bin/env python3
"""
split_recordings.py — unattended: turn one-long-file plays and stories into one
MP3 per act/chapter. Start it, go to work, read the report when you get back.

Why it is not just "run Whisper on everything": the eight remaining recordings
are 18.4 hours of audio. Transcribing all of it on a CPU takes days. But these
readings ANNOUNCE their divisions — "Действие второе", "Глава пятая" — always
right after a pause. So:

  1. ffmpeg silencedetect finds every long pause (cheap, decode-only).
  2. Only the longest N pauses become candidates, and only ~20 seconds after
     each one gets transcribed. That is minutes of audio per book, not hours.
  3. Whatever the reader announced there becomes the cut point.
  4. ffmpeg cuts, plain chapter JSONs are written, a report is left behind.

Nothing prompts, nothing blocks. Every book is independent: one failing does not
stop the rest. Transcribed windows are cached, so a re-run costs almost nothing.

Requires: ffmpeg, and `pip install faster-whisper`.

    # one shot, in the background, safe to close the terminal
    cd /mnt/c/Users/david/projects/govorim-app
    nohup python3 tools/split_recordings.py --root /mnt/c/Users/david/Downloads/audiobooks \
        --out ~/split-out --apply > ~/split-out/run.log 2>&1 &

    # later
    cat ~/split-out/REPORT.txt
"""
import argparse, json, os, re, subprocess, sys, time, traceback

# folder under --root, output slug, title, author
BOOKS = [
    ("Гоголь - Резивор - Радиоспектакль",          "revizor",        "Ревизор",        "Гоголь Н.В."),
    ("three sisters radio spectacle",              "tri-sestry",     "Три сестры",     "Чехов А.П."),
    ("Гоголь - Женитьба - радиосектакль",          "zhenitba",       "Женитьба",       "Гоголь Н.В."),
    ("гроза - островский - радиоспектакль",        "groza",          "Гроза",          "Островский А.Н."),
    ("Горе от ума - радиоспектакль",               "gore-ot-uma-radio", "Радиоспектакль «Горе от ума»", "Грибоедов А.С."),
    ("forest ostrovski",                           "les",            "Лес",            "Островский А.Н."),
    ("Бесприданница - островский - радиоспектакль","bespridannitsa", "Бесприданница",  "Островский А.Н."),
    ("Дети подземелья",                            "deti-podzemelya","Дети подземелья","Короленко В.Г."),
]

PUBLIC_BASE = "https://pub-84adcd23e17e4925a0ac7eca17ea2556.r2.dev"
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac")

ORDINALS = {
    "первое":1,"первая":1,"первый":1,"второе":2,"вторая":2,"второй":2,
    "третье":3,"третья":3,"третий":3,"четвертое":4,"четвёртое":4,"четвертая":4,"четвёртая":4,
    "пятое":5,"пятая":5,"пятый":5,"шестое":6,"шестая":6,"седьмое":7,"седьмая":7,
    "восьмое":8,"восьмая":8,"девятое":9,"девятая":9,"десятое":10,"десятая":10,
    "одиннадцатое":11,"одиннадцатая":11,"двенадцатое":12,"двенадцатая":12,
    "тринадцатая":13,"четырнадцатая":14,"пятнадцатая":15,
}
KIND = r"(действие|акт|картина|глава|часть)"
ANNOUNCE = re.compile(KIND + r"\s+([а-яё]+|\d{1,2})\b")


def log(msg):
    print("%s  %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                   "format=duration", "-of", "csv=p=0", path])
    return float(out.decode().strip())


def clock(t):
    t = max(0.0, float(t))
    return "%d:%02d:%02d" % (int(t // 3600), int(t % 3600 // 60), int(t % 60))


def find_silences(path, min_len, noise_db):
    """Every pause at least min_len long, as (end_of_silence, silence_length)."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "silencedetect=noise=%ddB:d=%.2f" % (noise_db, min_len),
         "-f", "null", "-"],
        capture_output=True)
    txt = (p.stderr or b"").decode("utf-8", "ignore")
    ends = [float(m.group(1)) for m in re.finditer(r"silence_end:\s*([0-9.]+)", txt)]
    durs = [float(m.group(1)) for m in re.finditer(r"silence_duration:\s*([0-9.]+)", txt)]
    n = min(len(ends), len(durs))
    return list(zip(ends[:n], durs[:n]))


def announcements(text):
    """Divisions announced in this snippet, as (kind, number)."""
    t = text.lower().replace("ё", "е")
    out = []
    for m in ANNOUNCE.finditer(t):
        # "конец первого действия" is an ending, not a beginning.
        before = t[max(0, m.start() - 24):m.start()]
        if "конец" in before or "окончани" in before:
            continue
        kind, val = m.group(1), m.group(2)
        num = int(val) if val.isdigit() else ORDINALS.get(val)
        if num:
            out.append((kind, num))
    return out


def transcribe_windows(model, path, candidates, window, cache_path):
    cache = {}
    if os.path.exists(cache_path):
        try:
            cache = json.load(open(cache_path, encoding="utf-8"))
        except Exception:
            cache = {}
    dirty = False
    results = {}
    for t, _ in candidates:
        key = "%.2f" % t
        if key in cache:
            results[t] = cache[key]
            continue
        segs, _ = model.transcribe(path, language="ru", beam_size=1,
                                   without_timestamps=True,
                                   clip_timestamps=[max(0.0, t - 1.0), t - 1.0 + window])
        txt = " ".join(s.text for s in segs).strip()
        cache[key] = txt
        results[t] = txt
        dirty = True
    if dirty:
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    return results


def pick_cuts(texts, candidates, total):
    """Announced divisions, forward-only and strictly increasing."""
    hits = []
    for t, _ in candidates:
        for kind, num in announcements(texts.get(t, "")):
            hits.append((t, kind, num, texts.get(t, "")[:70]))
    hits.sort(key=lambda h: h[0])
    # keep the dominant kind (a play announces действие; a story глава)
    kinds = {}
    for _, kind, _, _ in hits:
        kinds[kind] = kinds.get(kind, 0) + 1
    if not kinds:
        return []
    kind = max(kinds, key=lambda k: kinds[k])
    cuts, last_num, last_t = [], 0, -1
    for t, k, num, snip in hits:
        if k != kind or num <= last_num or t <= last_t + 30:
            continue
        cuts.append({"t": t, "label": "%s %d" % (k, num), "n": num, "snippet": snip})
        last_num, last_t = num, t
    return cuts


def process(book, args, model, report):
    folder, slug, title, author = book
    src_dir = os.path.join(args.root, folder)
    audio = None
    for f in sorted(os.listdir(src_dir)):
        if f.lower().endswith(AUDIO_EXT):
            audio = os.path.join(src_dir, f)
            break
    if not audio:
        report.append("%-22s NO AUDIO FILE FOUND in %s" % (title, folder))
        return

    out_dir = os.path.join(args.out, slug)
    os.makedirs(out_dir, exist_ok=True)
    total = duration(audio)
    log("%s — %s (%s)" % (title, os.path.basename(audio), clock(total)))

    sil = find_silences(audio, args.min_silence, args.noise)
    sil = [s for s in sil if s[0] > 20 and s[0] < total - 20]
    sil.sort(key=lambda s: -s[1])
    cands = sorted(sil[:args.candidates])
    cands = [(0.0, 0.0)] + cands                     # the opening announcement
    log("  %d pauses, taking %d candidates" % (len(sil), len(cands)))

    texts = transcribe_windows(model, audio, cands, args.window,
                               os.path.join(out_dir, "windows.json"))
    cuts = pick_cuts(texts, cands, total)
    log("  %d divisions announced" % len(cuts))

    with open(os.path.join(out_dir, "cuts.tsv"), "w", encoding="utf-8") as fh:
        fh.write("# n\tstart_seconds\tclock\tlabel\theard\n")
        for i, c in enumerate(cuts, 1):
            fh.write("%d\t%.2f\t%s\t%s\t%s\n" % (i, c["t"], clock(c["t"]), c["label"],
                                                 c["snippet"].replace("\t", " ")))
    if not cuts:
        report.append("%-22s %-9s NOTHING ANNOUNCED — needs a listen" % (title, clock(total)))
        return

    # A stretch before the first announcement is usually a cast list or an
    # announcer's intro. Keep it as its own piece rather than discarding it.
    starts = [c["t"] for c in cuts]
    labels = [c["label"] for c in cuts]
    if starts[0] > 45:
        starts.insert(0, 0.0)
        labels.insert(0, "вступление")
    pieces = []
    for i, st in enumerate(starts):
        en = starts[i + 1] if i + 1 < len(starts) else total
        pieces.append((st, en, labels[i]))

    if args.apply:
        for i, (st, en, lab) in enumerate(pieces, 1):
            dst = os.path.join(out_dir, "%02d.mp3" % i)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % st,
                            "-to", "%.2f" % en, "-i", audio,
                            "-c:a", "libmp3lame", "-q:a", "3", "-map_metadata", "-1", dst],
                           check=True)
        json_dir = os.path.join(out_dir, "json")
        os.makedirs(json_dir, exist_ok=True)
        for i in range(1, len(pieces) + 1):
            doc = {"audio_url": "%s/%s/%02d.mp3" % (PUBLIC_BASE, slug, i),
                   "narrator": "audiobook", "fragments": []}
            with open(os.path.join(json_dir, "%s-ch%02d.json" % (slug, i)), "w",
                      encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False); fh.write("\n")

    report.append("%-22s %-9s %2d pieces: %s" %
                  (title, clock(total), len(pieces), ", ".join(l for _, _, l in pieces)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="the audiobooks staging folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true", help="actually cut the MP3s")
    ap.add_argument("--model", default="small", help="faster-whisper model (small is plenty here)")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--compute-type", default=None)
    ap.add_argument("--candidates", type=int, default=80, help="longest N pauses to listen at")
    ap.add_argument("--window", type=float, default=20.0, help="seconds to transcribe per candidate")
    ap.add_argument("--min-silence", type=float, default=0.9)
    ap.add_argument("--noise", type=int, default=-34, help="silence threshold in dB")
    ap.add_argument("--only", help="slug to process alone")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    from faster_whisper import WhisperModel
    device = args.device
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    ctype = args.compute_type or ("float16" if device == "cuda" else "int8")
    log("loading %s on %s (%s)" % (args.model, device, ctype))
    model = WhisperModel(args.model, device=device, compute_type=ctype)

    report, t0 = [], time.time()
    for book in BOOKS:
        if args.only and book[1] != args.only:
            continue
        try:
            process(book, args, model, report)
        except Exception:
            log("  FAILED: %s" % book[2])
            traceback.print_exc()
            report.append("%-22s FAILED — see the log" % book[2])
    lines = ["Split report — %s" % time.strftime("%Y-%m-%d %H:%M"),
             "elapsed: %s" % clock(time.time() - t0), ""] + report + [
             "", "Each book: out/<slug>/cuts.tsv shows where it cut and what it heard there.",
             "Check any book whose piece count looks wrong, then upload out/<slug>/*.mp3",
             "to r2:govorim-audio/<slug>/ and add it with tools/add_plain_book.py."]
    open(os.path.join(args.out, "REPORT.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    log("done — %s" % os.path.join(args.out, "REPORT.txt"))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
