#!/usr/bin/env python3
"""Cut an FB2 into chapters the way the READER (src/App.jsx parseFb2 + the
marker re-split in loadBook) does, so tools can key English files, video
timings and jump points to the chapters a visitor actually sees.

Covers the ordinary paths: leaf <section>s (nested parts inherit the part
name), the untitled-scrap rule, the <subtitle> split (two distinct roman
markers, median-size guard), the nested-section median guard, and the in-text
marker re-split (splitByMarkers) that runs when the book has fewer than two
real headings. Scripture mode is not emulated.

    python3 tools/reader_chapters.py public/books/novel/asya.fb2
    python3 tools/reader_chapters.py --json out.json <fb2>

Every chapter comes back with its paragraphs and, for marker-split books, the
paragraph offset into the book as it was before the split — that is the
numbering the parallel-English files of single-section books were keyed to.
"""
import argparse, json, re, sys
import xml.etree.ElementTree as ET

MIN_MEDIAN_WORDS = 150
NOTES_DECO = r"[\s\*\-—–_.:]*"
NOTES_TITLE_RE = re.compile("^" + NOTES_DECO + r"(сноски?|примечани[ея]|комментари[ий]|notes?|footnotes?|endnotes?)" + NOTES_DECO + "$", re.I)
ROMAN_HOMO = {"Х": "X", "І": "I", "Ѵ": "V", "С": "C", "М": "M", "Д": "D"}
CHAPTER_MARK_RE = re.compile(r"^(?:глава\s+)?([ivxlcdm]+)\.?(?:\s+\S[\s\S]*)?$", re.I)


def ln(el):
    return el.tag.split("}", 1)[-1].lower()


