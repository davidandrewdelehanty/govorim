# -*- coding: utf-8 -*-
"""Everything about Russian Verbs — the conjugation half: an overview, one lesson (a chart page, then practice) for each of the sixteen
conjugation types, a module on reflexive verbs, the position verbs, and a large module on the irregular verbs of the site's own list
(src/verbs-irregular.json).  Run from the repo root:  python3 tools/courses/conj_course.py   then   merge_courses.py verbs  and  finalize_outline.py.

Nothing here writes a Russian form: the charts and notes read the OpenRussian verb table (CC BY-SA 4.0, with stress); the sentences are Tatoeba's
(CC BY 2.0 FR), the library's public-domain books' (the old course's exercises, kept) and the dictionary decides which verb and form is in each.
The explanations are the sources' own sentences (DLI Grammar Reference Book, Wikibooks, Wiktionary), set in conj_text.py."""
import collections, glob, io, json, os, random, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
os.chdir(ROOT)
import orverbs as OR
import conj_classes as CC
import conj_text as TX
import verb_notes as VN

OUT_DIR = os.path.join(ROOT, "public", "courses", "verbs")
DROPPED = os.path.join(ROOT, "public", "courses", "_dropped")
ACUTE = "́"
RUDE = re.compile(r"(ху[йияеёю]|пизд|[её]б[аеиуыл]|бля|трах|сук[аи]|жоп|говн|дерьм|шлюх|мудак|мудил|сра[лт]|ссать|секс|порн|голы[йем]|насил|минет|убий|труп|член\w* (?!клуб|партии|семьи))", re.I)
PRON = ["я", "ты", "он/она", "мы", "вы", "они"]
SETS = {1: 3, 2: 2, 3: 1, 4: 3, 5: 2, 6: 2, 7: 2, 8: 2, 9: 1, 10: 1, 11: 1, 12: 1, 13: 1, 14: 1, 15: 1, 16: 1}
IRR_SETS = {"core": 3, "motion": 2, "ava": 1, "nyat": 1, "byu": 2, "cons": 3, "stem": 2, "mut": 1, "ova": 1, "ilu": 2}
SET_SIZE = 20
NOTE_EX = {"t": "note", "text": "Exercises: sentences from Tatoeba (tatoeba.org, CC BY 2.0 FR) and from the library's public-domain books. The blank names the verb, its aspect, tense and person; the note after each answer gives every form."}

def P(text, quote=False):
    b = {"t": "p", "text": text}
    if quote: b["set"] = True
    return b
def H(t): return {"t": "h", "text": t}
def NOTE(t): return {"t": "note", "text": t}
def LIST(items): return {"t": "list", "items": items}

# ── charts ──────────────────────────────────────────────────────────────────────────────────────────────────
def fold(w): return (w or "").lower().replace("ё", "е").replace(ACUTE, "")
def bold_end(form, opts):
    plain = fold(form)
    for o in sorted(opts, key=len, reverse=True):
        if o and plain.endswith(fold(o)):
            k, i = len(fold(o)), len(form)
            while k > 0 and i > 0:
                i -= 1
                if form[i] != ACUTE: k -= 1
            return form[:i] + "**" + form[i:] + "**"
    return form
def entry(v):
    e = OR.entry(v)
    if not e: raise SystemExit("not in the OpenRussian table: " + v)
    return e
def first(ws): return ws[0] if ws else ""
def head_name(v, e):
    return e["accented"] or v
def chart(verbs, ends=None, past_ends=None, bold_opts=None, caption=None, show_ends=True):
    es = [entry(v) for v in verbs]
    pf = any(e["aspect"] == "pf." for e in es)
    head = [""] + (["ending"] if show_ends else []) + [head_name(v, e) + (" (pf.)" if e["aspect"] == "pf." else "") for v, e in zip(verbs, es)]
    rows = []
    for i in range(6):
        row = [PRON[i]]
        if show_ends: row.append("**-%s**" % ends[i].replace("/", "/-") if ends else "")
        for e in es:
            f = first(e["pres"][i]); opts = (bold_opts or [[x] for x in ends])[i] if (bold_opts or ends) else []
            row.append(bold_end(f, opts) if opts else f)
        rows.append(row)
    pl = ["past m.", "past f.", "past n.", "past pl."]; pe = past_ends or ["-л", "-ла", "-ло", "-ли"]
    for i in range(4):
        row = [pl[i]]
        if show_ends: row.append(pe[i])
        for e in es:
            f = first(e["past"][i]); row.append(bold_end(f, [pe[i].lstrip("-")]) if pe[i].startswith("-") else f)
        rows.append(row)
    cap = caption or ("Future (perfective verbs have no present tense) · past tense" if pf and all(e["aspect"] == "pf." for e in es) else "Present tense · past tense" + (" · (pf.) = perfective: these forms are the future" if pf else ""))
    return {"t": "table", "head": head, "rows": rows, "rowHeads": True, "fit": True, "caption": cap}

