#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Modern Russian shelf's groups — the shelf opens on these, as the
other shelves open on their authors: the rock scene, bands, musicians,
writers, the literature, cities, the news, the state.

Each book's group comes from where its title stands in the lists under
tools/modern/ (the "# …" headings there), or from its source for the news
and the official documents. Nothing is fetched. Run after an import, or on
its own:

    python3 tools/modern_groups.py      → private/books/index.json, a `group` on every Modern Russian entry
"""
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(ROOT, "private", "books", "index.json")
LISTS = os.path.join(HERE, "modern")

# A heading in a list file → the group its titles belong to.
HEADINGS = {
    "wikipedia.txt": [
        (r"scene", "Russian rock: the scene"),
        (r"\bbands?\b", "Bands"),
        (r"people", "Musicians"),
    ],
    "authors.txt": [
        (r"literature as a whole", "Russian literature"),
        (r".", "Writers"),
    ],
    "wikivoyage.txt": [(r".", "Cities")],
}
# Articles that come back under a name the lists do not use.
ALIASES = {
    "поэты пушкинской поры": "Russian literature",
    "серебряный век русской культуры": "Russian literature",
    "братья стругацкие": "Writers",
    "nautilus pompilius": "Bands",
    "сурганова, светлана яковлевна": "Musicians",
}
ORDER = ["Russian rock: the scene", "Bands", "Musicians", "Writers", "Russian literature", "Cities", "The state"]


def groups_from_lists():
    """title (as the list writes it) → group"""
    out = {}
    for fn, rules in HEADINGS.items():
        p = os.path.join(LISTS, fn)
        if not os.path.exists(p):
            continue
        group = None
        for line in io.open(p, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("#"):
                h = line.lstrip("# ").strip().lower()
                if not h or "licence" in h or "python3" in h or "one page" in h:
                    continue
                for pat, g in rules:
                    if re.search(pat, h):
                        group = g
                        break
                continue
            t = line.split("#", 1)[0].strip()
            if t and group:
                out[t] = group
    return out


def norm(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().lower().replace("ё", "е")


def assign(man, by_title):
    """`man`: the catalogue list. Sets `group` on every Modern Russian entry
    with a reason to; returns how many changed."""
    bt = {norm(k): v for k, v in by_title.items()}
    # «Цой, Виктор Робертович» in the list; the article may come back as that or as «Виктор Цой»
    bt_loose = {}
    for k, v in by_title.items():
        parts = [x.strip() for x in k.split(",")]
        if len(parts) == 2:
            bt_loose[norm(parts[1].split()[0] + " " + parts[0])] = v   # «Виктор Цой»
        bt_loose[norm(re.sub(r"\s*\(.*?\)\s*$", "", k))] = v           # «Кино (группа)» → «Кино»
    # a surname alone, for an article that came back under another form of the name
    by_surname = {}
    for k, v in by_title.items():
        if "," in k:
            by_surname.setdefault(norm(k.split(",")[0]), set()).add(v)
    n = 0
    for b in man:
        if b.get("category") != "Modern Russian":
            continue
        t = norm(b.get("title"))
        a = b.get("author") or ""
        g = None
        if "Викиновости" in a:
            g = "News"
        elif "Российская Федерация" in a:
            g = "The state"
        elif "Викигид" in a:
            g = "Cities"
        else:
            g = bt.get(t) or bt_loose.get(t) or bt_loose.get(norm(re.sub(r"\s*\(.*?\)\s*$", "", b.get("title") or "")))
            if not g and "," in (b.get("title") or ""):
                gs = by_surname.get(norm(b["title"].split(",")[0]))
                if gs and len(gs) == 1:
                    g = list(gs)[0]
            if not g:
                g = ALIASES.get(t)
            if not g:
                src = (b.get("blurbSrc") or "") + " " + (b.get("_note") or "")
                if "wikivoyage" in src:
                    g = "Cities"
                elif re.search(r"\(группа\)|рок|панк|метал", t):
                    g = "Bands"
        if g and b.get("group") != g:
            b["group"] = g
            n += 1
    return n


def main():
    man = json.load(io.open(MANIFEST, encoding="utf-8"))
    n = assign(man, groups_from_lists())
    io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(json.dumps(man, ensure_ascii=False, indent=2) + "\n")
    from collections import Counter
    c = Counter(b.get("group", "—") for b in man if b.get("category") == "Modern Russian")
    print("%d entries grouped;" % n, ", ".join("%s %d" % (k, v) for k, v in sorted(c.items(), key=lambda kv: (ORDER.index(kv[0]) if kv[0] in ORDER else 99))))


if __name__ == "__main__":
    main()
