# Grammatical hint labels from the Oct 25 2026 hint audit: every fill blank «___ (word)» that named only the
# dictionary form gets what to produce — «___ (книга, gen. pl.)», «___ (читать, impf., past f. sg.)».
# Payload hints.b64: gzip JSON {labels, files: {"course/file.json": [sha1 of q+answer list, [label index per exercise]]}}.
# A file whose exercises changed since the audit is skipped, never guessed at.  python3 apply_hints.py [--apply]
import json, io, re, glob, os, gzip, base64, hashlib, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
P = json.loads(gzip.decompress(base64.b64decode(open(os.path.join(HERE, "hints.b64")).read())))
L = P["labels"]; apply = "--apply" in sys.argv
def walk(o, out):
    if isinstance(o, dict):
        if isinstance(o.get("q"), str) and "answers" in o: out.append(o)
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
n = files = skipped = 0
for key, (h, seq) in P["files"].items():
    f = os.path.join(ROOT, "public", "courses", key)
    if not os.path.exists(f): print("missing", key); skipped += 1; continue
    d = json.load(io.open(f, encoding="utf-8")); out = []; walk(d, out)
    hh = hashlib.sha1("\n".join(e["q"] + "\t" + (e.get("answers") or [""])[0] for e in out).encode()).hexdigest()[:10]
    if hh != h or len(out) != len(seq): print("changed since audit, skipped:", key); skipped += 1; continue
    for e, i in zip(out, seq):
        if not i: continue
        m = re.search(r"___\s*\(([^)]*)\)", e["q"])
        e["q"] = e["q"][:m.end() - 1] + L[i] + e["q"][m.end() - 1:]; n += 1
    files += 1
    if apply: io.open(f, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
print("labelled", n, "in", files, "files; skipped", skipped, "(applied)" if apply else "(dry run)")
