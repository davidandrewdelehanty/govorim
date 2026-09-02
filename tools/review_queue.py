#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_queue.py — print the timing-review rows as something a person can act on.

The CSV carries a normalised probe ("расставшись с максимом максимычем"), which
is what the matcher needs and not what a human wants in their ear. This pulls
the chapter's real opening sentence out of the FB2, capitals and punctuation
intact, and pairs it with the listen-here link.

  python3 tools/review_queue.py                     # everything still undecided
  python3 tools/review_queue.py --group B --limit 6
  python3 tools/review_queue.py --decide kazaki:17=ok  otrochestvo:17=6821  yunost:9=no
"""
import argparse, csv, io, json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REVIEW = os.path.join(HERE, "timings-REVIEW.csv")
DECISIONS = os.path.join(HERE, "timings-DECISIONS.csv")
MANIFEST = os.path.join(ROOT, "private", "books", "index.json")


def strip_ns(t):
    return t.split("}", 1)[-1]


def chapter_openings(path, n=3):
    """First few real sentences of every chapter, as printed in the book."""
    raw = open(path, "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"']([\w-]+)[\"']", raw)
    text = raw.decode((m.group(1).decode() if m else "utf-8"), errors="replace")
    root = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text, count=1).strip())
    bodies = [el for el in root.iter() if strip_ns(el.tag) == "body"
              and el.get("name") not in ("notes", "comments")]
    out = []

    def walk(sec):
        subs = [c for c in sec if strip_ns(c.tag) == "section"]
        if subs:
            for c in subs:
                walk(c)
            return
        title_el = next((c for c in sec if strip_ns(c.tag) == "title"), None)
        buf = ""
        for el in sec:
            if el is title_el:
                continue
            buf += " " + " ".join(x.strip() for x in el.itertext() if x.strip())
            if len(buf) > 260:
                break
        buf = re.sub(r"\s+", " ", buf).strip()
        parts = re.split(r"(?<=[.!?…])\s+", buf)
        out.append(" ".join(parts[:n])[:230])

    for b in bodies:
        for s in [c for c in b if strip_ns(c.tag) == "section"]:
            walk(s)
    return out


def load_decisions():
    d = {}
    if os.path.exists(DECISIONS):
        for r in csv.DictReader(io.open(DECISIONS, encoding="utf-8-sig")):
            d[(r["slug"], r["chapter"])] = r
    return d


def save_decision(slug, ch, verdict, secs=""):
    d = load_decisions()
    d[(slug, ch)] = {"slug": slug, "chapter": ch, "verdict": verdict, "new_start_sec": secs}
    with io.open(DECISIONS, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["slug", "chapter", "verdict", "new_start_sec"])
        w.writeheader()
        for k in sorted(d, key=lambda k: (k[0], int(k[1]))):
            w.writerow(d[k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", help="A, B or C")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--decide", nargs="*", default=[],
                    help="slug:chapter=ok | =no | =<seconds>")
    args = ap.parse_args()

    for spec in args.decide:
        key, _, val = spec.partition("=")
        slug, _, ch = key.partition(":")
        val = val.strip().lower()
        if val in ("ok", "yes", "accept"):
            save_decision(slug, ch, "accept")
        elif val in ("no", "reject", "keep"):
            save_decision(slug, ch, "reject")
        else:
            save_decision(slug, ch, "override", str(int(float(val))))
        print("recorded %s ch%s -> %s" % (slug, ch, val))
    if args.decide:
        return 0

    manifest = json.load(io.open(MANIFEST, encoding="utf-8"))
    fb2_of = {e.get("slug"): e.get("filename") for e in manifest}
    decided = load_decisions()
    rows = list(csv.DictReader(io.open(REVIEW, encoding="utf-8-sig")))
    cache, shown = {}, 0
    for r in rows:
        if args.group and not r["priority"].startswith(args.group):
            continue
        if (r["slug"], r["chapter"]) in decided:
            continue
        slug = r["slug"]
        if slug not in cache:
            cache[slug] = chapter_openings(os.path.join(ROOT, "public", "books", fb2_of[slug]))
        ops = cache[slug]
        ci = int(r["chapter"])
        print("### %s  ch%s — %s   [%s]" % (slug, r["chapter"], r["heading"], r["priority"][2:]))
        print("    now %s -> %s  (%ss, score %s)" % (r["current_start"], r["proposed_start"],
                                                     r["delta_sec"], r["score"]))
        print("    listen: %s" % r["check_url"])
        print("    words : %s" % (ops[ci] if ci < len(ops) else "(?)"))
        print()
        shown += 1
        if args.limit and shown >= args.limit:
            break
    print("-- %d shown, %d already decided, %d rows total" % (shown, len(decided), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
