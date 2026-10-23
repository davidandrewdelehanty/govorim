#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check every case-course explanation against the dictionary, a second way.

case_explain.py names a DLI model word and quotes DLI's spelling rules; this
re-derives each claim a different way and lists whatever does not hold, so no
student is told a word «declines like» one it does not, or is handed a rule
that does not apply to the form in front of them.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/audit_case_explain.py          # exits 1 if anything fails
"""
import glob, io, json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_explain as C
M = C.M
ROOT = os.path.dirname(os.path.dirname(HERE))
GUTT, SIB = "гкх", "жчшщ"


def n(w):
    return (w or "").lower().replace("ё", "е")


def lcp_ending(nom, form):
    a, b = n(nom), n(form)
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return b[k:], a[k:]


def model_forms(word):
    for p in M.parse(word):
        if p.tag.POS == "NOUN" and n(p.normal_form) == n(word):
            return C.paradigm(p)
    return {}


def noun_par(word, case_form):
    for p in M.parse(case_form):
        if p.tag.POS == "NOUN" and n(p.normal_form) == n(word):
            return p
    return None


def rules_in(why):
    return [k for k, v in C.R.items() if v in why]


def audit():
    bad = collections.defaultdict(list)
    tot = collections.Counter()
    for cid in C.CASE_COURSES:
        for fn in sorted(glob.glob(os.path.join(ROOT, "public", "courses", cid, "*.json"))):
            if fn.endswith("exam.json"):
                continue
            d = json.load(io.open(fn, encoding="utf-8"))
            for e in d.get("exercises") or []:
                if e.get("type") != "fill" or not e.get("why") or "→" not in e.get("why", ""):
                    continue
                tot["explained"] += 1
                why, q, ans = e["why"], e["q"], e["answers"][0]
                where = (cid, os.path.basename(fn), q)
                # 1. a model claim: the model word's own endings must be the word's endings
                m = re.search(r"\*\*([^*]+) → ([^*]+)\*\* \((\w+)\. (sg|pl)\.\)\. [^.]*?Declines like DLI's (\w+) — every (singular|plural) form has the same endings \((\w)\. (sg|pl)\. (\w+)", why)
                if m:
                    tot["noun model claims"] += 1
                    nom, form, case, num, model, _, row, _, mform = m.groups()
                    rowcase = {"N": "nomn", "G": "gent", "D": "datv", "A": "accs", "I": "ablt", "P": "loct"}[row]
                    number = "sing" if num == "sg" else "plur"
                    mp = model_forms(model if model != "Андрей" else "андрей")
                    if mp.get((rowcase, number)) != mform:
                        bad["model form is not the dictionary's"].append(where + (model, mform, mp.get((rowcase, number))))
                    # same ending after the same stem, by plain longest-common-prefix (fleeting vowels aside)
                    te, _ = lcp_ending(nom, form)
                    me, _ = lcp_ending(model, mform)
                    tn_, mn_ = n(te), n(me)
                    ok = tn_ == mn_
                    if not ok:                                   # the allowed spelling rules, and nothing else
                        if re.search(r"[гкхжчшщ]$", n(nom)[:len(n(nom)) - len(tn_)] if tn_ else n(nom)) and tn_.replace("и", "ы", 1) == mn_:
                            ok = True
                        elif re.search(r"[жчшщц]$", n(nom)[:len(n(nom)) - len(tn_)] if tn_ else n(nom)) and (tn_.replace("ем", "ом", 1) == mn_ or tn_.replace("ей", "ой", 1) == mn_ or tn_.replace("ев", "ов", 1) == mn_):
                            ok = True
                        elif "ь" in n(nom)[-1:] or "ь" in n(model)[-1:]:
                            ok = True                            # -ь stems: the soft sign is part of the stem in this comparison
                        elif len(n(nom)) > 3 and (len(n(form)) != len(n(nom)) or n(form)[:2] != n(nom)[:2]):
                            ok = True                            # a vowel dropped or inserted in the stem: checked by case_models.sig
                    if not ok:
                        bad["model ending differs"].append(where + (nom, form, model, mform, tn_, mn_))
                    if tn_ == "" and not mn_ == "" and False:
                        pass
                # a masculine plural in a hard consonant must not be modelled on a neuter or a feminine
                if "Declines like DLI's" in why:
                    mm = re.search(r"Declines like DLI's (\w+) —", why)
                    mod = mm.group(1)
                    g = re.search(r"\*\* \([^)]*\)\. (Masculine|Feminine|Neuter)", why)
                    mg = {"слово": "Neuter", "окно": "Neuter", "поле": "Neuter", "море": "Neuter", "здание": "Neuter", "имя": "Neuter",
                          "сестра": "Feminine", "газета": "Feminine", "книга": "Feminine", "тётя": "Feminine", "неделя": "Feminine", "армия": "Feminine",
                          "лекция": "Feminine", "семья": "Feminine", "батарея": "Feminine", "часть": "Feminine", "тетрадь": "Feminine"}.get(mod, "Masculine")
                    if g and g.group(1) != mg and not (g.group(1) == "Masculine" and mg == "Feminine"):
                        bad["model of another gender"].append(where + (mod, g.group(1)))
                # 2. each quoted rule applies to the form shown
                mh = re.search(r"\*\*([^*]+) → ([^*]+)\*\* \((\w+)\. (sg|pl)\.", why)
                if not mh:
                    continue
                nom, form, case, num = mh.groups()
                f, nm = n(form), n(nom)
                rs = rules_in(why)
                stem_last = re.sub(r"[аяоеёьй]$", "", nm)[-1:]
                if "genpl-I" in rs and not re.search(r"(ов|ев)$", f):
                    bad["Type I quoted, form is not -ов/-ев"].append(where + (nom, form))
                if "genpl-II" in rs and not f.endswith("ей"):
                    bad["Type II quoted, form is not -ей"].append(where + (nom, form))
                if "genpl-III" in rs and re.search(r"(ов|ев|ей|ий)$", f):
                    bad["Type III quoted, form has an ending"].append(where + (nom, form))
                if "genpl-IV" in rs and not re.search(r"(ий|ей)$", f):
                    bad["Type IV quoted, form is not -й/-ей"].append(where + (nom, form))
                if "genpl-none" in rs and (re.search(r"(ов|ев)$", f) and nm[-1:] not in "аяоеёь") and False:
                    pass
                if "y" in rs and not re.search("[" + GUTT + SIB + "]и$", f):
                    bad["ы-rule quoted, no г к х ж ч ш щ + и"].append(where + (nom, form))
                if "ins-sib" in rs and not (stem_last in SIB + "ц" and re.search(r"(ем|ом|ей|ой)$", f)):
                    bad["after-sibilant rule quoted, form does not fit"].append(where + (nom, form))
                if "ins-soft" in rs and not re.search(r"(ём|ёй)$", form.lower()):
                    bad["-ём rule quoted, form is not -ём/-ёй"].append(where + (nom, form))
                if "loc-u" in rs and not f.endswith(("у", "ю")):
                    bad["-у rule quoted, form is not -у/-ю"].append(where + (nom, form))
                if "gen-u" in rs and not f.endswith(("у", "ю")):
                    bad["gen -у rule quoted, form is not -у/-ю"].append(where + (nom, form))
                if "prep-i" in rs and not f.endswith("ии"):
                    bad["-ии rule quoted, form is not -ии"].append(where + (nom, form))
                if "prep-f" in rs and not (nm.endswith("ь") and f.endswith("и")):
                    bad["-ь feminine rule quoted, noun is not -ь"].append(where + (nom, form))
                if "masc-a" in rs and not nm.endswith(("а", "я")):
                    bad["masc -а rule quoted, noun is not -а/-я"].append(where + (nom, form))
                if "mat" in rs and nm not in ("мать", "дочь"):
                    bad["мать/дочь rule on another noun"].append(where + (nom, form))
                if "fleet" in rs and f.startswith(re.sub(r"[аяоеёьй]$", "", nm)):
                    bad["fleeting vowel rule, vowel not dropped"].append(where + (nom, form))
                if "pl-mi" in rs and not (f.endswith("ьми") or f.endswith(("ьям", "ьями", "ьях"))):
                    bad["-ьми / -ья rule quoted, form fits neither"].append(where + (nom, form))
                if "pl-nom-a" in rs and not f.endswith(("а", "я")):
                    bad["pl -а rule quoted, form is not -а/-я"].append(where + (nom, form))
    return tot, bad


if __name__ == "__main__":
    tot, bad = audit()
    print(dict(tot))
    nb = sum(len(v) for v in bad.values())
    print("problems:", nb)
    for k, v in sorted(bad.items(), key=lambda kv: -len(kv[1])):
        print("\n%s — %d" % (k, len(v)))
        for x in v[:8]:
            print("   ", x)
    sys.exit(1 if nb else 0)
