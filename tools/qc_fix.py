#!/usr/bin/env python3
"""Apply the QC fixes: strip publisher/source junk from FB2 heads and tails,
delete apparatus sections, patch English pairing JSONs, shift sync maps.
Driven by the SPEC below; verifies every edit by reparsing. Run stages:
  python3 tools/qc_fix.py ru-tail | ru-head | en | verify
"""
import io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import chapters

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def bpath(fn):
    p = os.path.join(ROOT, "public", "books", fn)
    return p if os.path.exists(p) else os.path.join(ROOT, "private", "books", fn)

def load(fn):
    raw = io.open(bpath(fn), "rb").read()
    m = re.match(rb"<\?xml[^>]*encoding=[\"\']([\w-]+)", raw[:200])
    encs = ([m.group(1).decode("ascii","ignore")] if m else []) + ["utf-8","cp1251"]
    for enc in encs:
        try: return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError): continue
    raise RuntimeError("decode "+fn)

def save(fn, text, enc):
    io.open(bpath(fn), "w", encoding=enc, errors="xmlcharrefreplace").write(text)

P_RE = re.compile(r"<(?:p|v|subtitle)\b[^>]*>.*?</(?:p|v|subtitle)>", re.S)
def strip_tags(t): return re.sub(r"<[^>]+>", "", t)

def rm_para(text, snippet, from_end=False):
    """Remove the first (or last) <p> whose text contains snippet."""
    matches = list(P_RE.finditer(text))
    it = reversed(matches) if from_end else iter(matches)
    for m in it:
        if snippet in re.sub(r"\s+"," ",strip_tags(m.group(0))):
            return text[:m.start()] + text[m.end():], True
    return text, False

def rm_section(text, marker):
    i = text.find(marker)
    if i < 0: return text, False
    start = text.rfind("<section", 0, i)
    if start < 0: return text, False
    # balanced walk
    pos, depth = start, 0
    tok = re.compile(r"<section\b|</section>")
    for m in tok.finditer(text, start):
        depth += 1 if m.group(0).startswith("<section") else -1
        if depth == 0:
            end = m.end()
            return text[:start] + text[end:], True
    return text, False

def ins_paras(text, anchor_snippet, paras):
    """Insert <p> paragraphs immediately before the <p> containing anchor."""
    for m in P_RE.finditer(text):
        if anchor_snippet in re.sub(r"\s+"," ",strip_tags(m.group(0))):
            tag = re.match(r"<(\w+)", m.group(0)).group(1)
            block = "".join("<%s>%s</%s>" % (tag, p, tag) for p in paras)
            return text[:m.start()] + block + text[m.start():], True
    return text, False

SPEC = json.load(open(os.path.join(ROOT,"tools", os.environ.get("QC_SPEC","qc-fix-spec.json")), encoding="utf-8"))

def apply_ru(kind):
    ok, fail = 0, []
    for fn, spec in SPEC.items():
        ops = spec.get(kind) or []
        if not ops: continue
        text, enc = load(fn)
        for op in ops:
            t = op[0]
            if t == "rm_tail":   text, hit = rm_para(text, op[1], from_end=True)
            elif t == "rm_head_sec":
                i = text.find("<section")
                head, body = text[:i], text[i:]
                body, hit = rm_para(body, op[1])
                text = head + body
            elif t == "rm_head": text, hit = rm_para(text, op[1])
            elif t == "rm_sec":  text, hit = rm_section(text, op[1])
            elif t == "repl":
                hit = op[1] in text
                text = text.replace(op[1], op[2])
            elif t == "repl_re":
                text, n = re.subn(op[1], op[2], text)
                hit = n > 0
            elif t == "rm_all_re":
                pat = re.compile(op[1]); hit = False
                while True:
                    for m in P_RE.finditer(text):
                        if pat.search(re.sub(r"\s+"," ",strip_tags(m.group(0))).strip()):
                            text = text[:m.start()] + text[m.end():]; hit = True; break
                    else: break
            elif t == "ins":     text, hit = ins_paras(text, op[1], op[2])
            else: hit = False
            if not hit: fail.append((fn, op[0], op[1][:60]))
        save(fn, text, enc)
        ok += 1
    print(kind, "applied to", ok, "files;", len(fail), "misses")
    for f in fail: print("  MISS", f)

def verify():
    bad = 0
    for fn, spec in SPEC.items():
        v = spec.get("verify")
        if not v: continue
        chs = chapters(bpath(fn), spec.get("title",""))
        if chs is None: print("VERIFY FAIL (unparseable)", fn); bad += 1; continue
        msgs = []
        if "n" in v and len(chs) != v["n"]: msgs.append("n=%d want %d" % (len(chs), v["n"]))
        first = re.sub(r"\s+"," ",chs[0][0]).strip()
        last  = re.sub(r"\s+"," ",chs[-1][-1]).strip()
        if "first" in v and not first.startswith(v["first"]): msgs.append("first=%r" % first[:70])
        if "last" in v and v["last"] not in last: msgs.append("last=%r" % last[-70:])
        if msgs: print("VERIFY", fn, "; ".join(msgs)); bad += 1
    print("verify done,", bad, "problems")

if __name__ == "__main__":
    stage = sys.argv[1]
    if stage in ("ru-tail","ru-head"): apply_ru(stage)
    elif stage == "verify": verify()
