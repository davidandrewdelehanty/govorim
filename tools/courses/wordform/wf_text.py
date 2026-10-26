# Rendering Wiktionary wikitext the way Wiktionary displays it (no rewording): templates → their displayed text.
import re
ACC = re.compile("[́̀]")
LANG = {"orv": "Old East Slavic", "sla-pro": "Proto-Slavic", "ine-pro": "Proto-Indo-European", "ine-bsl-pro": "Proto-Balto-Slavic",
        "cu": "Old Church Slavonic", "zle-ort": "Old Ruthenian", "grc": "Ancient Greek", "la": "Latin", "en": "English", "de": "German",
        "fr": "French", "pl": "Polish", "cs": "Czech", "uk": "Ukrainian", "be": "Belarusian", "bg": "Bulgarian", "sh": "Serbo-Croatian",
        "sl": "Slovene", "mk": "Macedonian", "sk": "Slovak", "lt": "Lithuanian", "lv": "Latvian", "sa": "Sanskrit", "fa": "Persian",
        "got": "Gothic", "gem-pro": "Proto-Germanic", "ang": "Old English", "non": "Old Norse", "it": "Italian", "es": "Spanish",
        "nl": "Dutch", "hsb": "Upper Sorbian", "dsb": "Lower Sorbian", "csb": "Kashubian", "pox": "Polabian", "sga": "Old Irish",
        "hy": "Armenian", "xcl": "Old Armenian", "el": "Greek", "ro": "Romanian", "sv": "Swedish", "da": "Danish", "ru": "Russian",
        "ine-bsl-pro": "Proto-Balto-Slavic", "zls-chu": "Church Slavonic", "chu": "Church Slavonic", "orv-ort": "Old Ruthenian",
        "ira-pro": "Proto-Iranian", "iir-pro": "Proto-Indo-Iranian", "ae": "Avestan", "txb": "Tocharian B", "hit": "Hittite",
        "prg": "Old Prussian", "ku": "Kurdish", "tr": "Turkish", "ota": "Ottoman Turkish", "trk-pro": "Proto-Turkic", "ar": "Arabic"}
def args(body):
    out, depth, cur, i = [], 0, "", 0
    while i < len(body):
        two = body[i:i+2]
        if two in ("{{", "[["): depth += 1; cur += two; i += 2; continue
        if two in ("}}", "]]"): depth -= 1; cur += two; i += 2; continue
        if body[i] == "|" and depth == 0: out.append(cur); cur = ""; i += 1; continue
        cur += body[i]; i += 1
    out.append(cur); return out
def split(a):
    pos, kw = [], {}
    for x in a:
        m = re.match(r"^\s*([a-z]+\d*)\s*=(.*)$", x, re.S)
        if m: kw[m.group(1)] = m.group(2).strip()
        else: pos.append(x.strip())
    return pos, kw
class Unknown(Exception): pass
AFFIX = {"v": None}
def term(lang, word, alt, gloss, kw):
    w = re.sub(r"<[^>]*>", "", (alt or word or ""))
    g = kw.get("t") or kw.get("gloss") or gloss or ""
    tr = kw.get("tr")
    s = w + (" (" + tr + ")" if tr else "")
    if g: s += " (“" + render(g) + "”)"
    return s
