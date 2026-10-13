#!/usr/bin/env python3
"""Turn the 500 into an import list: find each work's page on Викитека.

works.py names the works the way a reader would. add_wikisource.py needs the
exact Wikisource page title, and those vary — a poem is often filed under its
first line in «», a work may exist only as an edition subpage, an author's
name may be spelled out. This asks Wikisource once per author for every page
title carrying the author's name (the same patient, one-question-per-author
request tools/wikisource_author.py makes) and matches the works against that
list on this side.

    python3 tools/top500/resolve.py            # from the repo root, in WSL

Writes three files beside this one:
  wanted.tsv     rows for tools/add_wikisource.py; works already on the shelf
                 are written commented out with #have, so nothing is imported
                 twice
  review.txt     matches worth a glance: more than one candidate page, or a
                 page found by its first line rather than by its title
  not-found.txt  works Wikisource does not have under that name. Wikisource
                 hosts only what is public domain in Russia, so most of these
                 are either still in copyright or filed under a title this
                 could not guess; nothing here is imported

Then, after reading review.txt:
    python3 tools/add_wikisource.py --list tools/top500/wanted.tsv

WHERE THIS RUNS: it needs ru.wikisource.org, so on your machine, not in the
sandbox — the same as wikisource_author.py and add_wikisource.py.
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from works import W                                  # noqa: E402
from wikisource_author import api, slugify, bare_title  # noqa: E402

MANIFEST = "private/books/index.json"
CATEGORY = {"novel": "Novels", "novella": "Novellas", "story": "Short Stories",
            "play": "Plays", "poem": "Poetry", "fable": "Poetry", "tale": "Poetry"}
# Subpages that are a piece of a work rather than an edition of it.
PART = re.compile(r"/(Глава|Часть|Книга|Том|Действие|Явление|Песнь|Песня|Пролог|Эпилог|"
                  r"ДО|Оглавление|Содержание|Примечания|[IVXLC]+\b|\d{1,3}\b)", re.I)


def norm(s):
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[«»\"“”„'’…!?.,:;()\[\]*—–-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def titles_for(marker, cap=9000):
    """Every ns-0 page title carrying the marker, in pages of 50."""
    out, offset = [], 0
    while len(out) < cap:
        d = api({"action": "query", "list": "search", "srnamespace": 0,
                 "srsearch": 'intitle:"%s"' % marker, "srlimit": 50,
                 "sroffset": offset, "srprop": ""})
        hits = d.get("query", {}).get("search", [])
        out.extend(h["title"] for h in hits)
        cont = d.get("continue", {}).get("sroffset")
        if not hits or cont is None:
            break
        offset = cont
        time.sleep(0.4)
    return out


def paren_of(page):
    head = page.split("/")[0]
    m = re.search(r"\(([^()]*)\)\s*$", head)
    return m.group(1) if m else ""


def candidates(title, marker, pages):
    want = norm(title)
    out = []
    for p in pages:
        if marker.lower() not in paren_of(p).lower():
            continue
        if "/" in p and PART.search(p[p.index("/"):]):
            continue
        b = norm(bare_title(p))
        if not b:
            continue
        if b == want:
            score = 0
        elif b.startswith(want + " ") or want.startswith(b + " "):
            score = 2          # «Осень» vs «Осень (Октябрь уж наступил…)»
        elif (" " + want + " ") in (" " + b + " ") and len(want) > 12:
            score = 3          # a poem filed under «К *** (Я помню чудное мгновенье…)»
        else:
            continue
        if "/" in p:
            score += 1         # an edition subpage: fine, but the plain page first
        out.append((score, len(p), p))
    out.sort()
    return out


def main():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    have = {}
    slugs = {b.get("slug") for b in man}
    for b in man:
        have.setdefault(b.get("author", ""), set()).add(norm(b.get("title", "")))

    seen, works = set(), []
    for a, m, t, k in W:
        if (a, t) not in seen:
            seen.add((a, t))
            works.append((a, m, t, k))

    pages_by_marker = {}
    rows, review, missing = [], [], []
    n_have = 0
    for a, m, t, k in works:
        if norm(t) in have.get(a, set()):
            rows.append("#have\t\t%s\t%s\t%s\t" % (a, t, CATEGORY[k]))
            n_have += 1
            continue
        if m not in pages_by_marker:
            print("… %s" % m, flush=True)
            pages_by_marker[m] = titles_for(m)
        cands = candidates(t, m, pages_by_marker[m])
        if not cands:
            missing.append("%s — %s" % (a, t))
            continue
        page = cands[0][2]
        slug = slugify(t)
        if slug in slugs:
            slug = (slug + "-" + slugify(m))[:60]
        n = 2
        while slug in slugs:
            slug = "%s-%d" % (slug.rstrip("-0123456789"), n)
            n += 1
        slugs.add(slug)
        rows.append("%s\t%s\t%s\t%s\t%s\t" % (slug, page, a, t, CATEGORY[k]))
        others = [c[2] for c in cands[1:4] if c[0] <= cands[0][0] + 1]
        if cands[0][0] >= 2 or others:
            review.append("%s — %s\n    chose: %s%s" % (a, t, page,
                          "".join("\n    also:  %s" % o for o in others)))

    with open(os.path.join(HERE, "wanted.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# The top 500, resolved against Викитека by tools/top500/resolve.py.\n"
                "# Columns: slug, Wikisource page, author, title, category, blurb.\n"
                "# #have rows are already on the shelf. Read review.txt, then:\n"
                "#   python3 tools/add_wikisource.py --list tools/top500/wanted.tsv\n")
        f.write("\n".join(rows) + "\n")
    with open(os.path.join(HERE, "review.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(review) + "\n")
    with open(os.path.join(HERE, "not-found.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(missing) + "\n")
    new = len(rows) - n_have
    print("\n%d works: %d already on the shelf, %d to import, %d not on Wikisource, %d to review"
          % (len(works), n_have, new, len(missing), len(review)))


if __name__ == "__main__":
    main()
