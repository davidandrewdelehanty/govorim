# -*- coding: utf-8 -*-
"""Which of the sixteen conjugation types (Zaliznyak's numbering, as in Wiktionary's Appendix:Russian verbs) a verb belongs to.
The type is read from the infinitive and the dictionary's present forms; the few rare types are told by the verb's root
(prefix stripped), because their endings look like those of a common type (греть/уметь, жать/стать)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paradigms as P
M = P.M

PREFIXES = sorted("""без бес в вз вс вы воз вос до за из ис на над недо низ нис о об обо от ото пере по под подо пред предо при про раз рас с у""".split(), key=len, reverse=True)
CORE = {
    9:  {"тереть", "мереть", "переть", "вереть"},
    10: {"колоть", "пороть", "молоть", "бороть"},
    11: {"пить", "бить", "лить", "шить", "вить"},
    12: {"мыть", "крыть", "рыть", "ныть", "выть", "дуть", "греть", "петь", "брить", "гнить"},
    14: {"жать", "мять", "нять", "чать", "ять"},
    15: {"стать", "деть", "стрять"},
    16: {"жить", "плыть", "слыть"},
}
IRREGULAR = {"быть", "есть", "дать", "хотеть", "бежать", "ехать", "создать", "ёхать"}
NAMES = {1: "-ать, -ять, -еть", 2: "-овать, -евать", 3: "-нуть", 4: "-ить", 5: "-еть, -ать (и-type)", 6: "-ать (stem change)",
         7: "-ти, -зть, -сть", 8: "-чь", 9: "-ереть", 10: "-олоть, -ороть", 11: "-ить (пью)", 12: "-ыть, -уть, -еть", 13: "-авать",
         14: "-ять, -ать (нять, мять)", 15: "-ть (стану)", 16: "-ть (живу)"}

def reflexive(v): return v.endswith(("ся", "сь"))
def base(v): return v[:-2] if reflexive(v) else v
def cores(b):
    yield b
    for p in PREFIXES:
        if b.startswith(p) and len(b) - len(p) >= 3:
            yield b[len(p):]
def forms(v, pf=False):
    """(1sg, 2sg, 3sg, 3pl) of the present (future) tense, from the dictionary."""
    try: lex = P._lemma(v, "INFN").lexeme
    except Exception: return None
    out = []
    for num, per in (("sing", "1per"), ("sing", "2per"), ("sing", "3per"), ("plur", "3per")):
        got = P._pick(lex, "VERB", num, per, "pres") or P._pick(lex, "VERB", num, per, "futr")
        out.append(got[0] if got else None)
    return out
def zclass(v):
    """1..16, or 'x' for an irregular verb, or None when the verb cannot be placed."""
    b = base(v)
    if b in IRREGULAR: return "x"
    f = forms(v)
    if not f or not f[0] or not f[3]:
        return None
    if reflexive(v):
        f = [x[:-2] if x and x.endswith(("сь", "ся")) else x for x in f]
    p1, p2, p3, pl = [x.replace("ё", "е") if x else x for x in f]
    bb = b.replace("ё", "е")
    for c in cores(bb):
        for n, s in CORE.items():
            if c in s:
                if n == 14 and not p1.endswith(("му", "ну", "мну", "иму", "му")): continue
                if n == 15 and not p1.endswith("ну"): continue
                if n == 11 and not p1.endswith("ью"): continue
                if n == 12 and not p1.endswith(("ю", "ую")): continue
                return n
    if bb.endswith(("овать", "евать")) and p1.endswith(("ую", "юю")) : return 2
    if bb.endswith("авать") and p1 == bb[:-4] + "ю": return 13
    if bb.endswith("нуть") and p1 == bb[:-2]: return 3
    if bb.endswith("чь"): return 8
    if bb.endswith("ереть") and p1.endswith("ру"): return 9
    if bb.endswith(("олоть", "ороть")): return 10
    if bb.endswith(("ти", "зть")) or (bb.endswith("сть") and not bb.endswith(("есть",))): return 7
    if bb.endswith("ить") and p1.endswith("ью"): return 11
    if bb.endswith("ить"):
        return 4 if pl.endswith(("ят", "ат")) else None
    if bb.endswith(("ать", "ять", "еть")):
        if pl.endswith(("ят", "ат")): return 5
        if p1 == bb[:-2] + "ю" or p1 == bb[:-2] + "у" and bb.endswith(("ать", "ять")) and False: return 1
        if bb.endswith(("ать", "ять")) and not p1.endswith(("ю", "ую")) : return 6
        if p1 == bb[:-2] + "ю": return 1
        return 6 if bb.endswith(("ать", "ять")) else None
    if bb.endswith("ть") and p1.endswith("ву"): return 16
    return None
if __name__ == "__main__":
    import collections
    for v in sys.argv[1:]: print(v, zclass(v), forms(v))
