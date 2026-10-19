#!/usr/bin/env python3
"""Real English–Russian sentence pairs for the "English tenses in Russian"
course, chosen by script — no sentence is written by hand.

Input: the Tatoeba Russian–English pair file (ManyThings `rus.txt`, or
Tatoeba's `id, ru, id, en` pair export) — CC BY 2.0 FR, attribution kept.

For every pair:
  * the English is sorted into a tense by its auxiliary verbs ("have been
    …ing" → present perfect progressive, "had …ed" → past perfect, "will be
    …ing" → future progressive, "used to" → past habit …);
  * the Russian is read with pymorphy3: the first verb from the 300
    commonest verbs in the library (public/vocab/verbs/index.json), with its
    tense, aspect, person/gender; "буду + infinitive" is the compound future;
  * kept if both are clear and the Russian sentence is short and plain.

Up to 12 pairs per English tense, no verb used twice in a tense, commonest
verbs first. Writes tools/courses/tense_pairs.json, which
tools/courses/tense_course.py turns into lessons and exercises.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/tense_examples.py ~/tatoeba/rus.txt
    python3 tools/courses/build_courses.py
"""
import io, json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
import pymorphy3

HAS_CYR = re.compile(r"[А-Яа-яЁё]")
LATIN = re.compile(r"[A-Za-z]")
RU_WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")

IRR = ("been|done|gone|seen|said|told|made|taken|given|come|become|left|known|thought|found|got|gotten|"
       "brought|bought|written|read|heard|met|put|run|sat|stood|understood|forgotten|begun|spoken|eaten|"
       "drunk|lost|sent|spent|kept|held|felt|built|paid|won|chosen|driven|fallen|flown|grown|shown|"
       "thrown|worn|broken|woken|hidden|ridden|risen|sung|swum|taught|caught|fought|sold|slept|lent|let|"
       "set|cut|hit|hurt|shut|quit|meant|led|fed|dealt|stolen|forgiven|drawn|beaten")
PART = r"(?:\w+ed|" + IRR + r")"
SUBJ = r"(?:I|you|he|she|it|we|they|Tom|Mary|[A-Z][a-z]+)"
PAST_IRR = ("was|were|did|went|saw|said|told|made|took|gave|came|became|left|knew|thought|found|got|"
            "brought|bought|wrote|heard|met|ran|sat|stood|understood|forgot|began|spoke|ate|"
            "drank|lost|sent|spent|kept|held|felt|built|paid|won|chose|drove|fell|flew|grew|showed|"
            "threw|wore|broke|woke|hid|rode|rose|sang|swam|taught|caught|fought|sold|slept|meant|led|"
            "asked|answered|wanted|decided|looked|worked|lived|loved|liked|tried|called|waited|stayed|"
            "returned|helped|opened|closed|started|finished|stopped|walked|played|watched|listened|seemed|"
            "happened|remembered|needed|turned|explained|learned|studied|cried|smiled|laughed|died")

# Order matters: the first pattern that matches decides.
TENSES = [
    ("pres-perf-prog", "Present perfect progressive", r"\b(?:have|has|'ve|'s)\s+been\s+\w+ing\b"),
    ("past-perf",      "Past perfect",                 r"\b(?:had|'d)\s+(?:just\s+|already\s+|never\s+|not\s+|n't\s+)?" + PART + r"\b"),
    ("fut-prog",       "Future progressive",           r"\b(?:will|'ll)\s+be\s+\w+ing\b"),
    ("going-to",       "Going to",                     r"\b(?:am|is|are|'m|'re|'s)\s+(?:not\s+)?going\s+to\s+(?!the\b|a\b|school|work|bed)\w+"),
    ("used-to",        "Used to",                      r"\bused\s+to\s+\w+"),
    ("would",          "Would (conditional)",          r"\b(?:would|'d)\s+(?:not\s+|n't\s+)?(?!like\b|rather\b)\w+"),
    ("pres-perf",      "Present perfect",              r"\b(?:have|has|'ve)\s+(?:just\s+|already\s+|never\s+|ever\s+|not\s+|n't\s+|always\s+)?" + PART + r"\b(?!\s+to\b)"),
    ("fut",            "Future",                       r"\b(?:will|'ll|won't|shall)\s+(?!be\s+\w+ing)\w+"),
    ("past-prog",      "Past progressive",             r"\b(?:was|were)\s+(?:not\s+)?\w+ing\b"),
    ("pres-prog",      "Present progressive",          r"\b(?:am|is|are|'m|'re)\s+(?:not\s+)?(?!going\s+to)\w+ing\b"),
    ("past",           "Past simple",                  r"\b" + SUBJ + r"\s+(?:didn't\s+\w+|did\s+not\s+\w+|" + PAST_IRR + r")\b"),
    ("pres",           "Present simple",               r"^(?:I|You|We|They)\s+(?:don't\s+|do\s+not\s+|always\s+|usually\s+|often\s+|never\s+|sometimes\s+)?(?:know|think|want|like|love|live|work|speak|understand|see|read|write|need|believe|remember|go|hear|feel|hope|play|say)\b|^(?:He|She|Tom|Mary)\s+(?:doesn't\s+\w+|always\s+\w+s|usually\s+\w+s|often\s+\w+s|never\s+\w+s|(?:knows|thinks|wants|likes|loves|lives|works|speaks|understands|sees|reads|writes|needs|believes|remembers|goes|hears|feels|hopes|plays|says))\b"),
]
TENSES = [(k, n, re.compile(p, re.I if k != "pres" else 0)) for k, n, p in TENSES]

