#!/usr/bin/env python3
"""Look for books whose text will read strangely in the reader.

Checks every chapter (as the reader cuts it, via reader_chapters.py) for:
  verse      a run of short lines that is a poem laid out as prose paragraphs
  toc        a table of contents left in the text («Глава I … Глава II …»)
  heading    a chapter heading left inside the text as an ordinary paragraph
  junk       Wikisource/transcription clutter: [12], {{…}}, «Редакции», «Источник:», ←/→, page numbers
  wall       a paragraph so long the paragraph breaks were evidently lost
  tiny/huge  a chapter with almost nothing in it, or a whole book in one chapter
  dupe       the chapter title repeated as its first paragraph

    python3 tools/format_audit.py --category Translations
    python3 tools/format_audit.py --only carroll-alice
    python3 tools/format_audit.py --all > tools/format_audit.txt
"""
import io, json, re, sys
sys.path.insert(0, "tools")
from reader_chapters import reader_chapters

END = re.compile(r"[.!?…»”\"):;]$")
HEADLIKE = re.compile(r"^(глава|часть|книга|том|chapter)\s+([ivxlc\d]+|[а-яё]+)\.?\s*$|^[IVXLC]{1,6}\.?$", re.I)
TOCLINE = re.compile(r"^((глава|часть)\s+)?[IVXLC\d]{1,6}\.\s+\S.{0,70}$", re.I)
JUNK = [
    (re.compile(r"\[\d{1,3}\]"), "footnote mark [n]"),
    (re.compile(r"\{\{|\}\}"), "wiki template"),
    (re.compile(r"^(Редакции|Переводы|Источник:|Ссылки|См\. также)\b"), "wikisource list"),
    (re.compile(r"[←→]"), "nav arrow"),
    (re.compile(r"^\s*[-—]?\s*\d{1,4}\s*[-—]?\s*$"), "bare page number"),
    (re.compile(r"&[a-z]+;"), "html entity"),
    (re.compile(r"\bОГЛАВЛЕНИЕ\b|^Оглавление$|^Содержание$"), "contents title"),
]


def audit(path):
    chs, how = reader_chapters(path)
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    in_verse = set(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", v)).strip() for v in re.findall(r"<v>(.*?)</v>", raw, re.S))
    issues = []
    total = sum(len(c["paras"]) for c in chs)
    if len(chs) == 1 and total > 600:
        issues.append(("huge", 0, "one chapter of %d paragraphs" % total))
    for ci, c in enumerate(chs):
        P = c["paras"]
        h = (c["heading"] or "").split(" — ")[-1].strip()
        if 0 < len(P) <= 2 and len(chs) > 1 and sum(len(p) for p in P) < 200:
            issues.append(("tiny", ci, "%r has %d short paragraph(s)" % (c["heading"][:40], len(P))))
        if P and h and P[0].strip(" .").lower() == h.strip(" .").lower():
            issues.append(("dupe", ci, "first paragraph repeats the title %r" % h[:40]))
        # verse as prose
        i = 0
        while i < len(P):
            j = i
            while j < len(P) and len(P[j]) < 75 and P[j] not in in_verse and not P[j].lstrip().startswith(("—", "–", "-")):
                j += 1
            run = P[i:j]
            if len(run) >= 5 and sum(1 for x in run if not END.search(x.strip())) >= len(run) * 0.4:
                issues.append(("verse", ci, "%d short lines from ¶%d: %r" % (len(run), i, " / ".join(run[:3])[:90])))
            i = max(j, i + 1)
        # toc
        toc = [k for k, p in enumerate(P) if TOCLINE.match(p.strip())]
        if len(toc) >= 4 and toc[-1] - toc[0] <= len(toc) + 2:
            issues.append(("toc", ci, "%d contents-like lines from ¶%d: %r" % (len(toc), toc[0], P[toc[0]][:60])))
        for k, p in enumerate(P):
            s = p.strip()
            if HEADLIKE.match(s) and k > 0 and not re.match(r"^Том\s+[а-яё]", s):
                issues.append(("heading", ci, "¶%d %r" % (k, s[:40])))
            for rx, what in JUNK:
                if rx.search(s):
                    issues.append(("junk", ci, "¶%d %s: %r" % (k, what, s[:60])))
                    break
            if len(s) > 9000:
                issues.append(("wall", ci, "¶%d is %d chars" % (k, len(s))))
    return chs, issues


def main():
    a = sys.argv[1:]
    idx = json.load(io.open("private/books/index.json", encoding="utf-8"))
    if "--only" in a:
        books = [b for b in idx if b.get("slug") in a[a.index("--only") + 1:]]
    elif "--category" in a:
        cat = a[a.index("--category") + 1]
        books = [b for b in idx if b.get("category") == cat]
    else:
        books = [b for b in idx if b.get("filename", "").endswith(".fb2")]
    summary = {}
    for b in books:
        try:
            chs, issues = audit("public/books/" + b["filename"])
        except Exception as e:
            print("!! %-30s %s" % (b.get("slug"), e)); continue
        if not issues:
            continue
        kinds = {}
        for k, _, _ in issues:
            kinds[k] = kinds.get(k, 0) + 1
        summary[b.get("slug")] = kinds
        print("== %s  (%s)  %s" % (b.get("slug"), b.get("title"), " ".join("%s:%d" % kv for kv in sorted(kinds.items()))))
        shown = {}
        for k, ci, msg in issues:
            shown[k] = shown.get(k, 0) + 1
            if shown[k] <= 3:
                print("   %-7s ch%-3d %s" % (k, ci + 1, msg))
    print("\n%d of %d books flagged" % (len(summary), len(books)))


if __name__ == "__main__":
    main()