def tmpl(a, strict):
    name = a[0].strip(); pos, kw = split(a[1:])
    if name in ("root", "etymon", "ety", "dercat", "etymid", "rfe", "attention", "C", "c", "top2", "bottom", "der-top", "der-bottom", "wp", "R:ru:Vasmer", "nb...", "senseid"): return ""
    if name in ("inh", "inh+", "der", "der+", "bor", "bor+", "lbor", "slbor", "uder", "cal", "calque", "inh-lite"):
        lang = pos[1] if len(pos) > 1 else ""
        if lang not in LANG:
            if strict: raise Unknown(lang)
            return ""
        lead = {"inh+": "Inherited from ", "der+": "Derived from ", "bor+": "Borrowed from "}.get(name, "")
        g = lambda i: pos[i] if len(pos) > i else ""
        return lead + LANG[lang] + " " + term(lang, g(2), g(3), g(4), kw)
    if name in ("cog", "noncog", "ncog", "m", "m+", "l", "mention", "link"):
        if name in ("m", "l", "mention", "link"):
            lang = pos[0] if pos else ""
            g = lambda i: pos[i] if len(pos) > i else ""
            t = term(lang, g(1), g(2), g(3), kw)
            return t if lang == "ru" else ((LANG[lang] + " " + t) if lang in LANG and name == "m+" else t)
        lang = pos[0] if pos else ""
        if lang not in LANG:
            if strict: raise Unknown(lang)
            return ""
        g = lambda i: pos[i] if len(pos) > i else ""
        return LANG[lang] + " " + term(lang, g(1), g(2), g(3), kw)
    if name in ("af", "affix", "prefix", "suffix", "compound", "com", "pre", "suf"):
        parts = [p for p in pos[1:] if p]
        glosses = [kw.get("t%d" % (i + 1)) for i in range(len(parts))]
        return " + ".join(p + (" (“" + g + "”)" if g else "") for p, g in zip(parts, glosses))
    if name in ("gloss", "gl"): return "(" + render(pos[0]) + ")" if pos else ""
    if name in ("q", "qualifier", "i", "qq"): return "(" + ", ".join(render(p) for p in pos) + ")"
    if name in ("lb", "lbl", "label"): return "(" + ", ".join(p for p in pos[1:] if p not in ("_",)) .replace(", _,", "") + ")"
    if name in ("n-g", "ng", "non-gloss"): return render(pos[0]) if pos else ""
    if name in ("w", "W"): return render(kw.get("2") or (pos[1] if len(pos) > 1 else pos[0] if pos else ""))
    if name in ("glossary",): return pos[-1] if pos else ""
    if name in ("lang",): return pos[1] if len(pos) > 1 else ""
    if name in ("taxlink", "vern"): return pos[0] if pos else ""
    if name in ("sense", "s"): return "(" + render(pos[0]) + "):" if pos else ""
    if name in ("prefex", "sufex"):
        # {{prefex|ru|[affix]|part|…|result|tN=…}}: Wiktionary shows «affix + part (“gloss”) → result (“gloss”)»; with no affix
        # given, the entry's own affix is the one implied (passed in as AFFIX by the caller).
        parts = pos[1:]
        gl = lambda i: kw.get("t%d" % i) or kw.get("gloss%d" % i)
        shown = []
        for i, x in enumerate(parts, 1):
            x = x.lstrip("!")
            shown.append(x + (" (“" + render(gl(i)) + "”)" if gl(i) else ""))
        if not shown: return ""
        res = shown[-1]; srcs = shown[:-1]
        aff = AFFIX.get("v")
        first = parts[0].lstrip("!") if parts else ""
        if aff and not (first.endswith("-") or first.startswith("-") and name == "sufex"):
            srcs = [aff] + srcs if name == "prefex" else srcs + [aff]
        return " + ".join(srcs) + " → " + res
    if name in ("alternative form of", "alt form"): return "alternative form of " + (pos[1] if len(pos) > 1 else "")
    if strict: raise Unknown(name)
    return ""
def render(s, strict=False):
    s = s or ""
    for _ in range(6):
        m = None
        # innermost template first
        i = s.rfind("{{")
        if i < 0: break
        j = s.find("}}", i)
        if j < 0: break
        body = s[i+2:j]
        rep = tmpl(args(body), strict)
        s = s[:i] + rep + s[j+2:]
    while "{{" in s:
        i = s.rfind("{{"); j = s.find("}}", i)
        if j < 0: break
        s = s[:i] + tmpl(args(s[i+2:j]), strict) + s[j+2:]
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"\.\.+$", ".", s)
    return s
