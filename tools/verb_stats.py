#!/usr/bin/env python3
"""How often every Russian verb appears in the library, and sentences from the
library that use it — for the Grammar tab's verb lists, the conjugation
window, the define popup and the vocabulary review.

Every word of every Russian book (the catalogue's non-English entries; the
same text counted once when it sits in two collections) is analysed with
pymorphy3. A verb counts with all its forms: the finite forms, the
infinitive, and its participles and gerunds (читающий, прочитав → читать).
Reflexives are their own verbs (учить, учиться).

Writes public/vocab/verbs/:
  index.json   totals; the 5,000 commonest verbs as [lemma, count] in rank
               order; the irregular-verb list's counts; an English gloss for
               the top verbs where the frequency deck has one; the books the
               example sentences come from
  <shard>.json per verb: count, rank, its commonest forms with their counts,
               and example sentences from the library (up to 12 for the
               commonest 1,500 verbs and the irregular list, 4 for the rest seen 40+ times), each
               [sentence, form used, book number]
Shards use the same two-letter names as public/lemmas (lib/lemmatable.js).

    pip3 install --break-system-packages pymorphy3     # if not already there
    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/verb_stats.py
"""
import collections, glob, hashlib, html, io, json, os, random, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
try:
    import pymorphy3
except Exception:
    print("Needs pymorphy3:  pip3 install --break-system-packages pymorphy3"); sys.exit(1)

OUT = "public/vocab/verbs"
ALPH = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
CODE = "0123456789abcdefghijklmnopqrstuvw"
WORD = re.compile(r"[а-яё]+")
SENT = re.compile(r"(?<=[.!?…])[»\"”)]*\s+(?=[«\"“—–-]?\s*[А-ЯЁ])")
GOOD_START = re.compile(r"^[«\"“—–-]?\s*[А-ЯЁ]")
random.seed(7)


def shard_of(w):
    k = "".join(CODE[ALPH.index(c)] if c in ALPH else "_" for c in w[:2])
    return k if len(k) == 2 else k + "_"


def paragraphs(path):
    raw = open(path, "rb").read()
    m = re.search(rb'encoding="([^"]+)"', raw[:200])
    enc = (m.group(1).decode() if m else "utf-8")
    try:
        t = raw.decode(enc, errors="replace")
    except LookupError:
        t = raw.decode("utf-8", errors="replace")
    t = re.sub(r"(?s)<binary\b.*?</binary>", " ", t)
    t = re.sub(r"(?s)<description\b.*?</description>", " ", t)
    for m in re.finditer(r"(?s)<(p|v)\b[^>]*>(.*?)</\1>", t):
        s = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).replace("́", "").replace("\xa0", " ")
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            yield s


def good_sentence(s):
    if not (28 <= len(s) <= 170) or not GOOD_START.match(s):
        return False
    if re.search(r"[A-Za-z\[\]{}*<>|_#=@]|\d{3,}", s):
        return False
    if len(s.split()) < 4 or s.count("…") > 1:
        return False
    return s[-1] in ".!?…»\"”"


