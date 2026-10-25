"""Drop «Declines like X.» where X is an irregularly declining noun for that form (имя; дом/учитель in the plural) or is the word itself."""
import glob, json, re, sys, io
BAN_ALWAYS = {"имя"}
BAN_PLURAL = {"дом", "учитель"}
SENT = re.compile(r"\s*Declines like (\w+)\.")
def fix_seg(seg):
    head = re.match(r"\*\*([^*→]+?)\s*→\s*([^*]+)\*\*(.{0,60})", seg, re.S)
    plural = bool(re.search(r"\bpl\.", seg[:90]))
    lemma = head.group(1).strip().lower() if head else ""
    def rep(m):
        x = m.group(1)
        if x in BAN_ALWAYS or (plural and x in BAN_PLURAL) or x == lemma:
            return ""
        return m.group(0)
    return SENT.sub(rep, seg)
def fix(s):
    return "".join(fix_seg(p) for p in re.split(r"(?=\*\*[^*]+→)", s))
def walk(o, ch):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and "Declines like" in v:
                n = fix(v)
                if n != v: o[k] = n; ch[0] += 1
            else: walk(v, ch)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str) and "Declines like" in v:
                n = fix(v)
                if n != v: o[i] = n; ch[0] += 1
            else: walk(v, ch)
apply = "--apply" in sys.argv
tot = 0
for f in sorted(glob.glob("public/courses/*/*.json")):
    j = json.load(open(f, encoding="utf-8")); ch = [0]; walk(j, ch)
    if ch[0]:
        tot += ch[0]; print(f, ch[0])
        if apply: io.open(f, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
print("changed", tot, "" if apply else "(dry)")
