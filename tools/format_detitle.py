#!/usr/bin/env python3
"""A poem whose first lines only repeat its section's title.

Wikisource prints a poem's heading as the poem's first line(s) — «Сказка / о
золотом петушке» — and the verse wrap (format_fix.py) took them in. The
reader already shows the section title, so here they go: dropped for a book
without parallel English (its indices may move), made a <subtitle> otherwise
(still one paragraph each, so the English stays aligned). A poem left with
fewer than four lines turns back into paragraphs.

    python3 tools/format_detitle.py --dry
    python3 tools/format_detitle.py
"""
import io, json, os, re, shutil, sys

ORIG = "tools/format-orig"
R = re.compile(r"(<title>((?:(?!</?title>).)*)</title>\s*)(<poem data-verse='1'>.*?</poem>|<poem data-verse=\"1\">.*?</poem>)", re.S)


def norm(x):
    return re.sub(r"[^0-9a-zа-яё]+", "", re.sub(r"<[^>]+>", "", x).lower().replace("ё", "е"))


def fix(t, keep_idx):
    n = [0]
    def one(m):
        # «Жених («Три дня купеческая дочь…»)»: the bracket quotes the first
        # line, which IS verse — compare with the name before it only.
        title = norm(re.sub(r"\s*[(\[]\s*[«\"„].*$", "", re.sub(r"<[^>]+>", " ", m.group(2)).strip()))
        poem = m.group(3)
        vs = re.findall(r"<v>(.*?)</v>", poem, re.S)
        k, acc = 0, ""
        for i in range(min(3, len(vs))):
            acc += norm(vs[i])
            if acc and title.startswith(acc):
                k = i + 1
            else:
                break
        if not k:
            return m.group(0)
        n[0] += 1
        head = "".join("<subtitle>%s</subtitle>\n" % v for v in vs[:k]) if keep_idx else ""
        rest = vs[k:]
        # drop the moved lines from the first stanza(s)
        body = poem
        for v in vs[:k]:
            body = body.replace("<v>%s</v>\n" % v, "", 1).replace("<v>%s</v>" % v, "", 1)
        body = re.sub(r"<stanza>\s*</stanza>\s*", "", body)
        if len(rest) < 4:
            body = "\n".join("<p>%s</p>" % v for v in rest)
        return m.group(1) + head + body
    return R.sub(one, t), n[0]


def main():
    a = sys.argv[1:]
    idx = json.load(io.open("private/books/index.json", encoding="utf-8"))
    hit = 0
    for b in idx:
        p = "public/books/" + str(b.get("filename", ""))
        if not p.endswith(".fb2") or not os.path.exists(p):
            continue
        try:
            t = io.open(p, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        new, n = fix(t, bool(b.get("parallelEn")))
        if not n:
            continue
        hit += 1
        print("%-36s %d poem heading(s)" % (b["slug"], n))
        if "--dry" in a:
            continue
        os.makedirs(ORIG, exist_ok=True)
        keep = os.path.join(ORIG, os.path.basename(p))
        if not os.path.exists(keep):
            shutil.copy(p, keep)
        io.open(p, "w", encoding="utf-8", newline="\n").write(new)
    print("\n%d book(s) %s" % (hit, "would change" if "--dry" in a else "changed"))


if __name__ == "__main__":
    main()
