#!/usr/bin/env python3
"""Aesop's fables on the Fairytales and Translations shelves, Russian beside
English. Runs in WSL (network). Nothing is machine-written.

  Russian  every Aesop fable on Russian Wikisource's «Басни Эзопа» page in a
           public-domain translation: Лев Толстой's 33 (from his «Русские
           книги для чтения», 1875), В. А. Алексеев's 7 (1888) and Ушинский's
           «Ветер и солнце». One section per fable.
  English  George Fyler Townsend's translation (1867), Project Gutenberg 21,
           fable by fable. A handful of Tolstoy's have no counterpart in
           Townsend's collection and stand alone.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/aesop.py
    python3 tools/gen_stress_maps.py
    python3 tools/make_case_drills.py --book aesop-basni.fb2 --min-per-chapter 1 --force
"""
import html, io, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from reader_chapters import reader_chapters

SLUG = "aesop-basni"
UA = {"User-Agent": "govorim-app/1.0 (library import; contact via github)"}
WS = "https://ru.wikisource.org/w/api.php"
GUT = "https://www.gutenberg.org/cache/epub/21/pg21.txt"
MANIFEST = "private/books/index.json"
BOOKS = "public/books"
CACHE = "tools/aesop-src"
COVER = "https://commons.wikimedia.org/wiki/Special:FilePath/Velázquez_-_Esopo_(Museo_del_Prado,_1639-41).jpg?width=500"

# Russian Wikisource page -> Townsend's title (None: not in his collection)
EN = {
    "Волк и журавль": "The Wolf and the Crane", "Волк и кобыла": None,
    "Волк и ягнёнок": "The Wolf And The Lamb", "Ворон и лисица": "The Fox and the Crow",
    "Галка и голуби": "The Jackdaw and the Doves", "Голова и хвост змеи": None,
    "Зайцы и лягушки": "The Hares and the Frogs", "Камыш и маслина": "The Oak and the Reeds",
    "Комар и лев": "The Gnat and the Lion", "Курица и золотые яйца": "The Hen and the Golden Eggs",
    "Курица и ласточка": "The Hen and the Swallow", "Лгун": "The Shepherd’s Boy and the Wolf",
    "Лев, волк и лисица": "The Lion, the Wolf, and the Fox", "Лев и мышь": "The Lion And The Mouse",
    "Лев, медведь и лисица": "The Lion, the Bear, and the Fox", "Лисица": "The Fox Who Had Lost His Tail",
    "Лисица и виноград": "The Fox and the Grapes", "Лисица и козёл": "The Fox and the Goat",
    "Лягушка и лев": None, "Муравей и голубка": "The Ant and the Dove", "Олень": "The Stag at the Pool",
    "Олень и ланчук": "The Fawn and His Mother", "Осёл в львиной шкуре": "The Ass in the Lion’s Skin",
    "Осёл и лошадь": "The Ass and the Mule", "Отец и сыновья": "The Father And His Sons",
    "Пчёлы и трутни": None, "Рыбак и рыбка": "The Fisherman and the Little Fish", "Собака и волк": None,
    "Собака и её тень": "The Dog and the Shadow", "Собака, петух и лисица": "The Dog, the Cock, and the Fox",
    "Старик и смерть": "The Old Man and Death", "Стрекоза и муравьи": "The Ants and the Grasshopper",
    "Черепаха и орёл": "The Tortoise and the Eagle",
    "Бедняк": None, "Бык и Жаба": "The Ox and the Frog", "Ворон и Лисица": "The Fox and the Crow",
    "Два Горшка": "The Two Pots", "Жук и Муравей": "The Ants and the Grasshopper", "Крестьянин и его сыновья": "The Farmer and His Sons",
    "Лисица и Виноград": "The Fox and the Grapes", "Ветер и солнце": "The North Wind and the Sun",
}
WHO = {"Лев Толстой": "", "Алексеев": " (пер. В. А. Алексеева)", "Ушинский": " (пер. К. Д. Ушинского)"}


def get(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r"[^\w.-]+", "_", name))
    if os.path.exists(path):
        return io.open(path, encoding="utf-8").read()
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                t = r.read().decode("utf-8")
            io.open(path, "w", encoding="utf-8").write(t)
            time.sleep(2)              # Wikisource answers 429 to anything faster
            return t
        except Exception as e:
            wait = 30 * (i + 1) if "429" in str(e) else 5
            ra = getattr(e, "headers", None) and e.headers.get("Retry-After")
            if ra and str(ra).isdigit():
                wait = max(wait, int(ra))
            print("   %s: %s — waiting %ds" % (name, e, wait), flush=True); time.sleep(wait)
    sys.exit("could not fetch " + url)


def wikitext(page):
    q = urllib.parse.urlencode({"action": "parse", "prop": "wikitext", "format": "json", "page": page})
    return json.loads(get(WS + "?" + q, page + ".json"))["parse"]["wikitext"]["*"]


