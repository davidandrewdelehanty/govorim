#!/usr/bin/env python3
"""Re-key a single-page book's English, jump points and video to the parts the
reader actually shows.

The reader cuts a single-section FB2 into chapters at its in-text numerals
("I", "II", …). The parallel English (books/<slug>-en/01.json), the jump
points (books/audio-sync/<slug>/00.json) and the one video entry were all
made for the book as ONE page, keyed by paragraph index across the whole
text — so on the site they reached part I only. This script:

  * cuts the FB2 with tools/reader_chapters.py (validated against the live
    reader for every book it is run on),
  * writes books/<slug>-en/NN.json per part, local paragraph keys,
  * writes books/audio-sync/<slug>/NN.json per part (NN = chapter index),
  * sets videos[k] = {youtube, heading, start, end} per part, the start
    being the jump point of the part's first paragraph (exact) or, when
    that paragraph has none, the first jump point inside the part with a
    note saying so, so it can be refined against captions.

    python3 tools/split_parts.py asya duel …        # report only
    python3 tools/split_parts.py --write asya …     # write files + manifest

Originals are kept beside the new files as *.bak-single (gitignored).
"""
import argparse, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reader_chapters as rc

MANIFEST = "private/books/index.json"


def load_json(p):
    return json.load(open(p, encoding="utf-8"))


def dump_json(p, obj, indent=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def backup(p):
    if os.path.exists(p):
        b = p + ".bak-single"
        if not os.path.exists(b):
            shutil.copyfile(p, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    manifest = load_json(MANIFEST)
    bymap = {b.get("slug"): b for b in manifest}
    changed = False
    for slug in a.slugs:
        b = bymap.get(slug)
        if not b:
            print("!! no manifest entry:", slug)
            continue
        chs, how = rc.reader_chapters("public/books/" + b["filename"], keep_lead=True)
        print("== %s  %d parts (%s)" % (slug, len(chs), how))
        if how != "markers":
            print("   not a marker-split book — skipped")
            continue
        offsets = [c["offset"] for c in chs]
        counts = [len(c["paras"]) for c in chs]

        # ---- English ------------------------------------------------------
        en = b.get("parallelEn")
        en_whole = None
        if en:
            d = "public/books/" + en
            files = sorted(f for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []
            if files == ["01.json"]:
                en_whole = load_json(os.path.join(d, "01.json"))
            elif files:
                print("   EN: %d files already — leaving alone" % len(files))
        en_parts = []
        if en_whole is not None:
            extra = {k: v for k, v in en_whole.items() if not k.isdigit()}
            got = 0
            moved = 0
            for k, (g, n) in enumerate(zip(offsets, counts)):
                part = dict(extra)
                for j in range(n):
                    v = en_whole.get(str(g + j))
                    if v is not None:
                        part[str(j)] = v
                        got += 1
                # The aligner often hung a part's first English paragraph on
                # the numeral line above it ("II" -> "I was in the habit of
                # wandering…") and left the real first paragraph empty. The
                # numeral is a heading now, so the line moves down to where
                # the Russian it translates begins.
                if "0" not in part and g > 0 and str(g - 1) in en_whole and len(en_whole[str(g - 1)]) > 20:
                    part["0"] = en_whole[str(g - 1)]
                    moved += 1
                en_parts.append(part)
            if moved:
                print("   EN: %d opening lines moved off their numeral onto the first paragraph" % moved)
            print("   EN: %d of %d numbered lines re-keyed into %d files" % (got, sum(1 for k in en_whole if k.isdigit()), len(en_parts)))

        # ---- jump points --------------------------------------------------
        sync_whole = None
        sd = "public/books/audio-sync/" + slug
        sfiles = sorted(f for f in os.listdir(sd) if f.endswith(".json")) if os.path.isdir(sd) else []
        if sfiles == ["00.json"]:
            sync_whole = {int(k): v for k, v in load_json(os.path.join(sd, "00.json")).items()}
        elif sfiles:
            print("   sync: files %s already — leaving alone" % sfiles)
        sync_parts = []
        if sync_whole is not None:
            for g, n in zip(offsets, counts):
                sync_parts.append({str(j): sync_whole[g + j] for j in range(n) if (g + j) in sync_whole})

        # ---- video --------------------------------------------------------
        vids = b.get("videos") or {}
        v0 = vids.get("0") or {}
        vid = v0.get("youtube")
        new_videos = None
        if vid and sync_whole is not None:
            new_videos = {}
            starts = []
            for k, (g, n) in enumerate(zip(offsets, counts)):
                t = None
                note = None
                if g in sync_whole:
                    t = sync_whole[g]
                else:
                    for j in range(1, n):
                        if (g + j) in sync_whole:
                            t = sync_whole[g + j]
                            note = "start taken from paragraph %d's jump point (paragraph 0 has none) — refine against captions" % j
                            break
                if k == 0 and v0.get("start") is not None:
                    t = v0["start"]
                    note = None
                starts.append((t, note))
            for k, c in enumerate(chs):
                t, note = starts[k]
                e = {"youtube": vid, "heading": c["heading"] or ("Глава %d" % (k + 1))}
                if t is None:
                    e["note"] = "no jump point in this part — start unknown"
                else:
                    e["start"] = int(round(t))
                nxt = starts[k + 1][0] if k + 1 < len(starts) else None
                if nxt is not None and t is not None and nxt > t:
                    e["end"] = int(round(nxt))
                if note:
                    e["note"] = note
                new_videos[str(k)] = e
            flagged = [k for k, e in new_videos.items() if e.get("note")]
            print("   video: %d parts, %d flagged for refinement: %s" % (len(new_videos), len(flagged), flagged))
            for k in flagged:
                print("      %s: %s" % (k, new_videos[k].get("note")))
        elif vid:
            print("   video: no jump points — timings need captions; leaving videos alone")

        if not a.write:
            continue
        if en_parts:
            d = "public/books/" + en
            backup(os.path.join(d, "01.json"))
            for k, part in enumerate(en_parts):
                dump_json(os.path.join(d, "%02d.json" % (k + 1)), part, indent=1)
        if sync_parts:
            backup(os.path.join(sd, "00.json"))
            for k, part in enumerate(sync_parts):
                dump_json(os.path.join(sd, "%02d.json" % k), part)
        if new_videos:
            b["videos"] = new_videos
            b["timingSource"] = "one whole-book recording; part starts are the jump points of each part's opening paragraph"
            changed = True
        print("   written")
    if a.write and changed:
        backup(MANIFEST)
        dump_json(MANIFEST, manifest, indent=2)
        print("manifest written")


if __name__ == "__main__":
    main()