def main():
    t0 = time.time()
    idx = json.load(io.open("private/books/index.json", encoding="utf-8"))
    books = [b for b in idx if b.get("lang") != "en" and b.get("filename")
             and os.path.exists(os.path.join("public/books", b["filename"]))]
    if os.environ.get("VERB_TEST"):
        books = books[:int(os.environ["VERB_TEST"])]
        global OUT
        OUT = "/tmp/verbs-test"
    m = pymorphy3.MorphAnalyzer()
    cache = {}

    # Not verbs, whatever the analyser guesses: the halves of кто-нибудь,
    # что-либо, скажи-ка; and «есть», which in the library means "there is"
    # far more often than "to eat", so it counts for быть.
    NOT_VERB = {"нибудь", "либо", "то", "ка", "таки", "кое", "де", "мол"}

    def verb_of(w):
        r = cache.get(w, 0)
        if r != 0:
            return r
        lem = None
        if w in NOT_VERB:
            cache[w] = None
            return None
        if w == "есть":
            cache[w] = "быть"
            return "быть"
        try:
            if not m.word_is_known(w):
                cache[w] = None
                return None
            p = m.parse(w)[0]
            pos = p.tag.POS
            if pos in ("VERB", "INFN"):
                lem = p.normal_form
            elif pos in ("PRTF", "PRTS", "GRND"):
                inf = p.inflect({"INFN"})
                lem = inf.word if inf else None
        except Exception:
            lem = None
        cache[w] = lem
        return lem

    count = collections.Counter()
    forms = collections.defaultdict(collections.Counter)
    seen_form = collections.Counter()                 # (lemma, form) → times seen in a good sentence
    cands = collections.defaultdict(list)             # (lemma, form) → up to 3 [sentence, book]
    used_books, seen_hash = [], set()
    tokens = 0
    for bi, b in enumerate(books, 1):
        paras = list(paragraphs(os.path.join("public/books", b["filename"])))
        h = hashlib.sha1(" ".join(paras[:40])[:4000].encode("utf-8")).hexdigest()
        if h in seen_hash:
            continue                                  # the same text, filed twice
        seen_hash.add(h)
        bnum = len(used_books)
        used_books.append(b["filename"])
        for para in paras:
            for s in SENT.split(para):
                ws = WORD.findall(s.lower())
                if not ws:
                    continue
                tokens += len(ws)
                ok = None
                for w in ws:
                    lem = verb_of(w)
                    if not lem:
                        continue
                    count[lem] += 1
                    w = w.replace("ё", "е")         # most of the library is printed without ё
                    forms[lem][w] += 1
                    if ok is None:
                        ok = good_sentence(s.strip())
                    if ok:
                        k = (lem, w)
                        seen_form[k] += 1
                        n = seen_form[k]
                        lst = cands[k]
                        item = [s.strip(), w, bnum]
                        if len(lst) < 3:
                            lst.append(item)
                        else:
                            j = random.randrange(n)  # reservoir: every sentence equally likely
                            if j < 3:
                                lst[j] = item
        if bi % 100 == 0 or bi == len(books):
            print("  %d/%d books · %s words · %d verbs · %.0fs" % (bi, len(books), format(tokens, ","), len(count), time.time() - t0), flush=True)

    ranked = [v for v, n in count.most_common() if n >= 3]
    rank = {v: i + 1 for i, v in enumerate(ranked)}

    # English glosses from the frequency deck, where it has the verb.
    gloss = {}
    for f in sorted(glob.glob("public/vocab/blocks/*.json")):
        try:
            for e in json.load(io.open(f, encoding="utf-8")):
                if e.get("pos") == "verb" and e.get("en"):
                    for r in re.split(r"\s*/\s*", e.get("ru") or ""):
                        r = r.replace("́", "").strip()
                        if r and r not in gloss:
                            gloss[r] = e["en"]
        except Exception:
            pass
    irr = []
    try:
        for g in json.load(io.open("src/verbs-irregular.json", encoding="utf-8"))["groups"]:
            irr += [v[0] for v in g["verbs"]]
    except Exception:
        pass

    def pick_examples(lem, want):
        fs = [f for f, _ in forms[lem].most_common()]
        pools = {f: list(cands.get((lem, f), [])) for f in fs}
        for f in pools:
            pools[f].sort(key=lambda it: abs(len(it[0]) - 85))
        out, books_used, sents = [], set(), set()
        rnd = 0
        while len(out) < want and rnd < 6:
            added = False
            for f in fs:
                if len(out) >= want:
                    break
                pool = pools[f]
                for it in pool:
                    if it[0] in sents:
                        continue
                    if rnd < 2 and it[2] in books_used:
                        continue
                    out.append(it); sents.add(it[0]); books_used.add(it[2]); pool.remove(it); added = True
                    break
            rnd += 1
            if not added and rnd >= 2:
                break
        return out

    shards = {}
    for v in ranked:
        n = count[v]
        r = rank[v]
        if n < 5 and v not in irr:
            continue                                  # ranked, but too rare to carry a shard entry
        want = 12 if r <= 1500 or v in irr else (4 if n >= 40 else 0)
        e = {"n": n, "r": r, "f": dict(forms[v].most_common(24 if (r <= 3000 or v in irr) else 5))}
        if want:
            x = pick_examples(v, want)
            if x:
                e["x"] = x
        if v in gloss:
            e["en"] = gloss[v]
        shards.setdefault(shard_of(v), {})[v] = e
    split = []
    for k in list(shards):
        if len(json.dumps(shards[k], ensure_ascii=False).encode("utf-8")) > 300000:
            split.append(k)
            for w, e in shards.pop(k).items():
                k3 = k + (CODE[ALPH.index(w[2])] if len(w) > 2 and w[2] in ALPH else "_")
                shards.setdefault(k3, {})[w] = e
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "*.json")):
        os.remove(f)
    size = 0
    for k, d in shards.items():
        s = json.dumps(d, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        io.open(os.path.join(OUT, k + ".json"), "w", encoding="utf-8").write(s)
        size += len(s.encode("utf-8"))
    verb_tokens = sum(count.values())
    index = {
        "built": time.strftime("%Y-%m-%d"),
        "books": len(used_books), "words": tokens, "verbTokens": verb_tokens, "verbs": len(ranked),
        "split": sorted(split),
        "top": [[v, count[v]] for v in ranked[:5000]],
        "irr": {v: [count.get(v, 0), rank.get(v, 0)] for v in irr},
        "en": {v: gloss[v] for v in ranked[:1500] if v in gloss},
        "files": used_books,
    }
    s = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    io.open(os.path.join(OUT, "index.json"), "w", encoding="utf-8").write(s)
    io.open(os.path.join(OUT, "LICENSE"), "w", encoding="utf-8").write(
        "Verb counts made with pymorphy3 (MIT) and the OpenCorpora dictionary (CC BY-SA 3.0).\n"
        "Example sentences are quoted from the public-domain books in this site's library.\n")
    print("\n%d books (%d skipped as duplicates) · %s words · %s verb uses · %d verbs (seen 3+ times)"
          % (len(used_books), len(books) - len(used_books), format(tokens, ","), format(verb_tokens, ","), len(ranked)))
    print("Top 25: " + ", ".join("%s %s" % (v, format(count[v], ",")) for v in ranked[:25]))
    print("%d shards, %.1f MB, index %.0f KB · %.0f min" % (len(shards), size / 1e6, len(s.encode('utf-8')) / 1e3, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
