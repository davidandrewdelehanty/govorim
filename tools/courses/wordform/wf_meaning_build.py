# -*- coding: utf-8 -*-
"""Modules built from documented meanings (see wf_meanings.py): one module per group of meanings, each meaning quoted from
its dictionary with the words that dictionary lists for it. Imported by wf_course.py, which owns the shared helpers."""
import re
import wf_meanings as MN

def install(C):
    S, WORDS, WK, WT = C.S, C.WORDS, C.WK, C.WT
    B = C._B
    WRONGSENSE = set(B.get("wrongsense", {}))         # "у-|label|word": the review found the word does not carry that meaning
    NO_MEANING_Q, NO_FILL = set(B.get("nomeaning", {})), set(B.get("nofill", {}))
    RU = S["ru"]
    RUW = "Russian Wiktionary"
    plain, acc, pos, aspect, gloss, gloss1, defs, ok, rank = C.plain, C.acc, C.pos, C.aspect, C.gloss, C.gloss1, C.defs, C.ok, C.rank
    H, P, NOTE, LEAD, T = C.H, C.P, C.NOTE, C.LEAD, C.T

    def ru_url(m): return "https://ru.wiktionary.org/wiki/" + m
    def en_url(m): return "https://en.wiktionary.org/wiki/" + m + "#Russian"
    def common(w):
        # a word with several dictionary entries (пропасть «precipice» / пропасть «to vanish») cannot be glossed without guessing which
        return w in WORDS and bool(defs(w)) and ok(w) and rank(w) <= C.FAMILY and len(C.ent(w)) <= 1
    def en_entry(key): return S["suffix"].get(key) if key.startswith("-") else S["prefix"].get(key)
    def en_sense_list(key):
        e = en_entry(key)
        return C.senses(e, None, key if key.startswith("-") else key + "-") if isinstance(e, str) else []
    def trim_en(t):
        """The English Wiktionary's sense line without its grammatical framing: «(used with verbs) out (describing …)» → «out»."""
        t = re.sub(r"^\((?:used )?with verbs\)\s*", "", t)
        t2 = re.sub(r"\s*\(describing [^)]*\)\s*$", "", t).strip()
        return t2 or re.sub(r"^\((.*)\)$", r"\1", t.strip())
    def group_of(p):
        p = p.strip("-")
        for g in MN.PREFIX_GROUPS:
            if p in g: return g
        return [p]
    def is_prefix(m): return m.endswith("-") and not m.startswith("-")
    def fits(w, morph):
        """The example really carries the morpheme (the Russian Wiktionary's lists sometimes give the base word as well)."""
        m = morph.strip("-")
        return any(w.startswith(v) for v in group_of(m)) if is_prefix(morph) else m in w
    SX_RU = {"-тель": "-тель", "-щик": "-щик", "-ист": "-ист", "-ость": "-ость", "-ный": "-н", "-ной": "-н", "-ивый": "-ив",
             "-овать": "-ова", "-евать": "-ева"}
    RU_LABEL = {}
    for mod in MN.PREFIX_MEANINGS + MN.SUFFIX_MEANINGS:
        for x in mod[2]:
            if x[0] == "ru": RU_LABEL[(x[1], x[2])] = x[3]
    for x in MN.BEGIN_REFS + MN.WHILE_REFS:
        if x[0] == "ru": RU_LABEL[(x[1], x[2])] = x[3]

    def resolve(ref):
        kind = ref[0]
        if kind == "ru":
            m, n = ref[1], ref[2]
            label = ref[3] if len(ref) > 3 and ref[3] else RU_LABEL.get((m, n))
            sv = RU["senses"].get(m) or []
            if n >= len(sv) or not label: return None
            s = sv[n]
            words = list(dict.fromkeys(w for w in s["ex"] if fits(w, m)))
            bad = any(x in s["text"] for x in ("[[", "{{", "???")) or not C.clean_text(s["text"])
            return {"m": m, "label": label, "quote": "" if bad else s["text"], "src": "%s, «%s», meaning %d (%s)" % (RUW, m, n + 1, ru_url(m)),
                    "all": words, "words": [w for w in words if common(w)], "base": s.get("base", {}), "ru": True}
        if kind == "en":
            key, n = ref[1], ref[2]
            sv = en_sense_list(key)
            if n >= len(sv): return None
            s = sv[n]
            words = [plain(w) for e in s["ex"] for w in re.findall(r"→ ([А-Яа-яЁё́]+)", e)]
            m = key if key.startswith("-") else key + "-"
            base = {}
            for e in s["ex"]:
                mm = re.match(r"\s*([А-Яа-яЁё́]+)\b.*?→ ([А-Яа-яЁё́]+)", e)
                if mm: base[plain(mm.group(2))] = plain(mm.group(1))
            return {"m": m, "label": trim_en(s["text"]), "quote": s["text"], "ex": s["ex"], "src": "%s, «%s» (%s)" % (WK, m, en_url(m)),
                    "all": words, "words": [w for w in words if common(w)], "base": base}
        if kind == "t1":
            p, w = ref[1], ref[2]
            e = (WORDS.get(w) or {}).get("etym") or ""
            mm = re.search(r"\|t1=([^|}]*)", e)
            if not mm or not common(w): return None
            return {"m": p, "label": WT.render(mm.group(1)), "quote": "", "src": "%s, «%s», Etymology (%s)" % (WK, w, C.cite(w)),
                    "all": [w], "words": [w], "base": {}, "t1": True}
        if kind == "rule":
            sx = ref[1]
            sv = en_sense_list(sx)
            ru = RU["senses"].get(SX_RU.get(sx, ""), [])
            if len(sv) != 1 or len(ru) > 1:
                print("  rule refused for", sx, len(sv), len(ru)); return None
            prs = [(a, b) for a, b in C.pairs_with({sx}, C.FAMILY) if common(b)]
            return {"m": sx, "label": trim_en(sv[0]["text"]), "quote": sv[0]["text"], "ex": sv[0]["ex"],
                    "src": "%s, «%s» (%s): the suffix's only meaning there%s" % (WK, sx, en_url(sx), (" and in the %s" % RUW) if ru else ""),
                    "all": [b for a, b in prs], "words": [b for a, b in prs], "base": {b: a for a, b in prs}, "rule": True}
        return None

    _resolve = resolve
    def resolve(ref):
        r = _resolve(ref)
        if r:
            bad = {w for w in r["all"] if "%s|%s|%s" % (r["m"], r["label"], w) in WRONGSENSE}
            if bad:
                r["all"] = [w for w in r["all"] if w not in bad]; r["words"] = [w for w in r["words"] if w not in bad]
        return r

    def sense_block(r, n_table=12):
        out = [H("%s — %s" % (r["m"], r["label"]))]
        if r.get("rule"):
            out.append(P("%s gives %s one meaning: “%s”. So every word its etymologies build with %s has it." % (WK, r["m"], r["quote"], r["m"])))
        elif r.get("ru"):
            if r["quote"]:
                out.append(P("«%s» is how the %s puts this meaning of %s. Its examples: %s." % (r["quote"], RUW, r["m"], ", ".join(r["all"]))))
            else:
                out.append(P("The %s's examples for this meaning of %s: %s." % (RUW, r["m"], ", ".join(r["all"]))))
        elif r.get("t1"):
            out.append(P("%s's etymology of %s glosses its %s as “%s”." % (WK, acc(r["words"][0]), r["m"], r["label"])))
        else:
            out.append(P(r["quote"] + ((" — " + "; ".join(r["ex"][:3])) if r.get("ex") else "")))
        if r["words"]:
            out.append(C.word_table(r["words"][:n_table]))
        out.append(NOTE(r["src"] + "."))
        return out

    PFX_ALL = []
    for t, sv in RU["senses"].items():
        if is_prefix(t):
            for n in range(len(sv)): PFX_ALL.append(("ru", t, n))
    for key in S["prefix"]:
        for n in range(len(en_sense_list(key))): PFX_ALL.append(("en", key, n))
    def group_senses(morph):
        g = group_of(morph)
        out = []
        for ref in PFX_ALL:
            if ref[1].strip("-") in g:
                r = resolve(ref)
                if r: out.append(r)
        return out

    def meaning_mc(w, mine, rnd):
        """«What does у- add in уйти?» The right meaning is the one the dictionary lists the word under; the wrong ones are other
        documented meanings of the same prefix that do not list it. Skipped if the word sits under more than one meaning."""
        if mine.get("t1") or w in NO_MEANING_Q: return None
        # wrong answers come from the same dictionary only: its numbered meanings are distinct by design, while the two
        # dictionaries word the same meaning differently («away» / «удаление»)
        others = [o for o in group_senses(mine["m"]) if bool(o.get("ru")) == bool(mine.get("ru"))]
        listed = {o["label"] for o in others if w in o["all"]} | {mine["label"]}
        if len(listed) > 1: return None
        labels = [o["label"] for o in others if w not in o["all"] and o["label"] != mine["label"]]
        labels = list(dict.fromkeys(labels))
        if len(labels) < 2: return None
        rnd.shuffle(labels)
        opts = [mine["label"]] + labels[:3]; rnd.shuffle(opts)
        who = ("The " + RUW) if mine.get("ru") else WK
        return {"type": "mc", "q": "What does %s add in %s (“%s”)?" % (mine["m"], acc(w), gloss1(w)), "options": opts,
                "answer": opts.index(mine["label"]), "why": "%s lists %s under this meaning of %s. Source: %s." % (who, acc(w), mine["m"], mine["src"])}

    def meaning_module(mid, title, refs, rnd, lead=None):
        rs = [r for r in (resolve(x) for x in refs) if r and r["all"]]
        if not rs: return []
        blocks = [LEAD(title)] + ([P(lead)] if lead else [])
        for r in rs: blocks += sense_block(r)
        exs, seen = [], []
        for r in rs:
            for w in r["words"][:16]:
                if w in seen: continue
                seen.append(w)
                if is_prefix(r["m"]):
                    q = meaning_mc(w, r, rnd)
                    if q: exs.append(q)
                    if pos(w) == "verb":
                        sib = C.same_base(w)
                        sib = [x for x in sib if aspect(x) == aspect(w)] + [x for x in sib if aspect(x) != aspect(w)]
                        exs += C.mc_sentence(w, sib, rnd, 2, "Which prefix? The English says which word it is.")
                else:
                    b = r["base"].get(w)
                    # the base must also be what the English Wiktionary's etymology builds the word on
                    if b and b in WORDS and b != w and w not in NO_FILL and (b in C.af_plain(w) or b in C.etym_links(w)):
                        exs.append({"type": "fill", "q": "%s → ___" % acc(b), "answers": [w, acc(w)], "hint": "the %s in %s" % (pos(w) or "word", r["m"]),
                                    "why": "**%s** — %s. Source: %s." % (acc(w), gloss(w, 1), r["src"])})
                    same = [x for rr in rs for x in rr["words"] if x != w and pos(x) == pos(w)]
                    exs += C.mc_sentence(w, list(dict.fromkeys(same)), rnd, 1, "The English says which word it is.")
        exs = C.interleave(exs, C.match_sets(seen, rnd))
        if len(exs) < 4: return []
        C.add(mid, title, blocks, exs)
        return seen

    def motion_rows():
        t = RU["motion"]
        i = t.find('{| class="wikitable"'); body = t[i:t.find("\n|}", i)]
        rows, grp = [], ""
        for chunk in body.split('\n|- style="vertical-align: top;"')[1:]:
            chunk = chunk.strip("\n")
            if "colspan" in chunk:
                continue
            cells = re.split(r"\n\| ?", "\n" + chunk)[1:]
            if len(cells) < 2 or "<!--" in chunk: continue          # the из- row carries an editor's doubt: left out
            head = [x.strip() for x in re.split(r"<br\s*/?>", cells[0])]
            pre, meaning = head[0], (head[1] if len(head) > 1 else "")
            ex = re.split(r"<br\s*/?>", cells[1].split("\n")[0])
            if len(ex) < 2 or not meaning: continue
            en, ru = ex[0].strip(), ex[1].strip()
            mm = re.search(r"'{3}(\w+)'{3}(\w*)", ru)
            if not mm: continue
            rows.append({"prefix": pre, "meaning": meaning, "en": en, "ru": re.sub(r"'{3}(\w+)'{3}", r"**\1**", ru), "pfx": mm.group(1)})
        return rows

    def motion_module(rnd):
        rows = motion_rows()
        if not rows: return
        t = RU["motion"]
        para = next((x for x in t.split("\n\n") if x.startswith("Motion verbs combine")), "")
        para = WT.render(re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", para, flags=re.S)).strip()
        blocks = [LEAD("Prefixes on verbs of motion")] + ([P(para)] if para else [])
        blocks += [T(["Prefix", "Primary meaning", "Example", "English"], [[r["prefix"], r["meaning"], r["ru"], r["en"]] for r in rows]),
                   NOTE("The English Wikipedia, «Russian grammar» § Prefixed motion verbs (CC BY-SA 4.0), a table it adapts from "
                        "Muravyova; the examples are quoted from it.")]
        exs = []
        for r in rows:
            others = list(dict.fromkeys(x["meaning"] for x in rows if x["meaning"] != r["meaning"] and x["pfx"] != r["pfx"]))
            rnd.shuffle(others)
            opts = [r["meaning"]] + others[:3]; rnd.shuffle(opts)
            exs.append({"type": "mc", "q": "%s (%s) What does %s- add here?" % (r["ru"], r["en"], r["pfx"]), "options": opts,
                        "answer": opts.index(r["meaning"]),
                        "why": "The English Wikipedia's table of prefixed motion verbs: %s — %s." % (r["prefix"], r["meaning"])})
        C.add("m00-motion", "Prefixes on verbs of motion", blocks, exs)

    C.resolve, C.sense_block, C.meaning_module, C.motion_module = resolve, sense_block, meaning_module, motion_module