# One clause only: a second verb in English or Russian would let the tense of
# one clause be matched with the verb of the other.
SUBCLAUSE = re.compile(r",|;|\b(?:that|if|when|whether|because|who|which|what|where|why|how|said|says|told|tell|know|knew|think|thought|than|while|before|after|until|so)\b", re.I)

# Nothing coarse in a course; and "could've / should have" is not the present perfect.
ROUGH = re.compile(r"\b(?:piss|shit|fuck|damn|hell|ass|boob|crap|sex|bitch|bastard|drunk|kill|gun|die|dead)\w*", re.I)
MODAL_PERF = re.compile(r"\b(?:could|should|would|might|must|may|can|cannot|can't|couldn't|shouldn't|wouldn't|mustn't)(?:\s+not)?\s*(?:'ve|have)\b", re.I)

# What DLI says each English tense becomes in Russian (Grammar Reference Book,
# Lessons 37, 84–94): the Russian verb must have this shape to be kept.
def fits(tense, h):
    t, a = h["tense"], h["aspect"]
    return {
        "pres":           t == "pres" and a == "impf",
        "pres-prog":      t == "pres" and a == "impf",
        "pres-perf-prog": t == "pres" and a == "impf",
        "pres-perf":      t == "past",
        "past":           t == "past" and not h.get("bi"),
        "past-prog":      t == "past" and a == "impf",
        "past-perf":      t == "past" and a == "perf",
        "used-to":        t == "past" and a == "impf",
        "fut":            t == "futr",
        "fut-prog":       t == "futr" and h.get("compound"),
        "going-to":       t == "futr",
        "would":          t == "past" and h.get("bi"),
    }.get(tense, False)


def read(path):
    out = []
    with io.open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for line in fh:
            parts = [c.strip() for c in line.replace("\r", "").rstrip("\n").split("\t")]
            ru = en = None
            attr = ""
            for c in parts:
                if not c:
                    continue
                if "tatoeba.org" in c or "CC-BY" in c:
                    attr = c
                elif ru is None and HAS_CYR.search(c):
                    ru = c
                elif en is None and LATIN.search(c) and not HAS_CYR.search(c):
                    en = c
            if ru and en:
                out.append((ru, en, attr))
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    idx = json.load(io.open("public/vocab/verbs/index.json", encoding="utf-8"))
    top = [v for v, n in idx["top"][:300]]
    rank = {v: i for i, v in enumerate(top)}
    m = pymorphy3.MorphAnalyzer()
    pairs = read(sys.argv[1])
    print("%d pairs" % len(pairs), flush=True)
    found = defaultdict(list)
    for ru, en, attr in pairs:
        if not (12 <= len(ru) <= 70 and 10 <= len(en) <= 70) or "," in ru or SUBCLAUSE.search(en):
            continue
        if ROUGH.search(en) or MODAL_PERF.search(en):
            continue
        tense = None
        for k, name, rx in TENSES:
            if rx.search(en):
                tense = k
                break
        if not tense:
            continue
        words = RU_WORD.findall(ru)
        if not 3 <= len(words) <= 12:
            continue
        hit = None
        for i, w in enumerate(words):
            for p in m.parse(w.lower())[:1]:
                if p.tag.POS not in ("VERB", "INFN"):
                    continue
                lem = p.normal_form
                if lem == "быть" and p.tag.POS == "VERB" and "futr" in p.tag and i + 1 < len(words):
                    # буду + infinitive: the compound future of the next verb
                    q = m.parse(words[i + 1].lower())[0]
                    if q.tag.POS == "INFN" and q.normal_form in rank:
                        hit = {"lemma": q.normal_form, "form": w + " " + words[i + 1], "tense": "futr",
                               "aspect": "impf", "compound": True}
                        break
                if lem in rank and lem != "быть":
                    t = p.tag
                    hit = {"lemma": lem, "form": w, "aspect": "perf" if "perf" in t else "impf",
                           "tense": ("past" if "past" in t else "futr" if "futr" in t else "pres") if p.tag.POS == "VERB" else "inf",
                           "mood": "impr" if "impr" in t else "", "bi": "бы" in [x.lower() for x in words],
                           "person": str(t.person or ""), "number": str(t.number or ""), "gender": str(t.gender or "")}
                    break
            if hit:
                break
        if not hit or hit.get("mood") == "impr" or not fits(tense, hit):
            continue
        # Exactly one finite verb in the Russian (бы and the буду of a compound future aside).
        finite = [w for w in words if m.parse(w.lower())[0].tag.POS == "VERB"]
        if len(finite) - (1 if hit.get("compound") else 0) != 1:
            continue
        found[tense].append({"ru": ru, "en": en, "attr": attr, **hit})
    out = {}
    for k, name, rx in TENSES:
        rows = sorted(found[k], key=lambda r: (rank[r["lemma"]], len(r["ru"])))
        used, picked = set(), []
        for r in rows:
            if r["lemma"] in used:
                continue
            used.add(r["lemma"])
            picked.append(r)
            if len(picked) == 12:
                break
        out[k] = {"name": name, "pairs": picked, "found": len(found[k])}
        print("%-26s %5d pairs found · %2d kept · e.g. %s" % (name, len(found[k]), len(picked),
              (picked[0]["en"] + " → " + picked[0]["ru"]) if picked else "—"), flush=True)
    io.open("tools/courses/tense_pairs.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("\nWrote tools/courses/tense_pairs.json")


if __name__ == "__main__":
    main()
