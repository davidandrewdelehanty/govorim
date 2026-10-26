# -*- coding: utf-8 -*-
"""Word Formation — prefixes, suffixes and roots of common Russian words.

Nothing in this course is written by us. Every statement about how a word is built, what a prefix or a suffix means,
what a word means and where it comes from is QUOTED from a documented source, and the source is named beside it:

  * the English Wiktionary (CC BY-SA 4.0): each prefix's and suffix's own entry (its senses and usage notes, with the
    entry's examples), each word's entry (its definitions, its aspect partner, and its etymology — «{{af|ru|при-|ходи́ть}}»
    is how Wiktionary records that приходи́ть is при- + ходи́ть), and each root word's «Derived terms» / «Related terms»
    lists, which are what put words into one family;
  * the English Wikipedia's «Russian grammar» § Word formation and the Russian Wikipedia's «Вид (лингвистика)»
    (both CC BY-SA 4.0);
  * Tatoeba (CC BY 2.0 FR) for every exercise sentence and its English.

Which words appear is decided by frequency (the library's own counts): common words only. A word is grouped under a
prefix, a suffix or a root only when Wiktionary's etymology for that word says so; a word is put in a thematic group
(«beginning an action», «for a while») only when Wiktionary's definition of that word says so.

    python3 tools/courses/wordform/wf_course.py          # writes public/courses/wordform/ and the outline entry
The source snapshot is wf_src.json beside this file (fetched from Wiktionary/Wikipedia/Tatoeba; see its "note").
"""
import io, json, os, re, random, sys, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import wf_text as WT

