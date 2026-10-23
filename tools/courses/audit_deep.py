# -*- coding: utf-8 -*-
"""Deep audit of every exercise in every course. Prints counts per check and a few samples; --all prints every hit.

    python3 tools/courses/audit_deep.py [--course ID] [--check NAME] [--all]
"""
import io, json, os, re, sys, glob, argparse
from collections import Counter, defaultdict
import pymorphy3
M = pymorphy3.MorphAnalyzer()
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public", "courses")
CYR = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
norm = lambda w: w.lower().replace("ё", "е")
HITS = defaultdict(list)


def hit(check, course, fn, e, note=""):
    HITS[check].append((course, os.path.basename(fn), (e.get("q") or "")[:90], (e.get("answers") or [e.get("answer")])[0] if (e.get("answers") or e.get("answer") is not None) else None, note))


def known(w):
    ps = M.parse(w)
    return any(p.is_known for p in ps)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--course"); ap.add_argument("--check"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    seen_q = defaultdict(list)
    for d in sorted(glob.glob(os.path.join(ROOT, "*"))):
        cid = os.path.basename(d)
        if cid.startswith("_") or not os.path.isdir(d) or (a.course and cid != a.course):
            continue
        for fn in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                raw = io.open(fn, encoding="utf-8").read()
                j = json.loads(raw)
            except Exception as ex:
                HITS["bad_json"].append((cid, os.path.basename(fn), "", None, str(ex)[:60])); continue
            exam = os.path.basename(fn) == "exam.json"
            exs = []
            if exam:
                for t in j.get("topics") or []:
                    exs += t.get("exercises") or []
            else:
                exs = j.get("exercises") or []
                ids = [e.get("id") for e in exs]
                if len(ids) != len(set(ids)):
                    HITS["dup_ids"].append((cid, os.path.basename(fn), "", None, "%d dup" % (len(ids) - len(set(ids)))))
            for e in exs:
                q, t = e.get("q") or "", e.get("type")
                if not q.strip():
                    hit("empty_q", cid, fn, e); continue
                if t == "mc":
                    opts = e.get("options") or []
                    ans = e.get("answer")
                    if len(opts) < 2: hit("mc_few_options", cid, fn, e)
                    if len(set(map(str, opts))) != len(opts): hit("mc_dup_options", cid, fn, e)
                    if isinstance(ans, int) and not (0 <= ans < len(opts)): hit("mc_answer_range", cid, fn, e, str(ans))
                    elif isinstance(ans, str) and ans not in opts: hit("mc_answer_not_option", cid, fn, e, ans[:40])
                    continue
                ans = e.get("answers") or []
                if not ans: hit("no_answers", cid, fn, e); continue
                if any((not isinstance(x, str)) or x != x.strip() or not x for x in ans): hit("answer_whitespace", cid, fn, e, repr(ans)[:60])
                if len(set(map(norm, ans))) != len(ans): hit("dup_answers", cid, fn, e, repr(ans)[:60])
                if q.count("___") != 1 and not exam: hit("blank_count", cid, fn, e, str(q.count("___")))
                a0 = ans[0]
                if re.search(r"[A-Za-z]", a0): hit("latin_in_answer", cid, fn, e)
                if re.search(r"\d", a0): hit("digit_in_answer", cid, fn, e)
                if re.search(r"  |^\s|\s$", q): hit("q_spacing", cid, fn, e)
                if "___" in q and re.search(r"___\s*\(\s*\)", q): hit("empty_hint", cid, fn, e)
                if not exam and not (e.get("prompt") or "").strip() and cid not in ("numerals",): hit("no_prompt", cid, fn, e)
                if (e.get("prompt") or "").strip() and norm(e["prompt"]) == norm(q): hit("prompt_equals_q", cid, fn, e)
                if re.search(r"\*\*[^*]*$|^[^*]*\*\*[^*]*$", e.get("why") or "") and (e.get("why") or "").count("**") % 2: hit("why_unbalanced_bold", cid, fn, e)
                # answer words unknown to the dictionary: a likely typo
                for w in CYR.findall(a0):
                    if len(w) > 2 and not known(w): hit("answer_unknown_word", cid, fn, e, w)
                # the sentence outside the blank: unknown words are likely typos in the source sentence
                if not exam:
                    for w in CYR.findall(re.sub(r"___ \([^)]*\)", " ", q)):
                        if len(w) > 3 and not known(w) and not re.match(r"^[А-ЯЁ]", w): hit("sentence_unknown_word", cid, fn, e, w)
                    seen_q[(cid, norm(q), norm(a0))].append(os.path.basename(fn))
    for k, v in seen_q.items():
        if len(v) > 1: HITS["duplicate_exercise"].append((k[0], ",".join(sorted(set(v)))[:50], k[1][:70], k[2], "x%d" % len(v)))
    out = Counter({k: len(v) for k, v in HITS.items()})
    print(dict(out))
    for k, v in HITS.items():
        if a.check and k != a.check: continue
        byc = Counter(x[0] for x in v)
        print("\n##", k, len(v), dict(byc))
        for x in (v if a.all else v[:6]): print("   ", x)


if __name__ == "__main__":
    main()