def table_rows(verbs, cols, head):
    """A small fit table: one row per verb, columns = indexes into the present forms ('p0'..'p5') or 'inf'."""
    rows = []
    for v in verbs:
        e = entry(v); row = []
        for c in cols:
            row.append(head_name(v, e) if c == "inf" else first(e["pres"][int(c[1:])]) if c[0] == "p" else "")
        rows.append(row)
    return {"t": "table", "head": head, "rows": rows, "rowHeads": False, "fit": True}

# ── exercises ───────────────────────────────────────────────────────────────────────────────────────────────
STATS = collections.Counter()
def make_ex(row):
    sent, form, inf = row["ru"], row["form"], row["inf"]
    pat = re.compile(r"(?<![А-Яа-яЁё])" + re.escape(form) + r"(?![А-Яа-яЁё])", re.I)
    ms = list(pat.finditer(sent))
    if len(ms) != 1: STATS["blank"] += 1; return None
    m = ms[0]
    e = {"type": "fill", "q": sent[:m.start()] + "___ (%s)" % inf + sent[m.end():], "prompt": row["en"], "answers": [form.lower()], "_note": True}
    if not VN.build(e, STATS): return None
    e.pop("_note", None)
    if not e.get("why"): STATS["no note"] += 1; return None
    e["context"] = ""; e["why"] = e["why"].replace("//", " / ")
    return e
def bucket(row):
    return (row.get("kind"), row.get("who"))
def pick(rows, n, rnd, vcap=3, used_v=None):
    """n rows with the present/future persons and past genders as even as the pool allows, at most vcap per verb."""
    used_v = used_v if used_v is not None else collections.Counter()
    cnt_b = collections.Counter(); cnt_v = collections.Counter(); out = []
    rows = rows[:]; rnd.shuffle(rows)
    while rows and len(out) < n:
        best = None
        for r in rows:
            if cnt_v[r["inf"]] >= vcap: continue
            c = cnt_b[bucket(r)] * 10 + cnt_v[r["inf"]] * 6 + used_v[r["inf"]] * 2 + (0 if len(r["ru"]) < 70 else 3) + (8 if r.get("pf") else 0)
            if best is None or c < best[0]: best = (c, r)
        if not best: break
        r = best[1]; rows.remove(r); out.append(r); cnt_b[bucket(r)] += 1; cnt_v[r["inf"]] += 1; used_v[r["inf"]] += 1
    return out
USED = set()
def practice_sets(rows, nsets, seed, size=SET_SIZE, min_size=8):
    rnd = random.Random(seed); used_v = collections.Counter(); sets = []; rows = [r for r in rows if r["ru"] not in USED]
    for _ in range(nsets):
        chosen = []
        while rows and len(chosen) < size:
            cand = pick(rows, size - len(chosen), rnd, used_v=used_v)
            if not cand: break
            for r in cand:
                rows.remove(r)
                e = make_ex(r)
                if e: chosen.append(e); USED.add(r["ru"])
            if len(chosen) < size and not rows: break
        if len(chosen) < min_size: break
        for i, e in enumerate(chosen): e["id"] = "q%d" % (i + 1)
        sets.append(chosen)
    return sets

