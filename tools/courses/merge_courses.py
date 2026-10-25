# -*- coding: utf-8 -*-
"""Fold courses into one long course: files, outline entries, covers.   python3 tools/courses/merge_courses.py [grammar|verbs]
(run from the repo root, then tools/courses/finalize_outline.py).  Done on the finished files — do NOT run build_courses.py
afterwards, it would write the old courses again.  Idempotent: a course already folded in is skipped."""
import io, json, os, shutil, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "src", "courses-outline.js")
PICS = os.path.join(ROOT, "src", "course-pictures.json")
MERGES = {
    "grammar": {"into": "inter2", "from": ["adv3"], "title": "Grammar in Depth", "short": "Grammar in depth", "level": "Intermediate"},
    "cases": {"into": "cases", "from": ["pronouns"], "title": "Nouns, Adjectives, and Pronouns in Cases", "short": "Cases", "level": "Beginner"},
    "time": {"into": "inter2", "from": ["time"], "title": "Grammar in Depth", "short": "Grammar in depth", "level": "Intermediate"},
    "verbs": {"into": "verbs", "from": ["aspect", "forms"], "title": "Everything about Russian Verbs", "short": "All about verbs", "level": "Beginner"},
}
def load():
    t = io.open(OUT, encoding="utf-8").read()
    return json.loads(t[t.index("export default ") + 15:].rstrip().rstrip(";"))
def save(cur):
    io.open(OUT, "w", encoding="utf-8").write("// Written by tools/courses/build_courses.py — the courses, their sections and\n"
        "// how many exercises each has. The lessons themselves are in public/courses/.\n"
        "export default " + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")
def main(which):
    cfg = MERGES[which]
    cur = load(); by = {m["id"]: m for m in cur}
    dest = by[cfg["into"]]
    dest["title"], dest["short"], dest["level"] = cfg["title"], cfg["short"], cfg["level"]
    ddir = os.path.join(ROOT, "public", "courses", cfg["into"])
    dropped = os.path.join(ROOT, "public", "courses", "_dropped"); os.makedirs(dropped, exist_ok=True)
    pics = json.load(io.open(PICS, encoding="utf-8"))
    secs = [s for s in dest["sections"] if not s.get("exam")]
    lic = set(x.strip() for x in dest.get("license", "").split("·"))
    cred = dest.get("credit", "")
    for fid in cfg["from"]:
        src = by.get(fid)
        if not src: continue
        sdir = os.path.join(ROOT, "public", "courses", fid)
        for s in src["sections"]:
            if s.get("exam"): continue
            a = os.path.join(sdir, s["id"] + ".json")
            if os.path.exists(a):
                j = json.load(io.open(a, encoding="utf-8")); j["course"] = cfg["into"] if "course" in j else None
                if j["course"] is None: del j["course"]
                io.open(os.path.join(ddir, s["id"] + ".json"), "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
                shutil.move(a, os.path.join(dropped, "%s-%s.json" % (fid, s["id"])))
            secs.append(s)
        e = os.path.join(sdir, "exam.json")
        if os.path.exists(e): shutil.move(e, os.path.join(dropped, fid + "-exam.json"))
        lic |= set(x.strip() for x in src.get("license", "").split("·"))
        for part in src.get("credit", "").split("; "):
            if part and part not in cred: cred += "; " + part
        cur = [m for m in cur if m["id"] != fid]
        pics.pop(fid, None)
    dest["sections"] = secs
    dest["license"] = " · ".join(sorted(x for x in lic if x))
    dest["credit"] = cred
    by_ids = {m["id"] for m in cur}
    save(cur)
    io.open(PICS, "w", encoding="utf-8").write(json.dumps(pics, ensure_ascii=False, indent=1))
    print("merged", cfg["from"], "into", cfg["into"], "—", len(secs), "sections")
if __name__ == "__main__":
    main(sys.argv[1])