def text_of(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def chapter_marker(txt):
    s = (txt or "").strip()
    if not s:
        return ""
    s = "".join(ROMAN_HOMO.get(c, c) for c in s)
    m = CHAPTER_MARK_RE.match(s)
    return m.group(1).upper() if m else ""


def is_chapter_marker(line):
    l = (line or "").strip()
    if not l or len(l) > 30:
        return False
    if re.match(r"^[IVXLivxl]{1,6}\.?$", l):
        return True
    if re.match(r"^\d{1,3}\.?$", l):
        return True
    if re.match(r"^(глава|часть|chapter|part)\s+([0-9]+|[ivxl]+)\.?$", l, re.I):
        return True
    if re.match(r"^(пролог|prologue|prolog|эпилог|epilogue|вступление|введение|заключение|послесловие)\.?$", l, re.I):
        return True
    return False


def paragraphs_of(sec, own_only):
    out = []

    def walk(el, in_verse):
        for c in list(el):
            tag = ln(c)
            if tag == "section":
                if not own_only:
                    walk(c, in_verse)
                continue
            if tag == "title":
                continue
            if tag in ("p", "v", "subtitle"):
                t = text_of(c)
                if not t:
                    continue
                if re.match(r"^\d+\s", t):
                    parts = re.split(r"(?<=[.!?»а-яёА-ЯЁa-zA-Z])\s+(\d+)\s+(?=[А-ЯЁ«—])", t)
                    if len(parts) > 1:
                        out.append(parts[0].strip())
                        for vi in range(1, len(parts) - 1, 2):
                            out.append((parts[vi] + " " + parts[vi + 1]).strip())
                        continue
                out.append(t)
                continue
            walk(c, in_verse or tag == "epigraph")

    walk(sec, False)
    return out


def words_in(text):
    return len(re.findall(r"\S+", text))


def median_words(chs):
    sizes = sorted(words_in(c["text"]) for c in chs)
    return sizes[len(sizes) // 2] if sizes else 0


def push_chapter(out, heading, paras):
    body = "\n\n".join(paras)
    if len(re.findall(r"[а-яёА-ЯЁ]", body)) < 5:
        return
    out.append({"heading": heading or ("Глава %d" % (len(out) + 1)), "text": body, "paras": list(paras)})


def title_of(sec):
    for c in list(sec):
        if ln(c) == "title":
            return text_of(c)
    return ""


def walk_section(sec, out, sole, ancestor):
    nested = [c for c in list(sec) if ln(c) == "section"]
    part_title = title_of(sec)
    if NOTES_TITLE_RE.match(part_title):
        return
    clean = re.sub(r"^\*+\s*|\s*\*+$", "", part_title)
    joined = (ancestor + " — " + clean) if (ancestor and clean) else (clean or ancestor or "")

    has_grandchild = any(any(ln(g) == "section" for g in list(c)) for c in nested)
    if nested and not has_grandchild:
        untitled = sum(1 for c in nested if not title_of(c))
        if untitled * 3 > len(nested):
            nested = []

    subs = [c for c in list(sec) if ln(c) == "subtitle" and chapter_marker(text_of(c))]
    distinct = {chapter_marker(text_of(c)) for c in subs}
    split = None
    if not nested and len(distinct) >= 2:
        split = []
        marker_set = set(id(c) for c in subs)
        cur = None
        cur_paras = []

        def flush():
            if cur is None:
                return
            body = "\n\n".join(cur_paras)
            if len(re.findall(r"[а-яёА-ЯЁ]", body)) >= 5:
                split.append({"heading": (joined + " — " if joined else "") + cur, "text": body, "paras": list(cur_paras)})

        for c in list(sec):
            tag = ln(c)
            if tag == "title":
                continue
            ct = text_of(c)
            if tag == "subtitle" and id(c) in marker_set:
                flush()
                cur = ct
                cur_paras = []
                continue
            if ct and cur is not None:
                cur_paras.append(ct)
        flush()
        sizes = sorted(words_in(c["text"]) for c in split)
        if len(split) < 2 or sizes[len(sizes) // 2] < MIN_MEDIAN_WORDS:
            split = None
    if split:
        out.extend(split)
        return
    if not nested:
        leaf = paragraphs_of(sec, False)
        if not part_title and not sole and words_in(" ".join(leaf)) < MIN_MEDIAN_WORDS:
            return
        push_chapter(out, joined, leaf)
        return
    sub = []
    push_chapter(sub, joined, paragraphs_of(sec, True))
    for n in nested:
        walk_section(n, sub, False, joined)
    if sub and median_words(sub) < MIN_MEDIAN_WORDS:
        push_chapter(out, joined, paragraphs_of(sec, False))
        return
    out.extend(sub)


def parse_fb2(path):
    root = ET.parse(path).getroot()
    bodies = [b for b in root if ln(b) == "body"]
    main = next((b for b in bodies if not b.get("name")), bodies[0] if bodies else None)
    sections = [c for c in list(main) if ln(c) == "section"] if main is not None else []
    chapters = []
    for s in sections:
        walk_section(s, chapters, len(sections) == 1, "")
    if not chapters and main is not None:
        paras = [text_of(p) for p in main.iter() if ln(p) == "p"]
        paras = [p for p in paras if p]
        if paras:
            chapters.append({"heading": "", "text": "\n\n".join(paras), "paras": paras})
    return chapters


def split_by_markers(chapters, keep_lead=True):
    """The reader's splitByMarkers, plus the global paragraph offset of each
    chunk in the pre-split numbering. keep_lead=True keeps the text before the
    first marker as a chapter of its own (the fix shipped with this tool)."""
    paras = []
    for c in chapters:
        paras.extend(c["paras"])
    marks = [i for i, p in enumerate(paras) if is_chapter_marker(p)]
    if len(marks) < 2:
        return None
    out = []
    bounds = []
    if keep_lead and marks[0] > 0:
        lead = "\n".join(paras[:marks[0]])
        if len(re.findall(r"[А-Яа-яЁё][А-Яа-яЁё-]*", lead)) >= MIN_MEDIAN_WORDS:
            bounds.append((None, 0, marks[0]))
    for j, m in enumerate(marks):
        end = marks[j + 1] if j + 1 < len(marks) else len(paras)
        bounds.append((m, m + 1, end))
    for m, start, end in bounds:
        chunk = paras[start:end]
        if len("\n\n".join(chunk).strip()) < 50:
            continue
        label = re.sub(r"\.+$", "", paras[m].strip()).upper() if m is not None else ""
        out.append({"heading": label, "text": "\n\n".join(chunk), "paras": chunk, "offset": start})
    return out if len(out) >= 2 else None


def reader_chapters(path, keep_lead=True):
    chs = parse_fb2(path)
    already_scripture = len(chs) > 1 and any(len(re.split(r"\s+[–—]\s+", c["heading"])) >= 3 for c in chs if c["heading"])
    real = [c for c in chs if c["heading"].strip() and not re.match(r"^глава\s+\d+$", c["heading"].strip(), re.I) and not re.match(r"^chapter\s+\d+$", c["heading"].strip(), re.I)]
    bymark = None if (already_scripture or len(real) >= 2) else split_by_markers(chs, keep_lead)
    if bymark:
        return bymark, "markers"
    if not already_scripture and len(chs) > 1:
        if not any(c["heading"].strip() for c in chs):
            paras = []
            for c in chs:
                paras.extend(c["paras"])
            return [{"heading": "", "text": "\n\n".join(paras), "paras": paras, "offset": 0}], "collapsed"
    elif len(chs) == 1:
        h = chs[0]["heading"]
        if re.match(r"^глава\s+\d+$", h.strip(), re.I) or re.match(r"^chapter\s+\d+$", h.strip(), re.I):
            h = ""
        return [{"heading": h, "text": chs[0]["text"], "paras": chs[0]["paras"], "offset": 0}], "single"
    for c in chs:
        c.setdefault("offset", None)
    return chs, "sections"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fb2")
    ap.add_argument("--json", help="write the chapter list here")
    ap.add_argument("--no-lead", action="store_true", help="emulate the old reader that dropped text before the first marker")
    a = ap.parse_args()
    chs, how = reader_chapters(a.fb2, keep_lead=not a.no_lead)
    print("%s: %d chapters (%s)" % (a.fb2, len(chs), how))
    for i, c in enumerate(chs):
        print("  %3d  %-32s paras=%-4d off=%-5s %s" % (i, c["heading"][:32], len(c["paras"]), c.get("offset"), c["paras"][0][:50] if c["paras"] else ""))
    if a.json:
        json.dump(chs, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