def load_rows():
    """Every candidate sentence: {ru, en, inf, form, kind, who, cls, src}."""
    rows = []; seen = set()
    def add(r):
        key = (r["ru"], r["src"] == "irr")        # a sentence may be in a type's pool and in an irregular group's: it is used once
        if key in seen or RUDE.search(r["ru"]) or not (20 <= len(r["ru"]) <= 100): return
        seen.add(key); rows.append(r)
    # the old course's exercises first (kept): sentences from the library's books and Tatoeba, with the form restored
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "v[12]-*-practice*.json")) + glob.glob(os.path.join(OUT_DIR, "v4-sya-practice*.json"))):
        j = json.load(io.open(p, encoding="utf-8"))
        for e in j.get("exercises") or []:
            m = re.search(r"___ \(([а-яё]+(?:ся|сь)?)(?:,[^)]*)?\)", e["q"])
            if not m or not e.get("answers"): continue
            inf, ans = m.group(1), e["answers"][0]
            if (inf, VN.fold(ans)) in VN.IMPERATIVE: continue
            add({"ru": e["q"][:m.start()] + ans + e["q"][m.end():], "en": e.get("prompt", ""), "inf": inf, "form": ans, "src": "old"})
    for fn in ("conj_drills.json", "conj_irr_drills.json"):
        d = json.load(io.open(os.path.join(HERE, fn), encoding="utf-8"))
        for z, rs in d.items():
            for s, en, v, w, kind, who in rs:
                add({"ru": s, "en": en, "inf": v, "form": w, "kind": kind, "who": who, "grp": z, "src": "tatoeba" if fn == "conj_drills.json" else "irr"})
    return rows
def classify(rows):
    for r in rows:
        try: r["cls"] = CC.zclass(r["inf"])
        except Exception: r["cls"] = None
        e = OR.entry(r["inf"], r["form"]); r["pf"] = bool(e and e["aspect"] == "pf.")
        if "kind" not in r:
            got = VN.analyze(r["inf"], r["form"])
            if len(got) == 1: r["kind"], r["who"] = next(iter(got))
            else: r["kind"] = r["who"] = None
    return rows

# ── pages ────────────────────────────────────────────────────────────────────────────────────────────────────
def quote_blocks(lines, src):
    bs = [P(x, True) for x in lines]
    if bs and src: bs.append(NOTE("From the " + src + "." if not src.startswith("DLI") else src + "."))
    return bs
def type_page(k):
    s = TX.T[k]
    bold = [o.split("/") for o in s["ends"]]
    if k == 8: bold = [["у"], ["ешь"], ["ет"], ["ем"], ["ете"], ["ут"]]
    if k == 7 or k == 9: bold = [["у"], ["ешь"], ["ет"], ["ем"], ["ете"], ["ут"]]
    pe = ["-л", "-ла", "-ло", "-ли"]
    if k in (7, 8, 9): pe = ["—", "-ла", "-ло", "-ли"]
    if k == 3: pe = ["-л/—", "-ла", "-ло", "-ли"]
    bl = [{"t": "lead", "text": s["lead"]}, chart(list(s["ex"]), ends=["ю" if False else e for e in s["ends"]], past_ends=pe, bold_opts=bold)]
    bl += [H("The pattern"), LIST(s["facts"])]
    if k == 4:
        rows = []
        for ch, v in [("б → бл", "любить"), ("в → вл", "ловить"), ("м → мл", "кормить"), ("п → пл", "топить"), ("д → ж", "ходить"), ("з → ж", "возить"), ("т → ч", "платить"), ("с → ш", "просить"), ("ст → щ", "чистить")]:
            e = entry(v); rows.append([ch, head_name(v, e), first(e["pres"][0]) + " · " + first(e["pres"][1])])
        bl += [H("The я-form: the consonant that changes"), {"t": "table", "head": ["change", "verb", "я · ты"], "rows": rows, "rowHeads": False, "fit": True,
               "caption": "Present tense, first and second person singular"}]
    if k == 14:
        bl += [H("More verbs of this type"), table_rows(["начать", "занять", "понять", "взять"], ["inf", "p0", "p2"], ["verb (pf.)", "я", "он/она"])]
    if k == 5 and s.get("wikibooks"):
        bl += [H("The verbs in -еть and -ать that belong here"), P(s["wikibooks"], True), NOTE("Wikibooks, Russian — Grammar/Verbs (CC BY-SA 4.0).")]
    if s["dli"]:
        bl += [H("In the DLI Grammar Reference Book")] + quote_blocks(s["dli"], s["dli_src"])
    bl.append(NOTE("Pattern of the type: Wiktionary, Appendix:Russian verbs, type %d (CC BY-SA 4.0). Forms and stress marks: OpenRussian (CC BY-SA 4.0)." % k))
    return bl

