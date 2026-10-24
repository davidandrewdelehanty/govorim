# -*- coding: utf-8 -*-
"""Verbs of Motion: the long explanation motion_explain writes (the form, Wiktionary's glosses and conjugation, the prefix quote from
Wikipedia and several DLI paragraphs) cut to what this exercise needs:
«**вёл** — past tense (masculine) of вести: one-direction verb (many directions: водить).  Prefix **под-**: approach (к + dat.; до + gen.).»
Idempotent: an explanation already short is left alone.   Usage: motion_short.py [--apply]
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DIR = os.path.join(ROOT, "public", "courses", "motion")


def balanced(s, i):
    """Index just past the parenthesis that closes the one at s[i]."""
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j + 1
    return -1


def plain(t):
    return t.replace("**", "").strip()


def rest_short(r):
    r = r.strip().rstrip(".")
    m = re.match(r"(perfective|imperfective); its (?:perfective|imperfective) partner is \*\*([^*]+)\*\*", r)
    if m:
        other = "imperfective" if m.group(1) == "perfective" else "perfective"
        return "%s (%s partner: %s)" % (m.group(1), other, m.group(2))
    m = re.match(r"the one-direction verb of its pair, with \*\*([^*]+)\*\* for many directions", r)
    if m:
        return "one-direction verb (many directions: %s)" % m.group(1)
    m = re.match(r"the many-directions \(or there-and-back\) verb of its pair, with \*\*([^*]+)\*\* for one direction", r)
    if m:
        return "many-directions verb (one direction: %s)" % m.group(1)
    return plain(r)


def prefix_short(why):
    for m in re.finditer(r"«\*\*([^*]+)\*\* — ([^»]*)»\s*— Wikipedia", why):
        pre, body = m.group(1), m.group(2)
        if not pre.endswith("-") and "-" not in pre:
            continue
        d = re.split(r"\s+(?:Example:|Antonym:|Prepositional phrases:)", body)[0].strip().rstrip(".")
        pp = re.search(r"Prepositional phrases:\s*(.*)$", body)
        s = "Prefix **%s**: %s" % (pre, d[:1].lower() + d[1:])
        if pp:
            s += " (%s)" % pp.group(1).strip().rstrip(".")
        return s + "."
    return None


def shorten(why):
    if "Wiktionary" not in why and "DLI" not in why and "Wikipedia" not in why:
        return why
    out = None
    m = re.match(r"\*\*([^*]+)\*\* is the (.+?) of \*\*([^*]+)\*\*", why)
    if m:
        mm = re.search(r"\s—\s(.+?)\.\s", why[m.end():] + " ")
        if mm:
            out = "**%s** — %s of %s: %s." % (m.group(1), m.group(2), m.group(3), rest_short(mm.group(1)))
    else:
        m = re.match(r"\*\*([^*]+)\*\* \(the infinitive\)", why)
        if m:
            mm = re.search(r"\s—\s(.+?)\.\s", why[m.end():] + " ")
            if mm:
                out = "**%s** — infinitive, %s." % (m.group(1), rest_short(mm.group(1)))
    if not out:
        return None
    pf = prefix_short(why)
    return out + ("  " + pf if pf else "")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv
    n_ok = n_bad = 0
    bad = []
    for fn in sorted(os.listdir(DIR)):
        if not fn.endswith(".json") or fn == "exam.json":
            continue
        p = os.path.join(DIR, fn)
        j = json.load(io.open(p, encoding="utf-8"))
        for e in j.get("exercises") or []:
            w = e.get("why") or ""
            s = shorten(w)
            if s is None:
                n_bad += 1
                bad.append((fn, w[:120]))
                continue
            n_ok += 1
            e["why"] = s
            e["context"] = ""
        if apply:
            io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print("motion_short: %d shortened, %d left as they were%s" % (n_ok, n_bad, "" if apply else " (dry run)"))
    for b in bad[:6]:
        print("   unparsed:", b)


if __name__ == "__main__":
    main()
