# -*- coding: utf-8 -*-
"""An explanation page has no exercises: the ones a lesson carried move to the practice page after it.
    python3 tools/courses/split_lessons.py [--dry]        (from the repo root; then finalize_outline.py)
A lesson with a practice set already gets its exercises as one more set after the last (a handful, as the end of the last set);
a lesson without one gets  <lesson>-practice.  Streams (endless practice) and exams are left alone.  Idempotent."""
import io, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "src", "courses-outline.js")
PR = re.compile(r"-practice(-\d+)?$")
TAIL = re.compile(r"^Practice\s*\d*:\s*")
FEW = 6
dry = "--dry" in sys.argv
def rd(p): return json.load(io.open(p, encoding="utf-8"))
def wr(p, j): io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
t = io.open(OUT, encoding="utf-8").read()
cur = json.loads(t[t.index("export default ") + 15:].rstrip().rstrip(";"))
moved = 0
for m in cur:
    cdir = os.path.join(ROOT, "public", "courses", m["id"])
    out = []
    secs = m["sections"]
    for s in secs:
        out.append(s)
        if s.get("exam") or s.get("stream") or PR.search(s["id"]): continue
        p = os.path.join(cdir, s["id"] + ".json")
        if not os.path.exists(p): continue
        j = rd(p); exs = j.get("exercises") or []
        if not exs: continue
        mine = [x for x in secs if x["id"] == s["id"] + "-practice" or re.fullmatch(re.escape(s["id"]) + r"-practice-\d+", x["id"])]
        note = {"t": "note", "text": "Exercises: sentences from Tatoeba (tatoeba.org, CC BY 2.0 FR) and from the library's public-domain books."}
        if mine and len(exs) <= FEW:
            last = mine[-1]; lp = os.path.join(cdir, last["id"] + ".json"); lj = rd(lp)
            have = {e.get("id") for e in lj["exercises"]}
            for k, e in enumerate(exs):
                e = dict(e); nid = "L%d" % (k + 1)
                while nid in have: nid += "x"
                e["id"] = nid; have.add(nid); lj["exercises"].append(e)
            last["n"] = len(lj["exercises"])
            if not dry: wr(lp, lj)
        elif mine:
            k = len(mine) + 1
            if len(mine) == 1 and not re.match(r"^Practice\s*\d", mine[0]["title"]):
                mine[0]["title"] = re.sub(r"^Practice:", "Practice 1:", mine[0]["title"])
                mp = os.path.join(cdir, mine[0]["id"] + ".json"); mj = rd(mp); mj["title"] = mine[0]["title"]
                if not dry: wr(mp, mj)
            nid = s["id"] + "-practice-%d" % k
            title = "Practice %d: %s" % (k, TAIL.sub("", mine[0]["title"]))
            new = {"id": nid, "title": title, "blocks": [note], "exercises": exs}
            if not dry: wr(os.path.join(cdir, nid + ".json"), new)
            # the new set goes after the last one of this lesson
            out.append(("AFTER", mine[-1]["id"], {"id": nid, "title": title, "n": len(exs)}))
        else:
            nid = s["id"] + "-practice"; title = "Practice: " + s["title"]
            new = {"id": nid, "title": title, "blocks": [note], "exercises": exs}
            if not dry: wr(os.path.join(cdir, nid + ".json"), new)
            out.append({"id": nid, "title": title, "n": len(exs)})
        s["n"] = 0
        j["exercises"] = []
        if not dry: wr(p, j)
        moved += 1
    # resolve the "after the last set" placements
    final = [x for x in out if not isinstance(x, tuple)]
    for x in out:
        if isinstance(x, tuple):
            _, after, sec = x
            i = next(k for k, y in enumerate(final) if y["id"] == after)
            final.insert(i + 1, sec)
    m["sections"] = final
if not dry:
    io.open(OUT, "w", encoding="utf-8").write("// Written by tools/courses/build_courses.py — the courses, their sections and\n"
        "// how many exercises each has. The lessons themselves are in public/courses/.\n"
        "export default " + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")
print("lessons whose exercises moved:", moved)