def overview_page():
    t = TX.T
    bl = [{"t": "lead", "text": "A short tour of the Russian verb — the infinitive, the two ways of conjugating it, the past tense, aspect and the ending -ся — before the course takes the conjugation types one by one."},
          H("The infinitive and the six forms"),
          P("The Russian infinitive (such a form as \"to read\", \"to speak\", \"to know\") usually ends in **-ть**: **читать** (to read), **говорить** (to speak). In dictionaries verbs are given in the infinitive.", True),
          NOTE("DLI Grammar Reference Book, Lesson 15."),
          P("Russian has two words for 'you' like French and German, but unlike modern English. Briefly, **ты** is used informally for a single person who you know well, while **вы** is used for groups of people, or for an individual person to whom you want to show respect.", True),
          P("The infinitive almost always ends in **-ть**, and conjugating a verb is as simple as removing this **-ть** and adding the appropriate ending.", True),
          NOTE("Wikibooks, Russian — Grammar/Verbs (CC BY-SA 4.0)."),
          H("Two basic types of conjugation"),
          P("Russian verbs may be divided into two basic groups according to their personal endings in the present tense. The present tense has six forms which are used with the corresponding personal pronouns. The 1st type of conjugation is characterized by the vowel **е** (**ё** if accented): the second type is characterized by the vowel **и**.", True),
          NOTE("DLI Grammar Reference Book, Lesson 15."),
          {"t": "table", "head": ["", "я", "ты", "он", "мы", "вы", "они"], "rows": [["1st (е)", "**-ю**", "**-ешь**", "**-ет**", "**-ем**", "**-ете**", "**-ют**"], ["2nd (и)", "**-ю**", "**-ишь**", "**-ит**", "**-им**", "**-ите**", "**-ят**"]], "rowHeads": True, "fit": True,
           "caption": "The present-tense endings (after a consonant, я takes -у and они -ут or -ат)"},
          P("The present tense can only be formed using the imperfective verb. If you are using the perfective aspect to form the future, simply conjugate it as you would the imperfective aspect, and this creates the future tense.", False) if False else P("If you're using the perfective aspect to form the future, simply conjugate it as you would the imperfective aspect, and this creates the future tense.", True),
          NOTE("Wikibooks, Russian — Grammar/Verbs (CC BY-SA 4.0)."),
          H("The past tense"),
          P("To form the past tense of either aspect of a verb, remove the ending **-ть**, and add **-л**. If the subject of the verb is feminine, add **-ла**. If it is neuter, add **-ло**, and if it is plural, add **-ли**.", True),
          NOTE("Wikibooks, Russian — Grammar/Past tense (CC BY-SA 4.0)."),
          P("Thus, the past does not have special endings for each person, but shows the gender and the number.", True),
          NOTE("DLI Grammar Reference Book, Lesson 36."),
          H("Aspect"),
          P("In Russian almost every action is expressed by a pair of verbs. Such twin-verbs differ only in what we call aspect, and otherwise have the same basic meaning.", True),
          P("The imperfective aspect emphasizes the action itself. The perfective aspect places the emphasis on the result of the action.", True),
          P("The verb **написать** is called perfective and expresses a single action with emphasis on its completion (either in the past or in the future, since the present tense deals only with actions in progress).", True),
          NOTE("DLI Grammar Reference Book, Lesson 37. The Verbal Aspect lessons later in this course take it further."),
          H("Verbs in -ся"),
          P("Reflexive verbs. These verbs express an action which is directed back upon the agent or subject: *Я моюсь. Мы готовимся к экзамену.*", True),
          NOTE("DLI Grammar Reference Book, Lessons 66–67."),
          P("Note that, as in the present tense, we use **-ся** if the word ends in a consonant, and **-сь** if it ends in a vowel.", True),
          NOTE("Wikibooks, Russian — Grammar/Past tense (CC BY-SA 4.0)."),
          H("How this course goes"),
          LIST(["Each module is a **chart page** with no exercises, then **practice pages** with verbs of that type only. Each exercise names the verb, its aspect, tense and person, and after the answer the note shows every form of the verb.",
                "The types are the sixteen of Zaliznyak's classification, numbered as in Wiktionary's Appendix:Russian verbs: " + "; ".join("%d %s" % (k, TX.T[k]["inf"]) for k in range(1, 17)) + ".",
                "Reflexive verbs have a module of their own after the first two types; position verbs follow type 5; the irregular verbs of the site's own list are the large module after type 16.",
                "Then Verbal Aspect, and Verb Forms and Participles: the imperative, the conditional, the participles and the деепричастия."]),
          NOTE("Pattern of each type: Wiktionary, Appendix:Russian verbs (CC BY-SA 4.0). Forms and stress marks: OpenRussian (CC BY-SA 4.0).")]
    return bl

