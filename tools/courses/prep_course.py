# -*- coding: utf-8 -*-
"""Russian Prepositions, Case by Case: one module for every preposition and each case it takes, in the order
genitive, dative, accusative, instrumental, prepositional.  A module is a short lesson — the preposition, its case
and the meanings Wiktionary (CC BY-SA 4.0) gives it, with its examples — and five exercises: real sentences from
Tatoeba (CC BY 2.0 FR), found by prep_mine.py, in which the noun after the preposition is blanked and typed in its
case.  Where Tatoeba has no sentence for a rare preposition, the library's public-domain books or Russian Wikipedia
(CC BY-SA 4.0) supply it, and the exercise says which.  Explanations are the case-course engine's (OpenCorpora forms)."""
import io, json, os
from kit import *
from prep_data import MODULES, CASE_NAME, CASE_ORDER

HERE = os.path.dirname(os.path.abspath(__file__))
PER_MODULE = 5
_D = os.path.join(HERE, "prep_drills.json")
DRILLS = json.load(io.open(_D, encoding="utf-8")) if os.path.exists(_D) else {}
WK = "https://en.wiktionary.org/wiki/"


def _tidy(why):
    import tidy_explanations as t
    return t.strip_tails(t.trim_case(t.strip_tails(why or "")))


def exercises(slug):
    try:
        import hint_check as H
    except ImportError:
        H = None
    out = []
    for e in DRILLS.get(slug, []):
        e = {k: v for k, v in e.items() if k != "src"}
        e["why"] = _tidy(e.get("why"))
        e["context"] = ""
        if not e["why"] or (H is not None and H.good(e) is False):
            continue
        out.append(e)
        if len(out) == PER_MODULE:
            break
    return out


def blocks(mod):
    case = CASE_NAME[mod["case"]]
    label = mod["label"]
    bl = [P("**%s** takes the **%s** case: %s." % (label, case, mod["gloss"]))]
    if mod["senses"]:
        bl.append(L(*mod["senses"]))
    if mod["ex"]:
        bl.append(EX(*[tuple(x) for x in mod["ex"]]))
    notes = []
    if mod["wk"]:
        notes.append("Meanings and examples: Wiktionary, «%s» (en.wiktionary.org, CC BY-SA 4.0)." % mod["wk"])
    srcs = {("book" if e.get("prompt", "").count("«") and not e.get("prompt", "").startswith("Russian") else "wiki" if e.get("prompt", "").startswith("Russian Wikipedia") else "t")
            for e in DRILLS.get(mod["slug"], [])[:PER_MODULE]}
    ex_note = "Exercises: sentences and translations from Tatoeba (tatoeba.org, CC BY 2.0 FR)"
    if "book" in srcs and "wiki" in srcs:
        ex_note += ", with sentences from the library's public-domain books and from Russian Wikipedia (CC BY-SA 4.0) where Tatoeba has none"
    elif "book" in srcs:
        ex_note += ", with sentences from the library's public-domain books where Tatoeba has none"
    elif "wiki" in srcs:
        ex_note += ", with sentences from Russian Wikipedia (CC BY-SA 4.0) where Tatoeba has none"
    notes.append(ex_note + ".")
    bl.append(NOTE(" ".join(notes)))
    return bl


def sections():
    out = []
    for case in CASE_ORDER:
        for mod in [m for m in MODULES if m["case"] == case]:
            exs = exercises(mod["slug"])
            out.append(SEC("pr-%s-%s" % (case[:3], mod["slug"]), "%s + %s: %s" % (mod["label"], CASE_NAME[case], mod["gloss"]),
                           blocks(mod), exercises=exs, sub="%s · %s" % (CASE_NAME[case], mod["gloss"])))
    return out


CREDIT = ("Meanings and examples: Wiktionary (CC BY-SA 4.0); exercises: Tatoeba (CC BY 2.0 FR), with a few sentences from the library's "
          "public-domain books and Russian Wikipedia (CC BY-SA 4.0) for rare prepositions; word forms analysed with the OpenCorpora dictionary (CC BY-SA 4.0)")

COURSE_DEFS = [
    ({"id": "prepositions", "title": "Russian Prepositions, Case by Case", "short": "Prepositions", "mark": "пр",
      "blurb": "", "credit": CREDIT, "creditUrl": "https://en.wiktionary.org/wiki/Category:Russian_prepositions",
      "license": "CC BY-SA 4.0 · CC BY 2.0 FR · public domain", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/"}, sections()),
]
