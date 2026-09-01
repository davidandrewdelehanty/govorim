#!/usr/bin/env python3
"""Library-wide quality scan.

For every catalogue entry: parse the FB2 with the same chapter logic the
reader uses (scan_alignment.chapters), capture the opening and closing
paragraphs, flag structural problems, and do the same for the English
pairing folder. Output: tools/qc-report.json for human review.
"""
import io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import chapters

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "private", "books", "index.json")
BOOKS = os.path.join(ROOT, "public", "books")

PUB_SIGNS = re.compile(
    r"ISBN|©|\(c\)\s|Издательство|ИЗДАТЕЛЬСТВО|Все права защищены|OCR|"
    r"Аннотация|Государственное издательство|Печатается по|"
    r"Project Gutenberg|Transcriber|Produced by|All rights reserved|"
    r"PRINTED IN|Publishers?,? (New York|London)|Copyright", re.I if False else 0)
PUB_SIGNS_I = re.compile(r"ISBN|Все права защищены|All rights reserved|Copyright|Printed in", re.I)
def MOJI_hit(t):
    return ("\ufffd" in t) or ("Ð" in t and "Ñ" in t)
TAGGY = re.compile(r"<[a-zA-Z/][^>]*>|&[a-z]+;|&#\d+;")

def clip(t, n=240):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[:n] + "…"

def scan_ru(path, title):
    chs = chapters(path, title)
    if chs is None:
        return {"error": "unparseable"}
    r = {"n_chapters": len(chs),
         "para_counts": [len(c) for c in chs],
         "flags": []}
    if not chs:
        r["flags"].append("no chapters"); return r
    tiny = [i for i, c in enumerate(chs) if len(c) < 2]
    if tiny: r["flags"].append("tiny chapters (<2 paras): " + str(tiny[:12]))
    allp = [p for c in chs for p in c]
    bad_markup = [clip(p, 120) for p in allp if TAGGY.search(p)][:3]
    if bad_markup: r["flags"].append("raw markup/entities: " + " | ".join(bad_markup))
    moji = [clip(p, 80) for p in allp if MOJI_hit(p)][:2]
    if moji: r["flags"].append("mojibake: " + " | ".join(moji))
    head = chs[0][:4]
    for p in head:
        if PUB_SIGNS.search(p) or PUB_SIGNS_I.search(p):
            r["flags"].append("publisher-ish opening: " + clip(p, 160)); break
    r["first"] = [clip(p) for p in chs[0][:3]]
    r["last"] = [clip(p) for p in chs[-1][-3:]]
    # last paragraph ending mid-sentence?
    lastp = re.sub(r"\s+", " ", chs[-1][-1]).strip()
    if lastp and lastp[-1] not in ".!?…»\"')]*":
        r["flags"].append("last paragraph ends without terminal punctuation")
    return r

def scan_en(dirname, n_ch, para_counts, flow):
    d = os.path.join(BOOKS, dirname)
    if not os.path.isdir(d):
        return {"error": "folder missing"}
    files = sorted(f for f in os.listdir(d) if re.match(r"^\d+\.json$", f))
    r = {"n_files": len(files), "flags": []}
    if not files:
        r["flags"].append("no chapter files"); return r
    nums = [int(f[:-5]) for f in files]
    want = set(range(1, n_ch + 1))
    missing = sorted(want - set(nums))
    extra = sorted(set(nums) - want)
    if missing: r["flags"].append("missing chapters: " + str(missing[:15]) + ("…" if len(missing) > 15 else ""))
    if extra: r["flags"].append("extra chapter files: " + str(extra[:10]))
    first_txt = last_txt = None
    empties, overs = [], []
    junk = []
    for f in files:
        try:
            data = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception as e:
            r["flags"].append(f + " unreadable: " + str(e)[:60]); continue
        if not isinstance(data, dict) or not data:
            empties.append(f); continue
        try:
            keys = sorted(int(k) for k in data)
        except ValueError:
            r["flags"].append(f + " has non-integer keys"); continue
        idx = int(f[:-5]) - 1
        if not flow and 0 <= idx < len(para_counts) and keys and keys[-1] >= para_counts[idx]:
            overs.append(f + " maxkey " + str(keys[-1]) + "/" + str(para_counts[idx]))
        vals = [str(data[k]) for k in sorted(data, key=lambda x: int(x))]
        blob = " ".join(vals)
        for sign in ("Project Gutenberg", "Transcriber", "Produced by", "*** START", "*** END", "eBook", "E-text", "etext"):
            if sign in blob:
                junk.append(f + ": " + sign); break
        if f == files[0]:
            first_txt = clip(vals[0]); r["first_key"] = keys[0]
        if f == files[-1]:
            last_txt = clip(vals[-1], 300)
    if empties: r["flags"].append("empty files: " + str(empties[:10]))
    if overs: r["flags"].append("keys beyond RU paragraph count: " + " | ".join(overs[:6]))
    if junk: r["flags"].append("gutenberg/transcriber junk: " + " | ".join(junk[:6]))
    r["first"] = first_txt
    r["last"] = last_txt
    return r

def main():
    man = json.load(open(MAN, encoding="utf-8"))
    a = int(os.environ.get("QC_START", "0")); b = int(os.environ.get("QC_END", "99999"))
    man = [e for e in man if e.get("filename") and not e.get("isBible")][a:b]
    out = []
    seen = set()
    for e in man:
        fn = e.get("filename")
        if not fn or e.get("isBible"):
            continue
        rec = {"filename": fn, "title": e.get("title", ""), "author": e.get("author", ""),
               "category": e.get("category", ""), "flow": bool(e.get("flowEn"))}
        path = os.path.join(ROOT, "public", "books", fn)
        if not os.path.exists(path):
            path = os.path.join(ROOT, "private", "books", fn)
        if not os.path.exists(path):
            rec["ru"] = {"error": "file not found: " + fn}
            out.append(rec); continue
        key = fn
        if key in seen:
            rec["dup_of_scanned"] = True
        seen.add(key)
        rec["ru"] = scan_ru(path, e.get("title", ""))
        pe = e.get("parallelEn")
        if pe:
            rec["en_dir"] = pe
            nch = rec["ru"].get("n_chapters", 0)
            rec["en"] = scan_en(pe, nch, rec["ru"].get("para_counts", []), rec["flow"])
        out.append(rec)
        sys.stderr.write(".")
    tag = os.environ.get("QC_START", "0")
    json.dump(out, open(os.path.join(ROOT, "tools", "qc-report-%s.json" % tag), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    sys.stderr.write("\n%d entries scanned\n" % len(out))

if __name__ == "__main__":
    main()