def reflexive_page():
    es = ["заниматься", "учиться"]
    ends = ["юсь/усь", "ешься/ишься", "ется/ится", "емся/имся", "етесь/итесь", "ются/ятся/атся"]
    bold = [["сь"], ["ся"], ["ся"], ["ся"], ["сь"], ["ся"]]
    ch = chart(es, ends=ends, past_ends=["-лся", "-лась", "-лось", "-лись"], bold_opts=bold)
    for row in ch["rows"][6:]:
        row[2:] = [bold_end(c.replace("**", ""), ["ся", "сь"]) for c in row[2:]]
    for r, n in zip(ch["rows"], ["-ю +сь", "-ешь +ся", "-ет +ся", "-ем +ся", "-ете +сь", "-ют +ся", "-л +ся", "-ла +сь", "-ло +сь", "-ли +сь"]):
        r[1] = n
    ch["caption"] = "Present tense · past tense"
    bl = [{"t": "lead", "text": "Verbs in **-ся** conjugate like the verbs they come from; **-ся** (after a consonant) or **-сь** (after a vowel) is added last."},
          ch, H("The pattern"),
          LIST(["The ending is added to the finished form: заниматься — **занимаюсь, занимаешься, занимается, занимаемся, занимаетесь, занимаются**; the past: занимался, занималась, занималось, занимались.",
                "**-ся** follows a consonant (он занимается, он занимался, они занимаются) and **-сь** follows a vowel (я занимаюсь, вы занимаетесь, она занималась).",
                "The verb under the ending can be of any type: заниматься is type 1, учиться type 4."]),
          H("What -ся means"),
          P("The suffix \"**-ся**\" with some verbs indicates action of two or more actors upon one another (reciprocal action). Thus: **встречаться** (to meet), **знакомиться** (to become acquainted), **здороваться** (to greet each other) etc.", True),
          P("The second actor (if mentioned) is always in the Instrumental case with the preposition \"**с**\": *Я не хочу встречаться с этим человеком.* Note that without \"**-ся**\" the verb **встречать** — **встретить** is used with the direct object in the Accusative case: *Вчера я встретил моего друга.* but: *Мы встретились на улице.*", True),
          P("We already know that the verbs in \"**-ся**\" may be divided into several groups. Group 1.", True),
          P("Reflexive verbs. These verbs express an action which is directed back upon the agent or subject: *Я моюсь. Мы готовимся к экзамену.* Group 2: *Наступление начинается. Урок продолжается 50 минут.* Group 3.", True),
          P("Reciprocal verbs: *Мы часто встречаемся. Он хочет с вами познакомиться.* Group 4. Verbs which never occur without the ending \"**-ся**\": *Я боюсь вашего брата. Он смеётся над вами.*", True),
          NOTE("DLI Grammar Reference Book, Lessons 66–67."),
          P("Similar to how reflexive verbs are conjugated in the present tense, you add the appropriate reflexive ending *after* forming the past tense.", True),
          NOTE("Wikibooks, Russian — Grammar/Past tense (CC BY-SA 4.0). Forms and stress marks: OpenRussian (CC BY-SA 4.0).")]
    return bl

def irr_intro(groups):
    rows = []
    for g in groups:
        types = collections.Counter(str(CC.zclass(v[0])) for v in g["verbs"])
        rows.append(["**%s**" % g["title"], str(len(g["verbs"]))])
    return [{"t": "lead", "text": "The irregular verbs of the site's own list (the Grammar tab, **Irregular Verbs**): the verbs whose forms cannot be guessed from the infinitive, in the same groups, with practice on each."},
            {"t": "table", "head": ["group in the list", "verbs"], "rows": rows, "rowHeads": False,
             "caption": "%d verbs in %d groups" % (sum(len(g["verbs"]) for g in groups), len(groups))},
            LIST(["Each lesson here is one group of the list, with the forms exactly as the list gives them, then practice with the verbs of that group and no others.",
                  "Many of these verbs also belong to one of the sixteen types: the lessons on the types teach the pattern, these lessons teach the verbs that need to be known by heart."]),
            NOTE("The list: Grammar tab → Irregular Verbs (src/verbs-irregular.json).")]