S = json.load(io.open(os.path.join(HERE, "wf_src.json"), encoding="utf-8"))
WORDS, SENTS = S["words"], S["sentences"]
OUT = os.path.join(ROOT, "public", "courses", "wordform")
ACC = re.compile("[́̀]")
COMMON = 5000          # library frequency rank: the words a module teaches
FAMILY = 15000         # … and the furthest a root family reaches
WORD_RE = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
WK = "Wiktionary"
# Items the line-by-line review flagged (wf_review_blocks.json): a word whose breakdown or family membership was disputed
# is left out altogether; a flagged sentence is not used; a word whose first definition misled is kept out of matching.
_B = json.load(io.open(os.path.join(HERE, "wf_review_blocks.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "wf_review_blocks.json")) else {}
BLOCK_W, BLOCK_S, BLOCK_M = set(_B.get("words", {})), set(_B.get("sentences", [])), set(_B.get("match", []))
NO_MC, BAD_TEXT, NO_ETYM = set(_B.get("nomc", [])), list(_B.get("text", [])), set(_B.get("noetym", []))
def clean_text(t): return t and not any(b in t for b in BAD_TEXT)
MEANING = set(_B.get("meaning", {}))          # a word whose shown definition misled: left out (a root module keeps its own root)
LINKS, FAM_GLOSS = set(_B.get("links", {})), set(_B.get("famgloss", {}))
def ok(w): return w not in BLOCK_W and w not in MEANING

def plain(w): return ACC.sub("", w or "")
def ent(w): return (WORDS.get(w) or {}).get("entries") or []
def rank(w): return (WORDS.get(w) or {}).get("rank") or 10 ** 9
def acc(w):
    e = ent(w)
    a = (e[0].get("accented") if e else None) or w
    a = re.sub(r"[\[\]{}|<>].*$", "", a).strip()
    return a if plain(a) == w or plain(a).replace("ё", "е") == w.replace("ё", "е") else w
def pos(w):
    e = ent(w); return (e[0]["pos"] if e else "").lower()
def aspect(w):
    e = ent(w); return e[0].get("aspect") if e and e[0]["pos"] == "Verb" else None
def _good_def(d):
    if "{{" in d or "}}" in d: return False
    r = WT.render(d)
    if r.count("(") != r.count(")") or "()" in r.replace(" ", "") or not re.search(r"[a-z]{3}", re.sub(r"\([^)]*\)", "", r)): return False
    return True
def defs(w):
    e = ent(w)
    return [d for d in (e[0]["defs"] if e else []) if _good_def(d)]
def homograph(w):
    """Two Wiktionary entries of one part of speech (проводи́ть «spend» / «see off»): a sentence cannot say which is meant."""
    e = (WORDS.get(w) or {}).get("entries") or []
    c = collections.Counter(x["pos"] for x in e)
    return any(n > 1 for n in c.values())
def lab(t): return re.sub(r",\s*_\s*,\s*", " ", t)
def gloss(w, n=3):
    ds = [lab(WT.render(d)).lstrip(": ").strip() for d in defs(w)[:n]]
    return "; ".join(d for d in ds if d)
def gloss1(w):
    ds = defs(w); return lab(WT.render(ds[0])).lstrip(": ").strip() if ds else ""
def af(w): return [re.sub(r"<[^>]*>", "", p) for p in (WORDS.get(w) or {}).get("af") or [] if p]
def af_plain(w): return [plain(WT.render(p)) for p in af(w)]
def built(w):
    a = [WT.render(x) for x in af(w)]
    return " + ".join(a) if len(a) >= 2 else ""
def etymology(w):
    if w in NO_ETYM: return ""
    t = (WORDS.get(w) or {}).get("etym") or ""
    if not t: return ""
    try:
        r = WT.render(t, strict=True)
        return r if clean_text(r) else ""
    except WT.Unknown:
        return ""
def cite(w): return "https://en.wiktionary.org/wiki/" + w + "#Russian"
ASP = {"pf": "perfective", "impf": "imperfective", "both": "imperfective and perfective"}

def P(text): return {"t": "p", "text": text}
def H(text): return {"t": "h", "text": text}
def NOTE(text): return {"t": "note", "text": text}
def LEAD(text): return {"t": "lead", "text": text}
def T(head, rows, caption=None):
    b = {"t": "table", "head": head, "rows": rows, "rowHeads": False}
    if caption: b["caption"] = caption
    return b

def senses(entry_text, keep=None, affix=None):
    """The numbered senses of a Wiktionary prefix/suffix entry, rendered, each with the entry's own examples under it."""
    if not entry_text: return []
    WT.AFFIX["v"] = affix
    i = entry_text.find("===Prefix"); i = i if i >= 0 else entry_text.find("===Suffix")
    body = entry_text[i:] if i >= 0 else entry_text
    j = body.find("\n====")
    body = body if j < 0 else body[:j]
    out = []
    for line in body.split("\n"):
        if line.startswith("# "):
            out.append({"text": WT.render(line[2:]), "ex": []})
        elif line.startswith("#:") and out:
            r = WT.render(line[2:])
            if r and "→" in r and clean_text(r): out[-1]["ex"].append(r)
    if keep is not None:
        out = [out[k] for k in keep if k < len(out)]
    # a sense that is only labels with no example ("(takes numeral, produces nouns)") says nothing; a flagged one is dropped
    return [o for o in out if clean_text(o["text"]) and (o["ex"] or re.search(r"[a-z]{3}", re.sub(r"\([^)]*\)", "", o["text"])))]
def usage_notes(entry_text):
    m = re.search(r"====Usage notes====\n(.*?)(?=\n====|\Z)", entry_text or "", re.S)
    if not m: return []
    paras = []
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("{|") or line.startswith("|") or line.startswith("!"): continue
        if re.match(r"^[*\s]*[:;]", line): continue
        r = WT.render(re.sub(r"^\*+\s*", "", line))
        if r and len(r) > 25 and clean_text(r) and not r.startswith(":"): paras.append(r)
    return paras
def sense_blocks(label, entry_text, keep=None):
    sv = senses(entry_text, keep, label if label.startswith("-") else label + "-")
    items = []
    for s in sv:
        txt = s["text"] + ("" if not s["ex"] else " — " + "; ".join(s["ex"][:3]))
        items.append(txt)
    return [{"t": "list", "items": items}] if items else []

# ── sentences ────────────────────────────────────────────────────────────────────────────────────────────────────
USED_SENT = set()
def sentences_for(w, n=2):
    out = []
    for ru, en, sid, eid, i, tok in SENTS.get(w, []):
        if ru in USED_SENT: continue
        toks = list(WORD_RE.finditer(ru))
        if i >= len(toks) or toks[i].group(0) != tok: continue
        if sum(1 for t in toks if t.group(0).lower() == tok.lower()) != 1: continue
        m = toks[i]
        if ru[:m.start()] + "___" + ru[m.end():] in BLOCK_S: continue
        out.append((ru[:m.start()] + "___" + ru[m.end():], en, tok, sid, eid))
        USED_SENT.add(ru)
        if len(out) >= n: break
    return out

STOP = set("to a an the of in on at by for with from up out off into onto one's oneself someone something somebody be is are was "
           "and or not no as it its this that do make get go come take have give put set (colloquial) (transitive) (intransitive) "
           "e.g. etc. also very much more some any all".split())
def content_words(w):
    """The words of Wiktionary's definitions of w, so a distractor that shares a meaning with the answer is never offered."""
    out = set()
    for d in defs(w)[:4]:
        for t in re.findall(r"[a-z']+", WT.render(d).lower()):
            if t not in STOP and len(t) > 2: out.add(t)
    return out
def mc_sentence(answer, distractors, rnd, n=2, label=""):
    """Real sentences with the word left out; the English says which word it is; the options are words of one family."""
    exs = []
    if not ok(answer) or homograph(answer) or answer in NO_MC: return exs
    keyw = content_words(answer)
    distractors = [d for d in distractors if d != answer and ok(d) and not homograph(d) and not (content_words(d) & keyw)]
    opts0 = [answer] + distractors[:3]
    if len(opts0) < 3: return exs
    for ru, en, tok, sid, eid in sentences_for(answer, n):
        opts = list(opts0); rnd.shuffle(opts)
        why = "**%s** — %s" % (tok, acc(answer))
        a = aspect(answer)
        if a in ASP: why += " (%s)" % ASP[a]
        why += ": %s." % gloss(answer, 4)
        if built(answer): why += " %s: %s." % (WK, built(answer))
        exs.append({"type": "mc", "q": en, "ru": ru, "options": [acc(o) for o in opts], "answer": opts.index(answer),
                    "why": why, "context": label})
    return exs

def match_sets(words, rnd, size=4, q="Match each word with its meaning (Wiktionary's definitions)."):
    ws = [w for w in words if gloss1(w) and ok(w) and w not in BLOCK_M and len(gloss1(w)) <= 100]
    out = []
    for i in range(0, len(ws) - size + 1, size):
        grp = ws[i:i + size]
        gl = [gloss1(w) for w in grp]
        if len(set(gl)) < len(gl): continue
        out.append({"type": "match", "q": q, "pairs": [[acc(w), g] for w, g in zip(grp, gl)],
                    "why": "From " + WK + ": " + "; ".join("%s — %s" % (acc(w), g) for w, g in zip(grp, gl)) + "."})
    return out

def word_table(ws, cols=("word", "built", "meaning")):
    rows = []
    for w in ws:
        r = []
        for c in cols:
            if c == "word": r.append("**%s**" % acc(w))
            elif c == "pos": r.append(pos(w))
            elif c == "aspect": r.append(ASP.get(aspect(w) or "", ""))
            elif c == "built": r.append(built(w) or "—")
            elif c == "meaning": r.append(gloss(w, 2))
        rows.append(r)
    head = {"word": "Word", "pos": "Part of speech", "aspect": "Aspect", "built": "Made of (Wiktionary's etymology)", "meaning": "Meaning (Wiktionary)"}
    return T([head[c] for c in cols], rows)

# ── word sets ────────────────────────────────────────────────────────────────────────────────────────────────────
def with_prefix(variants, limit=COMMON):
    vs = {v + "-" for v in variants}
    return sorted([w for w in WORDS if ok(w) and af_plain(w) and af_plain(w)[0] in vs and rank(w) <= limit and defs(w)], key=rank)
def same_base(w):
    """Words Wiktionary builds on the same base as w, with another prefix."""
    a = af_plain(w)
    if len(a) < 2: return []
    base = a[1:]
    return sorted([x for x in WORDS if x != w and af_plain(x)[1:] == base and af_plain(x) and af_plain(x)[0].endswith("-")
                   and af_plain(x)[0] != a[0] and rank(x) <= FAMILY], key=rank)
def by_def(rx, prefixes=None, posn="Verb", limit=8000):
    out = []
    for w in WORDS:
        if rank(w) > limit or not ok(w) or not af_plain(w) or not af_plain(w)[0].endswith("-"): continue
        if prefixes and af_plain(w)[0][:-1] not in prefixes: continue
        e = ent(w)
        if not e or e[0]["pos"] != posn: continue
        if any(re.search(rx, WT.render(d), re.I) for d in e[0]["defs"][:2]): out.append(w)
    return sorted(out, key=rank)

SECTIONS, OUTLINE = [], []
def add(sec_id, title, blocks, exercises, sub=None, set_size=12):
    sec = {"id": sec_id, "title": title, "blocks": blocks, "exercises": []}
    if sub: sec["sub"] = sub
    SECTIONS.append(sec); OUTLINE.append({"id": sec_id, "title": title, "n": 0})
    ex = [e for e in exercises if e]
    sets = [ex[i:i + set_size] for i in range(0, len(ex), set_size)]
    if len(sets) > 1 and len(sets[-1]) < 4:
        sets[-2] += sets[-1]; sets.pop()
    for k, s in enumerate(sets):
        pid = sec_id + "-practice" + ("-%d" % (k + 1) if k else "")
        t = ("Practice %d: " % (k + 1) if len(sets) > 1 else "Practice: ") + title
        for i, e in enumerate(s): e["id"] = "q%d" % (i + 1)
        SECTIONS.append({"id": pid, "title": t, "blocks": [NOTE("Sentences and their English: Tatoeba (tatoeba.org, CC BY 2.0 FR). "
                         "Words, meanings and how each word is built: the English Wiktionary (CC BY-SA 4.0).")], "exercises": s})
        OUTLINE.append({"id": pid, "title": t, "n": len(s)})

# ═══ 0. How Russian words are built ═════════════════════════════════════════════════════════════════════════════
def intro():
    t = S["texts"]["enwiki_word_formation"]
    first = next((x for x in t.split("\n\n") if "prefixes" in x and "{|" not in x), "")
    first = WT.render(re.sub(r"\{\{Unreferenced[^}]*\}\}", "", first)).split("For example:")[0].strip()
    rows = []
    for line in t.split("\n"):
        m = re.match(r"\|\s*(.+?)\s*\|\|\s*\{\{IPA\|[^}]*\}\}\s*\|\|\s*(.+)$", line)
        if m:
            mean = WT.render(m.group(2)).strip().strip('"“”').strip()
            if '"' in mean or "(" in mean or "process" in mean: continue      # keep only the plainly quoted glosses
            rows.append(["**" + WT.render(m.group(1)) + "**", mean])
    blocks = [LEAD("How Russian words are built: a prefix, a root, suffixes, an ending."), P(first)]
    if rows: blocks += [T(["Word", "Meaning"], rows[:12], caption="One root, мысл-, and the words built on it")]
    blocks += [NOTE("Quoted from the English Wikipedia, «Russian grammar» § Word formation (CC BY-SA 4.0)."),
               P("This course takes the commonest prefixes, suffixes and roots one at a time. For each, the lesson quotes what the "
                 "English Wiktionary says it means, then lists the common words Wiktionary builds with it, each with Wiktionary's own "
                 "account of how it is made and what it means. The practice uses real sentences from Tatoeba with their English.")]
    add("w00-intro", "How Russian words are built", blocks, [])

# ═══ 1. Prefixes, grouped by meaning ════════════════════════════════════════════════════════════════════════════
PREFIX_MODULES = [
    ("p01-in-out", "в- and вы-", [("в", ["в", "во"], [0, 1]), ("вы", ["вы"], [0, 1])]),
    ("p02-arrive-leave", "при- and у-", [("при", ["при"], [0, 1, 2, 3]), ("у", ["у"], [0, 1])]),
    ("p03-near-away", "под- and от-", [("под", ["под", "подо"], [1, 0, 2, 3, 4, 5]), ("от", ["от", "ото"], [0])]),
    ("p04-across-through", "пере- and про-", [("пере", ["пере"], [0, 1, 2, 3, 4]), ("про", ["про"], [0, 2, 3, 5, 6])]),
    ("p05-reach-around", "до- and о-, об-", [("до", ["до"], [0, 1]), ("о", ["о", "об", "обо"], [2, 3, 4, 0, 1])]),
    ("p06-up-down", "вз-, воз- and с-", [("вз", ["вз", "вс", "взо"], [0, 1]), ("воз", ["воз", "вос"], [0, 1]), ("с", ["с", "со"], [1, 2, 0])]),
    ("p07-apart-out", "раз- and из-", [("раз", ["раз", "рас", "разо"], [0, 1, 2, 3]), ("из", ["из", "ис", "изо"], [0, 1, 2])]),
    ("p08-onto-behind", "на- and за-", [("на", ["на"], [0, 1, 2]), ("за", ["за"], [0, 1, 2, 4, 5])]),
    ("p09-po", "по-", [("по", ["по"], [0, 1])]),
    ("p10-pre-pred", "пре- and пред-", [("пре", ["пре"], [0, 1]), ("пред", ["пред", "предо"], [0])]),
]
def prefix_module(mid, title, parts, rnd):
    blocks, exs, allw = [LEAD(title)], [], []
    for p, variants, keep in parts:
        entry = S["prefix"].get(p)
        blocks.append(H("%s" % ", ".join(v + "-" for v in variants)))
        blocks += sense_blocks(p, entry, keep)
        blocks.append(NOTE("The senses of the prefix, with the entry's own examples: %s, «%s-» (https://en.wiktionary.org/wiki/%s-#Russian)." % (WK, p, p)))
        ws = with_prefix(variants)[:14]
        if ws:
            blocks.append(word_table(ws))
            blocks.append(NOTE("Common words %s builds with %s, each with its etymology and definitions as %s gives them." % (WK, " / ".join(v + "-" for v in variants), WK)))
        allw += [(w, p) for w in ws]
    # practice: real sentences; the options are the same base with other prefixes
    for w, p in allw:
        if pos(w) != "verb": continue
        sib = same_base(w)
        others = [x for x in sib if aspect(x) == aspect(w)] + [x for x in sib if aspect(x) != aspect(w)]
        exs += mc_sentence(w, others, rnd, 2, "Which prefix? The English says which word it is.")
    ms = match_sets([w for w, _ in allw], rnd)
    exs = interleave(exs, ms)
    add(mid, title, blocks, exs)

def interleave(a, b):
    out, j = [], 0
    step = max(3, len(a) // max(1, len(b)) if b else 3)
    for i, x in enumerate(a):
        out.append(x)
        if b and j < len(b) and (i + 1) % step == 0: out.append(b[j]); j += 1
    return out + b[j:]

# ═══ 2. Patterns the definitions show ═══════════════════════════════════════════════════════════════════════════
INCEPTIVE = r"\b(begin|start)s? to\b|\bstart(?:s)? \w+ing\b|\bburst (?:out|into)\b|\bbreak into\b|\bbegin \w+ing\b"
WHILE = r"\(for a while\)|\bfor a while\b|\bfor a bit\b|\bfor some time\b|\(a little\)"
def theme(mid, title, quote_parts, rx, rnd, intro_text, limit=8000):
    blocks = [LEAD(title)]
    for p, keep in quote_parts:
        sv = senses(S["prefix"].get(p), keep, p + "-")
        if sv:
            blocks.append(H(p + "-"))
            blocks.append({"t": "list", "items": [s["text"] + ("" if not s["ex"] else " — " + "; ".join(s["ex"][:2])) for s in sv]})
            blocks.append(NOTE("%s, «%s-» (https://en.wiktionary.org/wiki/%s-#Russian)." % (WK, p, p)))
    ws = by_def(rx, limit=limit)
    blocks.append(P(intro_text))
    groups = collections.OrderedDict()
    for w in ws: groups.setdefault(af_plain(w)[0], []).append(w)
    for p, g in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        blocks.append(H("with " + p))
        blocks.append(word_table(g[:12]))
    blocks.append(NOTE("Every word here is one whose own definition in %s says so; its etymology is %s's." % (WK, WK)))
    exs = []
    for w in ws:
        a = af_plain(w); base = [x for x in a[1:] if not x.startswith("-")]
        dis = [b for b in base if b in WORDS] + same_base(w)
        exs += mc_sentence(w, dis, rnd, 2, "The English says which word it is.")
    exs = interleave(exs, match_sets(ws, rnd))
    add(mid, title, blocks, exs)

# ═══ 3. Suffixes ═══════════════════════════════════════════════════════════════════════════════════════════════
def pairs_with(suffixes, limit=8000):
    out = []
    for w in WORDS:
        a = af_plain(w)
        if len(a) == 2 and a[1] in suffixes and a[0] in WORDS and ok(w) and min(rank(w), rank(a[0])) <= limit:
            out.append((a[0], w))
    return sorted(out, key=lambda p: min(rank(p[0]), rank(p[1])))
def suffix_module(mid, title, sfx, rnd, kind, extra_blocks=(), limit=COMMON, fill_q=None, aspect_pair=False):
    blocks = [LEAD(title)]
    for s in sfx:
        e = S["suffix"].get(s)
        if not e: continue
        blocks.append(H(s))
        blocks += sense_blocks(s, e)
        un = usage_notes(e)
        if un: blocks += [P(x) for x in un[:3]]
        blocks.append(NOTE("%s, «%s» (https://en.wiktionary.org/wiki/%s#Russian)." % (WK, s, s)))
    blocks += list(extra_blocks)
    prs = pairs_with(set(sfx), limit)
    if aspect_pair:      # only where Wiktionary's headwords say perfective → imperfective
        def partners(w): return {plain(x) for e in ent(w) for x in (e.get("pf") or []) for x in x.split(",")}
        prs = [(a, b) for a, b in prs if aspect(a) == "pf" and aspect(b) == "impf" and a in partners(b)]
    prs = prs[:24]
    if prs:
        blocks.append(T(["From", "", "Word", "Meaning (Wiktionary)"],
                        [["**%s**" % acc(a), "→", "**%s**" % acc(b), gloss(b, 1)] for a, b in prs]))
        blocks.append(NOTE("Pairs from %s's etymologies: each right-hand word is the left-hand word + %s, as %s records it." % (WK, " / ".join(sfx), WK)))
    exs = []
    for a, b in prs:
        q = (fill_q or "%s → ___") % acc(a)
        sx = [x for x in af(b)[1:] if x.startswith("-")]
        exs.append({"type": "fill", "q": q, "answers": [b, acc(b)], "hint": (kind + " in " + plain(sx[-1])) if sx else kind,
                    "why": "**%s** — %s. %s: %s." % (acc(b), gloss(b, 1), WK, built(b))})
    exs = interleave(exs, match_sets([b for a, b in prs], rnd))
    add(mid, title, blocks, exs)

# ═══ 4. Roots: word families ═══════════════════════════════════════════════════════════════════════════════════
LINK_T = re.compile(r"\{\{(?:af|affix|surf|deverbal|back-form|backform|prefix|suffix|compound|com)\|ru\|([^{}]*)\}\}")
def etym_links(w):
    """The Russian words a word's etymology says it is made from ({{af}}, {{surf}}, {{deverbal}}, {{back-form}} …)."""
    t = (WORDS.get(w) or {}).get("etym") or ""
    t = re.sub(r"\[\[([^\]|]*)\|[^\]]*\]\]", r"\1", t)
    out = set()
    for m in LINK_T.finditer(t):
        for a in m.group(1).split("|"):
            if "=" in a: continue
            a = plain(re.sub(r"<[^>]*>|[\[\]()]", "", a)).strip()
            if a and not a.startswith("-") and not a.endswith("-"): out.add(a)
    return out
def family(root):
    r = S["roots"].get(root) or {}
    listed = set(r.get("derived", [])) | set(r.get("related", [])) | set(r.get("dv", [])) | set(S["dv"].get(root, []))
    fam = {root}
    listed = {w for w in listed if w in WORDS and rank(w) <= FAMILY and defs(w) and ok(w)}
    changed = True
    while changed:
        changed = False
        for w in sorted(listed - fam):
            parts = set(af_plain(w)) | etym_links(w)
            if w in r.get("dv", []) or w in S["dv"].get(root, []) or parts & fam or root in plain((WORDS[w].get("etym") or "")):
                fam.add(w); changed = True
    return sorted(fam, key=rank)
ROOTS = ["след", "ход", "вести", "нести", "писать", "говорить", "сказать", "дело", "ставить", "стать", "положить", "мысль",
         "знать", "видеть", "брать", "дать", "читать", "жить", "сила", "слово", "держать", "звать", "бить", "чувство",
         "бежать", "лететь", "глядеть", "рука", "пасть", "сидеть", "стоять", "лежать", "крыть", "помнить", "учить",
         "просить", "решить", "мир", "свет", "род", "образ"]
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a","b","v","g","d","e","yo","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","shch","","y","","e","yu","ya"]))
def translit(w): return "".join(TR.get(c, c) for c in w.lower())
def root_module(n, root, rnd):
    fam = family(root)
    fam = [w for w in fam if w == root or rank(w) <= FAMILY][:20]
    if len(fam) < 6: return False
    title = "The family of %s" % acc(root)
    blocks = [LEAD(title)]
    et = etymology(root)
    if et:
        blocks += [H("Where %s comes from" % acc(root)), P(et), NOTE("%s, «%s», Etymology (%s)." % (WK, root, cite(root)))]
    blocks += [H("The family"), word_table(fam, ("word", "pos", "built", "meaning")),
               NOTE("The words %s lists under «%s» as derived or related terms, which its own etymologies link to the family; "
                    "common words only." % (WK, root))]
    exs = []
    for w in fam:
        same_pos = [x for x in fam if x != w and pos(x) == pos(w)]
        exs += mc_sentence(w, same_pos, rnd, 2, "One family: which of its words fits?")
    exs = interleave(exs, match_sets(fam, rnd))
    if len(exs) < 5: return False
    add("r%02d-%s" % (n, translit(root)), title, blocks, exs)
    return True

def main():
    rnd = random.Random("wordform")
    intro()
    for mid, title, parts in PREFIX_MODULES:
        prefix_module(mid, title, parts, rnd)
    theme("t01-beginning", "«To begin doing»: за- and others", [("за", [1])], INCEPTIVE, rnd,
          "Words whose definition in Wiktionary is «to begin to …», «to start …ing» or «to burst out …»:")
    theme("t02-for-a-while", "«For a while»: по- and про-", [("по", [1]), ("про", [5])], WHILE, rnd,
          "Words whose definition in Wiktionary is «… for a while», «… for some time» or «… a little»:")
    vid = S["texts"]["ruwiki_vid_imperfectivation"]
    para = ""      # the Wikipedia paragraph misquotes Pushkin; left out
    suffix_module("s01-yvat", "-ывать and -ивать", ["-ывать", "-ивать"], rnd, "the imperfective",
                  extra_blocks=([P(para), NOTE("Russian Wikipedia, «Вид (лингвистика)» (CC BY-SA 4.0).")] if para else []),
                  limit=8000, fill_q="%s (perfective) → imperfective: ___", aspect_pair=True)
    suffix_module("s02-vat", "-вать", ["-вать"], rnd, "the imperfective", limit=8000,
                  fill_q="%s (perfective) → imperfective: ___", aspect_pair=True)
    suffix_module("s03-nut", "-нуть", ["-нуть"], rnd, "the verb", limit=8000)
    suffix_module("s04-ovat", "-овать and -евать", ["-овать", "-евать"], rnd, "the verb", limit=8000)
    suffix_module("s05-nie", "-ение and -ание", ["-ние", "-ение", "-ание"], rnd, "the noun")
    suffix_module("s06-tel", "-тель", ["-тель"], rnd, "the noun")
    suffix_module("s07-ost", "-ость", ["-ость"], rnd, "the noun")
    suffix_module("s08-stvo", "-ство and -ие", ["-ство", "-ие"], rnd, "the noun")
    suffix_module("s09-nik", "-ник, -ец, -щик, -чик", ["-ник", "-ец", "-щик", "-чик"], rnd, "the noun")
    suffix_module("s10-ka", "-ка, -ок, -ик", ["-ка", "-ок", "-ик"], rnd, "the noun")
    suffix_module("s11-ny", "-ный, -ной, -ский", ["-ный", "-ной", "-ский", "-ской"], rnd, "the adjective")
    suffix_module("s12-livy", "-ливый, -ивый, -тельный", ["-ливый", "-ивый", "-тельный"], rnd, "the adjective")
    n = 0
    for root in ROOTS:
        if root in WORDS and root_module(n + 1, root, rnd): n += 1
    write()

def write():
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "*.json")):
        os.remove(f)
    for s in SECTIONS:
        io.open(os.path.join(OUT, s["id"] + ".json"), "w", encoding="utf-8").write(json.dumps(s, ensure_ascii=False))
    op = os.path.join(ROOT, "src", "courses-outline.js"); t = io.open(op, encoding="utf-8").read(); k = t.index("export default ")
    cur = json.loads(t[k + 15:].rstrip().rstrip(";"))
    cur = [m for m in cur if m["id"] != "wordform"]
    meta = {"id": "wordform", "title": "Word Formation", "short": "Word formation", "mark": "Сл", "blurb": "",
            "credit": "Lesson text quoted from the English Wiktionary (each prefix's, suffix's and word's entry: senses, definitions, etymologies, "
                      "derived and related terms; CC BY-SA 4.0), the English Wikipedia's «Russian grammar» § Word formation and the Russian Wikipedia's "
                      "«Вид (лингвистика)» (CC BY-SA 4.0); exercises: sentences and translations from Tatoeba (CC BY 2.0 FR)",
            "creditUrl": "https://en.wiktionary.org/wiki/Appendix:Russian_prefixes", "license": "CC BY-SA 4.0 · CC BY 2.0 FR",
            "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/", "level": "Intermediate", "sections": OUTLINE}
    cur.append(meta)
    import make_exams
    make_exams.add_exams([meta])
    io.open(op, "w", encoding="utf-8").write(t[:k + 15] + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")
    print("sections", len(SECTIONS), "exercises", sum(len(s["exercises"]) for s in SECTIONS))

if __name__ == "__main__":
    main()
