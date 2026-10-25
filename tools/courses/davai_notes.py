# -*- coding: utf-8 -*-
"""Давай / Давайте exercises: name the number of people spoken to in the blank and explain the rule after the answer.
Run from the repo root:  python3 tools/courses/davai_notes.py   (idempotent)

Rule text paraphrases the DLI Grammar Reference Book (public domain): «давайте» + infinitive of the imperfective, or «давайте» +
perfective future; давай is the form for one person.  The ты/вы split is the ordinary ты/вы rule."""
import glob, io, json, re

WORD = {
    "Давай": ("let’s, to one person you call ты",
              "**Давай** — «let's», said to one person you call ты. **Давайте** is for several people, or for one person you call вы. "
              "Either way the verb is the same: a perfective verb takes its мы-form (определим), an imperfective verb takes the infinitive (Давай разговаривать!). "
              "With a perfective verb the word may be dropped: Пойдём в кино! — and -те added: Пойдёмте! (DLI Grammar Reference Book)"),
    "Давайте": ("let’s, to several people, or one person you call вы",
                "**Давайте** — «let's», said to several people, or to one person you call вы. **Давай** is for one person you call ты. "
                "Either way the verb is the same: a perfective verb takes its мы-form (уладим), an imperfective verb takes the infinitive (Давайте разговаривать!). "
                "With a perfective verb the word may be dropped: Пойдём в кино! — and -те added: Пойдёмте! (DLI Grammar Reference Book)"),
}
ONE = "Давай — one person (ты); Давайте — several people, or one person by вы; the verb is the same."
PAT = re.compile(r"^___ \(let[’']s.*?\)+(?= [а-яё])")
n = m = 0
for p in glob.glob("public/courses/*/*.json"):
    if p.endswith("/exam.json"): continue
    j = json.load(io.open(p, encoding="utf-8")); ch = False
    for e in j.get("exercises") or []:
        q = e.get("q", ""); a = (e.get("answers") or [""])[0]
        if PAT.match(q) and a in WORD:
            hint, why = WORD[a]
            v = re.search(r"\) ([а-яё]+)", q); vb = v.group(1) if v else "уладим"
            e["q"] = PAT.sub("___ (%s)" % hint, q); e["why"] = why.replace("(уладим)", "(%s)" % vb).replace("(определим)", "(%s)" % vb); ch = True; n += 1
        elif re.match(r"^Давай(?:те)?\b", q) and "___" in q and e.get("why") and ONE not in e["why"] \
                and re.search(r"1st person plural|infinitive", e["why"]) and "(let" not in q:
            e["why"] = e["why"].rstrip() + " " + ONE; ch = True; m += 1
    if ch:
        io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
print("blank-word exercises:", n, " verb-blank exercises with the rule added:", m)
