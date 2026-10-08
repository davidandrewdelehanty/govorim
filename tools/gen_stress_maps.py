#!/usr/bin/env python3
"""Build per-book stress-mark sidecars for the reader's "a-acute Stress" toggle.

For every book in the catalogue, collects the Russian words that occur in its
text and looks each up in tools/data/stress-dict.json.gz (built by
tools/build_stress_dict.py). That dictionary holds only words whose stress is
certain however they are printed: no homographs, no word with a ё relative
(«слезы» may be слёзы), and only where two independent sources agree. Unknown
words are simply absent; a wrong stress mark teaches a learner a wrong word,
and no mark is always better than that.

One more guard here, per book, because the dictionary cannot see it: a word
the book uses as a NAME. «Мила» is мила́ as an adjective and Ми́ла as a girl,
and the reader marks by spelling, not by sense. So any word that appears
capitalised in the middle of a sentence anywhere in the book is left unmarked
throughout it.

Output: public/books/stress/<fb2-basename>.json  mapping
    lowercase word -> index of the stressed vowel in that word
The app inserts U+0301 after that index at render time — display only.

    python3 tools/gen_stress_maps.py              # missing, or older than the dictionary
    python3 tools/gen_stress_maps.py --all        # rebuild every sidecar
"""
import gzip, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "tools", "data", "stress-dict.json.gz")
OUT = os.path.join(ROOT, "public", "books", "stress")
STEM_RE = re.compile(r"\.(fb2\.zip|epub|fb2|txt|x?html?)$", re.I)
WORD_RE = re.compile(r"[А-Яа-яЁё]+")
# What may stand between a sentence end and the next sentence's first word.
OPENERS = set(" \t «»\"„“”'(—–-*[")
ENDS = set(".!?…")


def read_text(path):
    """FB2 text, honouring the encoding its XML declaration names (four books
    are windows-1251), with the binary blobs and the description dropped and
    one paragraph per line."""
    raw = open(path, "rb").read()
    m = re.search(rb'encoding=["\']([\w-]+)["\']', raw[:400])
    enc = m.group(1).decode("ascii") if m else "utf-8"
    try:
        t = raw.decode(enc, errors="replace")
    except LookupError:
        t = raw.decode("utf-8", errors="replace")
    t = re.sub(r"<binary[\s\S]*?</binary>", " ", t)
    t = re.sub(r"<description[\s\S]*?</description>", " ", t)
    t = re.sub(r"</(p|v|subtitle|title|text-author|stanza|section|epigraph|cite)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    for a, b in (("&nbsp;", " "), ("&laquo;", "«"), ("&raquo;", "»"), ("&mdash;", "—"),
                 ("&ndash;", "–"), ("&quot;", '"'), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">")):
        t = t.replace(a, b)
    return t


def names_in(text):
    """Lowercased words that appear capitalised mid-sentence somewhere."""
    out = set()
    for line in text.split("\n"):
        for m in WORD_RE.finditer(line):
            w = m.group(0)
            if not w[0].isupper() or w.isupper() and len(w) > 1:
                continue
            j = m.start() - 1
            while j >= 0 and line[j] in OPENERS:
                j -= 1
            if j < 0 or line[j] in ENDS:
                continue                     # paragraph or sentence start
            out.add(w.lower())
    return out


def main():
    rebuild = "--all" in sys.argv
    stress = json.load(gzip.open(DICT, "rt", encoding="utf-8"))
    dict_time = os.path.getmtime(DICT)
    manifest = json.load(io.open(os.path.join(ROOT, "private", "books", "index.json"),
                                 encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    done = skipped = missing = 0
    for e in manifest:
        fn = e.get("filename")
        if not fn or not fn.lower().endswith(".fb2"):
            continue
        stem = STEM_RE.sub("", os.path.basename(fn))
        dest = os.path.join(OUT, stem + ".json")
        # A sidecar older than the dictionary was built from the old one.
        if os.path.exists(dest) and not rebuild and os.path.getmtime(dest) > dict_time:
            skipped += 1
            continue
        path = next((p for p in (os.path.join(ROOT, t, "books", fn) for t in ("public", "private"))
                     if os.path.exists(p)), None)
        if not path:
            print("  missing, skipped:", fn)
            missing += 1
            continue
        text = read_text(path)
        words = set(w.lower() for w in WORD_RE.findall(text))
        names = names_in(text)
        m = {w: stress[w] for w in words if w in stress and w not in names}
        tmp = dest + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        os.replace(tmp, dest)
        done += 1
        print("  %-52s %6d marked / %6d unique / %4d name-like left out"
              % (stem[:52], len(m), len(words), len(names & set(stress))), flush=True)
    print("done: %d written, %d already had one%s"
          % (done, skipped, (", %d missing files" % missing) if missing else ""))


if __name__ == "__main__":
    main()
