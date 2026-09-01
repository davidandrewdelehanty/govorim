#!/usr/bin/env python3
"""Pair one English chapter (plain text) to one Russian chapter's paragraphs.

Shape-based: paragraphs are coded dialogue/narration, sequence-matched, and
inside fuzzy stretches distributed by cumulative word share. EN paragraphs
merged into a slot are joined with blank lines. Writes {ru_index: en_text}.
"""
import difflib, json, re

def code(paras, dialog_re):
    return "".join("d" if dialog_re.match(p.strip()) else ("s" if len(p.split())<8 else "n") for p in paras)

RU_D = re.compile(r"^[-—–]")
EN_D = re.compile(r"^[“\"']")

def pair(ru, en):
    a, b = code(ru, RU_D), code(en, EN_D)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = {}
    def put(i, txt):
        if not txt.strip(): return
        out[i] = (out[i] + "\n\n" + txt) if i in out else txt
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                put(i1 + k, en[j1 + k])
        elif tag in ("replace",):
            rus, ens = list(range(i1, i2)), list(range(j1, j2))
            if not rus:
                if i1 > 0:
                    for j in ens: put(i1 - 1, en[j])
                continue
            # distribute EN paras over RU paras by word share
            rw = [max(1, len(ru[i].split())) for i in rus]
            tot = sum(rw); acc = 0; bounds = []
            for w in rw:
                acc += w; bounds.append(acc / tot)
            ew = [max(1, len(en[j].split())) for j in ens]
            etot = sum(ew); eacc = 0
            ri = 0
            for j, w in zip(ens, ew):
                mid = (eacc + w / 2) / etot
                while ri < len(rus) - 1 and mid > bounds[ri]:
                    ri += 1
                put(rus[ri], en[j])
                eacc += w
        elif tag == "delete":
            pass          # RU paragraphs left without EN
        elif tag == "insert":
            if i1 > 0:
                for j in range(j1, j2): put(i1 - 1, en[j])
    return out

def paras_from_text(text):
    """Blank-line-separated hard-wrapped plaintext -> unwrapped paragraphs."""
    out, cur = [], []
    for l in text.splitlines():
        if not l.strip():
            if cur: out.append(re.sub(r"\s+", " ", " ".join(cur)).strip()); cur = []
        else:
            cur.append(l.strip())
    if cur: out.append(re.sub(r"\s+", " ", " ".join(cur)).strip())
    return [p for p in out if p]

def pair_prop(ru, en):
    """Monotonic proportional pairing by cumulative word share (order-preserving)."""
    out = {}
    rw = [max(1, len(p.split())) for p in ru]
    tot = sum(rw); acc = 0; bounds = []
    for w in rw:
        acc += w; bounds.append(acc / tot)
    ew = [max(1, len(p.split())) for p in en]
    etot = sum(ew); eacc = 0; ri = 0
    for p, w in zip(en, ew):
        mid = (eacc + w / 2) / etot
        while ri < len(ru) - 1 and mid > bounds[ri]:
            ri += 1
        out[ri] = (out[ri] + "\n\n" + p) if ri in out else p
        eacc += w
    return out