def irr_page(g):
    gid = g["id"]
    bl = [{"t": "lead", "text": "%s · %d verbs" % (g["title"], len(g["verbs"]))}]
    if gid == "core":
        bl.append(chart(["хотеть", "бежать", "есть"], show_ends=False, caption="Present tense · past tense"))
    bl += [H("The verbs"), {"t": "table", "head": ["verb", "forms"], "rows": [["**%s** — %s" % (v[0], v[1]), v[2]] for v in g["verbs"]], "rowHeads": False,
                            "caption": "As on the site's Irregular Verbs list"}]
    if gid == "core":
        bl += [H("In the DLI Grammar Reference Book"),
               P("The conjugation of this verb is irregular: in singular - \"**Е**\" type, in plural - \"**И**\" type.", True), NOTE("DLI Grammar Reference Book, Lesson 20 (хотеть)."),
               P("Verbs which have in the infinitive a consonant before **-ть** (**-ти**) or end with **-чь** have the past tense as follows: **есть** — **ел**, **ела**; **идти** — **шёл**, **шла**, **шло**, **шли**; **мочь** — **мог**, **могла**, **могло**, **могли**.", True), NOTE("DLI Grammar Reference Book, Lesson 36.")]
    if gid == "cons":
        bl += [H("In the DLI Grammar Reference Book"), P("Verbs which have in the infinitive a consonant before **-ть** (**-ти**) or end with **-чь** have the past tense as follows: **есть** — **ел**, **ела**; **идти** — **шёл**, **шла**, **шло**, **шли**; **мочь** — **мог**, **могла**, **могло**, **могли**.", True), NOTE("DLI Grammar Reference Book, Lesson 36.")]
    if gid == "ava":
        bl += [H("In the DLI Grammar Reference Book")] + quote_blocks(TX.T[13]["dli"], TX.T[13]["dli_src"])
    if gid == "ova":
        bl += [H("Type 2")]  # the pattern is on the type-2 page
        bl[-1] = NOTE("The pattern of these verbs is on the page of type 2.")
    if gid == "motion":
        bl += [H("In the DLI Grammar Reference Book"), P("This verb belongs to the 1st conjugation (characterized by the vowel **-ё-**, like **живу**, **-ёшь**, **-ёт** …).", True), NOTE("DLI Grammar Reference Book, Lesson 19 (идти).")]
    bl.append(NOTE("Forms: the site's Irregular Verbs list. Stress marks in the exercise notes: OpenRussian (CC BY-SA 4.0)."))
    return bl

# ── assembly ─────────────────────────────────────────────────────────────────────────────────────────────────
def write(sec):
    io.open(os.path.join(OUT_DIR, sec["id"] + ".json"), "w", encoding="utf-8").write(json.dumps(sec, ensure_ascii=False))