def body(wt):
    """The fable's text from a Wikisource page: after the header template,
    before the categories; bold title line, poem tags and markup removed."""
    i = wt.find("}}\n")
    t = wt[i + 3:] if i >= 0 else wt
    t = re.split(r"\[\[(?:Категория|[a-z]{2,3}):", t)[0]
    t = re.sub(r"\{\{poemx1\|[^|]*\|(.*?)\|\}\}", r"\1", t, flags=re.S)   # {{poemx1|TITLE|text|}}
    t = re.sub(r"</?poem>|<br\s*/?>|<center>|</center>", "\n", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", t)]
    paras = [p for p in paras if p]
    if paras and re.fullmatch(r"'''[^']+'''", paras[0]):      # the bold title line
        paras = paras[1:]
    paras = [html.unescape(re.sub(r"'{2,}", "", p)).strip() for p in paras]
    return [p for p in paras if p]


def townsend():
    t = get(GUT, "pg21.txt").replace("\r\n", "\n")
    s, e = t.find("*** START"), t.find("*** END")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", t[s:e])]
    out, cur = {}, None
    for b in blocks:
        if re.match(r"^The [A-Z]", b) and len(b) < 70 and "\n" not in b and not re.search(r"[.!?]$", b):
            cur = b.lower() if b.lower() not in out else None     # a title Townsend repeats: keep the first
            if cur:
                out[cur] = []
            continue
        if cur:
            out[cur].append(re.sub(r"\s+", " ", b))
    return out


def esc(s):
    return html.escape(s, quote=False)


def main():
    idx_wt = wikitext("Басни Эзопа")
    pages = re.findall(r"#\s*\[\[([^|\]]+\((?:Эзоп;\s*)(Лев Толстой|Алексеев|Ушинский)\)\s*)\|", idx_wt)
    print("%d fables listed" % len(pages))
    en = townsend()
    sections, english, words, unmatched = [], [], 0, []
    for page, who in pages:
        page = re.sub(r"\s+", " ", page).strip()
        name = re.sub(r"\s*\(Эзоп;.*\)$", "", page).strip()
        paras = body(wikitext(page))
        if not paras:
            print("   !! empty: %s" % page); continue
        title = name + WHO[who]
        sections.append("<section>\n<title><p>%s</p></title>\n%s\n</section>"
                        % (esc(title), "\n".join("<p>%s</p>" % esc(p) for p in paras)))
        words += sum(len(p.split()) for p in paras)
        key = EN.get(name)
        txt = "\n\n".join(en.get(key.lower(), [])) if key else ""
        if key and not txt:
            unmatched.append(key)
        english.append(((key + "\n\n") if txt else "") + txt)
    fb2 = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">\n<description><title-info>'
           '<author><first-name></first-name><last-name>Эзоп</last-name></author>'
           '<book-title>Басни Эзопа</book-title><lang>ru</lang></title-info></description>\n'
           '<body>\n<title><p>Эзоп</p><p>Басни</p></title>\n%s\n</body>\n</FictionBook>\n' % "\n".join(sections))
    path = os.path.join(BOOKS, "novel", SLUG + ".fb2")
    io.open(path, "w", encoding="utf-8", newline="\n").write(fb2)
    chs, how = reader_chapters(path)
    print("FB2: %d fables, %s words; reader sees %d chapters (%s)" % (len(sections), format(words, ","), len(chs), how))
    if len(chs) != len(sections):
        print("   !! chapter count differs from fables — English would misalign; not writing it")
        return
    d = os.path.join(BOOKS, SLUG + "-en")
    os.makedirs(d, exist_ok=True)
    for i, t in enumerate(english, 1):
        io.open(os.path.join(d, "%02d.json" % i), "w", encoding="utf-8").write(
            json.dumps({"0": t} if t else {}, ensure_ascii=False))
    print("English: %d of %d fables matched in Townsend%s" % (sum(1 for t in english if t), len(english),
          ("; not found: " + ", ".join(unmatched)) if unmatched else ""))
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    entry = {
        "filename": "novel/%s.fb2" % SLUG, "slug": SLUG, "title": "Басни Эзопа", "author": "Эзоп",
        "category": "Fairytales", "alsoIn": ["Translations"], "words": words, "public": True, "cover": COVER,
        "translator": "Л. Н. Толстой, В. А. Алексеев, К. Д. Ушинский",
        "parallelEn": SLUG + "-en", "enTitle": "Aesop's Fables", "enAuthor": "Aesop (tr. George Fyler Townsend)",
        "blurb": "Эзоп — полулегендарный древнегреческий поэт-баснописец, живший около VI века до н. э. "
                 "Басни Эзопа стали основой для басен многих поколений баснописцев.",
        "blurbSrc": "https://ru.wikipedia.org/wiki/Эзоп", "blurbLang": "ru",
        "translationNote": ("Neither column is the original: Aesop's fables come down in ancient Greek. The Russian "
                            "is Лев Толстой's retellings for his readers for children (1875), with seven by "
                            "В. А. Алексеев (1888) and one by Ушинский; the English is George Fyler Townsend's "
                            "translation (1867). All are in the public domain. Tolstoy retold freely, so the two "
                            "versions of a fable may differ in detail, and a few of his have no English "
                            "counterpart. Swipe right on the text to read them side by side, or tap the EN button "
                            "on the right."),
    }
    old = next((b for b in idx if b.get("slug") == SLUG), None)
    if old:
        old.update(entry)
    else:
        idx.append(entry)
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\nDone. Next: python3 tools/gen_stress_maps.py, then the case drills (see the top of this file).")


if __name__ == "__main__":
    main()
