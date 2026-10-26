#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multiple-choice options in the form the sentence needs, dictionary form in brackets.

The word-formation course blanks a real word in a real sentence («Как ты ___?»
→ вошёл) but used to offer the dictionary forms as the choices (войти́, вы́йти,
прийти́, пойти́). A reader then has to pick an infinitive for a slot that no
infinitive fits. Here every option becomes the SAME form as the blanked word,
made from that option's own word, with the dictionary form after it:

    вошёл (войти́) · вышел (вы́йти) · пришёл (прийти́) · пошёл (пойти́)

How a form is made — OpenCorpora via pymorphy3, nothing guessed:
  * the blanked word comes from the explanation's **bold** token; its reading
    is the one whose dictionary form is the answer option;
  * the grammemes that belong to the FORM (tense, person, number, past gender,
    mood, case, voice...) are carried over to each other option's own lexeme;
    perfective future ↔ imperfective present count as the same slot;
  * if the blanked word has several readings (стойки: gen. sg. or nom. pl.)
    an option is kept only when every reading gives it the same form;
  * an option no reading can be made from is dropped; an exercise left with
    fewer than three options is dropped.

Stress: an acute only where tools/data/stress-dict.json.gz (OpenRussian, the
reader's own map — words with one stress across the whole dictionary) knows the
form, or none needed (ё, one vowel). No mark rather than a possibly wrong one.

When the blanked word already IS the dictionary form (разгляде́ть), the options
stay as they were — a bracket would only repeat the word.

    python3 tools/courses/inflect_options.py            # report
    python3 tools/courses/inflect_options.py --apply    # build_courses.py does this
"""
import argparse, glob, gzip, io, json, os, re

import pymorphy3

M = pymorphy3.MorphAnalyzer()
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.join(REPO, "public", "courses")
ACC = "́"
VOW = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
_SD = None

FORM_LEVEL = {"tense": ("pres", "futr", "past"), "person": ("1per", "2per", "3per"),
              "number": ("sing", "plur"), "mood": ("indc", "impr"), "involvement": ("incl", "excl"),
              "voice": ("actv", "pssv"),
              "case": ("nomn", "gent", "datv", "accs", "ablt", "loct", "voct", "gen2", "acc2", "loc2")}
VERBISH = {"INFN", "VERB", "GRND", "PRTF", "PRTS"}


def plain(s):
    return s.replace(ACC, "").lower()


def yo(s):
    return s.replace("ё", "е")


def stress_dict():
    global _SD
    if _SD is None:
        _SD = json.load(gzip.open(os.path.join(REPO, "tools", "data", "stress-dict.json.gz"), "rt", encoding="utf-8"))
    return _SD


def accent(w):
    """w with its stress marked, where the stress is certain; otherwise w as it is."""
    if "ё" in w or sum(ch in VOW for ch in w) <= 1:
        return w
    i = stress_dict().get(w)
    if not isinstance(i, int) or i >= len(w) or w[i] not in VOW:
        return w
    return w[:i + 1] + ACC + w[i + 1:]


def grams(tag):
    """The grammemes of one form that another word of the same kind can be put into."""
    g = set()
    if tag.POS in VERBISH:
        g.add(tag.POS)
    for attr in FORM_LEVEL:
        v = getattr(tag, attr)
        if v:
            g.add(v)
    if tag.POS in ("VERB", "PRTS", "PRTF", "ADJF", "ADJS") and tag.gender and tag.number == "sing":
        g.add(tag.gender)
    if tag.POS in ("ADJF", "PRTF") and tag.case == "accs" and tag.animacy:
        g.add(tag.animacy)
    if tag.POS in ("ADJS", "COMP", "ADJF"):
        g.add(tag.POS)
    return frozenset(g)


def lemma_parses(lemma):
    """Readings of a dictionary form that are its own dictionary form."""
    return [p for p in M.parse(lemma) if yo(p.normal_form) == yo(lemma) and yo(p.word) == yo(lemma)]


def make(lemma, g, verb):
    """lemma put into grammemes g, or None."""
    outs = set()
    for p in lemma_parses(lemma):
        if verb != (p.tag.POS in VERBISH):
            continue
        for gg in (g, g - {"futr"} | {"pres"} if "futr" in g else g - {"pres"} | {"futr"} if "pres" in g else None):
            if gg is None:
                continue
            f = p.inflect(set(gg))
            if f:
                outs.add(f.word)
                break
    return outs.pop() if len(outs) == 1 else None


def readings(tok, lemma):
    t = tok.lower()
    return [p for p in M.parse(t) if yo(p.normal_form) == yo(lemma) and yo(p.word) == yo(t)]


def fix(e):
    """New options/answer for one exercise: (options, answer) / "same" / None (cannot)."""
    m = re.match(r"\*\*(.+?)\*\*", e.get("why") or "")
    if not m or any("(" in o for o in e["options"]):
        return "same"
    tok = m.group(1).strip().lower()
    lem = [plain(o) for o in e["options"]]
    ans = lem[e["answer"]]
    if yo(tok) == yo(ans):
        return "same"
    rs = readings(tok, ans)
    # «приведём» is also the inclusive imperative ("let's bring"); its form is the
    # 1st plural future, and an imperfective has no such imperative — so the
    # indicative reading stands for both whenever there is one.
    if any(r.tag.involvement != "incl" for r in rs):
        rs = [r for r in rs if r.tag.involvement != "incl"]
    if not rs:
        return None
    gs = {grams(r.tag) for r in rs}
    verb = rs[0].tag.POS in VERBISH
    new = []
    for k, (o, l) in enumerate(zip(e["options"], lem)):
        if k == e["answer"]:
            new.append((tok, o, True))
            continue
        fs = {make(l, g, verb) for g in gs}
        if len(fs) != 1 or None in fs:
            continue
        f = fs.pop()
        if f == tok or any(f == x[0] for x in new):
            continue
        new.append((f, o, False))
    if len(new) < 3:
        return None
    opts = ["%s (%s)" % (accent(f), o) for f, o, _ in new]
    return opts, [x[2] for x in new].index(True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--course")
    a = ap.parse_args(argv)
    done = same = dropped = 0
    samples, lost = [], []
    for f in sorted(glob.glob(os.path.join(ROOT, a.course or "*", "*.json"))):
        j = json.load(io.open(f, encoding="utf-8"))
        exs = j.get("exercises")
        if not exs:
            continue
        out, changed = [], False
        for e in exs:
            if e.get("type") != "mc" or "___" not in (e.get("ru") or ""):
                out.append(e); continue
            r = fix(e)
            if r == "same":
                same += 1; out.append(e); continue
            changed = True
            if r is None:
                dropped += 1; lost.append((os.path.basename(f), e["ru"], e["options"], (e.get("why") or "")[:40]))
                continue
            e = dict(e, options=r[0], answer=r[1])
            done += 1; out.append(e)
            if len(samples) < 25:
                samples.append((e["ru"], e["options"], e["answer"]))
        if changed and a.apply:
            j["exercises"] = out
            io.open(f, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    for s in samples:
        print("  ", s)
    for s in lost[:40]:
        print("  dropped:", s)
    print("inflect_options: %d exercises given conjugated/declined options, %d already fine, %d dropped%s"
          % (done, same, dropped, "" if a.apply else " (report only)"))


if __name__ == "__main__":
    main()