def main():
    os.makedirs(DROPPED, exist_ok=True)
    rows = classify(load_rows())
    print("rows", len(rows), collections.Counter(r["src"] for r in rows))
    bycls = collections.defaultdict(list); refl = []; irr = collections.defaultdict(list)
    for r in rows:
        if r.get("kind") is None: continue
        if r["src"] == "irr": irr[r["grp"]].append(r); continue
        if r["inf"].endswith(("ся", "сь")): refl.append(r)
        if r["cls"] in range(1, 17) and r["src"] != "irr": bycls[r["cls"]].append(r)
    outline = []; secs = {}
    def add(sec, n=None):
        secs[sec["id"]] = sec; outline.append({"id": sec["id"], "title": sec["title"], "n": len(sec.get("exercises") or [])})
    add({"id": "c00-overview", "title": "Russian verbs in a nutshell: aspect, conjugation, -ся", "blocks": overview_page(), "exercises": []})
    order = [1, 2, "refl", 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    num = 0
    for k in order:
        num += 1
        if k == "refl":
            sid = "c%02d-reflexive" % num; title = "Reflexive verbs in -ся: занимаюсь, учусь"
            add({"id": sid, "title": title, "blocks": reflexive_page(), "exercises": []})
            pool = [r for r in refl]
            sets = practice_sets(pool, 3, "refl")
        else:
            sid = "c%02d-type%d" % (num, k); title = TX.T[k]["title"]
            add({"id": sid, "title": title, "blocks": type_page(k), "exercises": []})
            pool = [r for r in bycls[k] if not r["inf"].endswith(("ся", "сь"))]
            if len(pool) < SETS[k] * SET_SIZE: pool += [r for r in bycls[k] if r["inf"].endswith(("ся", "сь"))]
            sets = practice_sets(pool, SETS[k], "type%d" % k)
        for i, ex in enumerate(sets):
            multi = len(sets) > 1
            pid = sid + "-practice" + ("-%d" % (i + 1) if i else "")
            add({"id": pid, "title": ("Practice %d: " % (i + 1) if multi else "Practice: ") + title, "blocks": [NOTE_EX], "exercises": ex})
        print(sid, "pool", len(pool), "sets", [len(s) for s in sets])
        if k == 5: outline.append("POSITION")
    # the position verbs (the old course's DLI page and its exercises, kept as they are)
    # the irregular verbs of the site's list
    groups = json.load(io.open(os.path.join(ROOT, "src", "verbs-irregular.json"), encoding="utf-8"))["groups"]
    num += 1
    add({"id": "c%02d-irregular" % num, "title": "Irregular verbs: the site's list, group by group", "blocks": irr_intro(groups), "exercises": []})
    for gi, g in enumerate(groups):
        num += 1
        sid = "c%02d-irr-%s" % (num, g["id"]); title = "Irregular verbs %d: %s" % (gi + 1, g["title"])
        add({"id": sid, "title": title, "blocks": irr_page(g), "exercises": []})
        sets = practice_sets(irr[g["id"]], IRR_SETS[g["id"]], "irr" + g["id"])
        for i, ex in enumerate(sets):
            multi = len(sets) > 1
            pid = sid + "-practice" + ("-%d" % (i + 1) if i else "")
            add({"id": pid, "title": ("Practice %d: " % (i + 1) if multi else "Practice: ") + title, "blocks": [NOTE_EX], "exercises": ex})
        print(sid, "pool", len(irr[g["id"]]), "sets", [len(s) for s in sets])
    # write: the old v1/v2/v4 files go to _dropped, the new ones in
    for p in glob.glob(os.path.join(OUT_DIR, "v[124]-*.json")) + glob.glob(os.path.join(OUT_DIR, "exam.json")):
        shutil.move(p, os.path.join(DROPPED, "verbs-" + os.path.basename(p)))
    for sec in secs.values(): write(sec)
    # the outline
    t = io.open(os.path.join(ROOT, "src", "courses-outline.js"), encoding="utf-8").read()
    cur = json.loads(t[t.index("export default ") + 15:].rstrip().rstrip(";"))
    m = [x for x in cur if x["id"] == "verbs"][0]
    old = {s["id"]: s for s in m["sections"]}
    final = []
    for o in outline:
        if o == "POSITION":
            final += [old["v3-position"], old["v3-position-practice"]] if "v3-position-practice" in old else [old["v3-position"]]
        else: final.append(o)
    m["sections"] = final
    m["title"] = "Everything about Russian Verbs"; m["short"] = "All about verbs"; m["mark"] = "Гл"; m["level"] = "Beginner"
    m["credit"] = ("Explanations: the DLI Basic Course grammar reference books (public domain), the Wikibooks Russian textbook and Wiktionary's Appendix:Russian verbs (CC BY-SA 4.0); "
                   "verb forms and stress marks: OpenRussian (CC BY-SA 4.0); sentences: Tatoeba (CC BY 2.0 FR) and the library's public-domain books; word forms analysed with the OpenCorpora dictionary (CC BY-SA 4.0)")
    m["license"] = "Public domain · CC BY-SA 4.0 · CC BY 2.0 FR"; m["licenseUrl"] = "https://creativecommons.org/licenses/by-sa/4.0/"
    io.open(os.path.join(ROOT, "src", "courses-outline.js"), "w", encoding="utf-8").write("// Written by tools/courses/build_courses.py — the courses, their sections and\n"
        "// how many exercises each has. The lessons themselves are in public/courses/.\nexport default " + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")
    print({k: v for k, v in STATS.items() if not k.startswith("amb:")})
if __name__ == "__main__":
    main()
