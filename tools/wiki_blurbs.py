#!/usr/bin/env python3
"""Shelf descriptions from Wikipedia, for the works that have none. WSL (network).

Nothing here is written by a model: every description is the opening of the
work's own Wikipedia article, quoted, with a link back to it. Wikipedia text is
CC BY-SA 4.0, so each one carries its source URL (`blurbSrc`), which the shelf
shows as a "Wikipedia" credit.

How a work is found:
  1. the author's Wikidata item (from their Russian Wikipedia article);
  2. every Wikidata item with that author (P50), matched to the catalogue
     title on its Russian/English label, its aliases, or its article title
     without the "(рассказ)" bracket;
  3. failing that, Russian Wikipedia page titles tried directly — «Тоска
     (рассказ)», «Тоска (рассказ Чехова)» and so on — kept only if the page's
     Wikidata item names this author.
Descriptions are Russian (`blurbLang: "ru"`), from Russian Wikipedia; an
English-only article is used only with --allow-en. With --described the
works that already carry a hand-written English description get a Russian
one too, and --apply keeps the English as `blurbEn`.

    python3 tools/wiki_blurbs.py                # fetch, write tools/out/wiki-blurbs.json + .tsv to review
    python3 tools/wiki_blurbs.py --apply        # write the reviewed file into the catalogue
    python3 tools/wiki_blurbs.py --en-only      # skip Russian-only articles
    python3 tools/wiki_blurbs.py --author "Чехов А.П."   # one author only
    python3 tools/wiki_blurbs.py --refresh      # re-cut the articles already found (English → Russian)
    python3 tools/wiki_blurbs.py --described    # also the works that already have an English description
    python3 tools/wiki_blurbs.py --allow-en     # take an English article where there is no Russian one

Safe to stop and re-run: finished authors are kept in tools/out/wiki-blurbs.json.
"""
import json, os, re, sys, time, urllib.parse, urllib.request, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
UA = {"User-Agent": "SamovarShelfBlurbs/1.0 (samovar.live; personal reading library)"}
MANIFEST = "private/books/index.json"
OUT = "tools/out/wiki-blurbs.json"
TSV = "tools/out/wiki-blurbs.tsv"
MAXLEN = 320

AUTHOR_PAGES = {
"Платон": "Платон", "Аристотель": "Аристотель", "Ницше Ф.": "Ницше, Фридрих", "Макиавелли Н.": "Макиавелли, Никколо", "Шопенгауэр А.": "Шопенгауэр, Артур", "Эпиктет": "Эпиктет", "Чаадаев П.Я.": "Чаадаев, Пётр Яковлевич", "Соловьёв В.С.": "Соловьёв, Владимир Сергеевич", "Бердяев Н.А.": "Бердяев, Николай Александрович", "Шестов Л.": "Шестов, Лев Исаакович", "Розанов В.В.": "Розанов, Василий Васильевич", "Фёдоров Н.Ф.": "Фёдоров, Николай Фёдорович", "Кропоткин П.А.": "Кропоткин, Пётр Алексеевич", "Бакунин М.А.": "Бакунин, Михаил Александрович", "Леонтьев К.Н.": "Леонтьев, Константин Николаевич",
"Чехов А.П.": "Чехов, Антон Павлович",
"Бунин И.А.": "Бунин, Иван Алексеевич",
"Тургенев И.С.": "Тургенев, Иван Сергеевич",
"Горький М.": "Максим Горький",
"Толстой Л.Н.": "Толстой, Лев Николаевич",
"Пушкин А.С.": "Пушкин, Александр Сергеевич",
"Достоевский Ф.М.": "Достоевский, Фёдор Михайлович",
"Булгаков М.А.": "Булгаков, Михаил Афанасьевич",
"Лермонтов М.Ю.": "Лермонтов, Михаил Юрьевич",
"Маяковский В.В.": "Маяковский, Владимир Владимирович",
"Есенин С.А.": "Есенин, Сергей Александрович",
"Тютчев Ф.И.": "Тютчев, Фёдор Иванович",
"Куприн А.И.": "Куприн, Александр Иванович",
"Андреев Л.Н.": "Андреев, Леонид Николаевич",
"Некрасов Н.А.": "Некрасов, Николай Алексеевич",
"Блок А.А.": "Блок, Александр Александрович",
"Афанасьев А.Н.": "Афанасьев, Александр Николаевич",
"Фет А.А.": "Фет, Афанасий Афанасьевич",
"Крылов И.А.": "Крылов, Иван Андреевич",
"Гоголь Н.В.": "Гоголь, Николай Васильевич",
"Салтыков-Щедрин М.Е.": "Салтыков-Щедрин, Михаил Евграфович",
"Лесков Н.С.": "Лесков, Николай Семёнович",
"Толстой А.К.": "Толстой, Алексей Константинович",
"Островский А.Н.": "Островский, Александр Николаевич",
"Ленин В.И.": "Ленин, Владимир Ильич",
"Короленко В.Г.": "Короленко, Владимир Галактионович",
"Жуковский В.А.": "Жуковский, Василий Андреевич",
"Цветаева М.И.": "Цветаева, Марина Ивановна",
"Гаршин В.М.": "Гаршин, Всеволод Михайлович",
"Диккенс Ч.": "Диккенс, Чарльз",
"Замятин Е.И.": "Замятин, Евгений Иванович",
"Гайдар А.П.": "Гайдар, Аркадий Петрович",
"Никитин И.С.": "Никитин, Иван Саввич",
"Брюсов В.Я.": "Брюсов, Валерий Яковлевич",
"Купер Дж. Ф.": "Купер, Джеймс Фенимор",
"Лондон Дж.": "Лондон, Джек",
"Сталин И.В.": "Сталин, Иосиф Виссарионович",
"Грин А.С.": "Грин, Александр Степанович",
"Толстой А.Н.": "Толстой, Алексей Николаевич",
"Державин Г.Р.": "Державин, Гавриил Романович",
"Твен М.": "Марк Твен",
"Марриет Ф.": "Марриет, Фредерик",
"Сологуб Ф.К.": "Фёдор Сологуб",
"Карамзин Н.М.": "Карамзин, Николай Михайлович",
"Одоевский В.Ф.": "Одоевский, Владимир Фёдорович",
"Аверченко А.Т.": "Аверченко, Аркадий Тимофеевич",
"Кольцов А.В.": "Кольцов, Алексей Васильевич",
"Майков А.Н.": "Майков, Аполлон Николаевич",
"Полонский Я.П.": "Полонский, Яков Петрович",
"Бальмонт К.Д.": "Бальмонт, Константин Дмитриевич",
"Волошин М.А.": "Волошин, Максимилиан Александрович",
"Уэллс Г.": "Уэллс, Герберт Джордж",
"Мамин-Сибиряк Д.Н.": "Мамин-Сибиряк, Дмитрий Наркисович",
"Беляев А.Р.": "Беляев, Александр Романович",
"Анненский И.Ф.": "Анненский, Иннокентий Фёдорович",
"Хлебников В.": "Хлебников, Велимир",
"Стивенсон Р. Л.": "Стивенсон, Роберт Льюис",
"Герцен А.И.": "Герцен, Александр Иванович",
"Гончаров И.А.": "Гончаров, Иван Александрович",
"Гарин-Михайловский Н.Г.": "Гарин-Михайловский, Николай Георгиевич",
"Вересаев В.В.": "Вересаев, Викентий Викентьевич",
"Тэффи Н.А.": "Тэффи",
"Тынянов Ю.Н.": "Тынянов, Юрий Николаевич",
"Батюшков К.Н.": "Батюшков, Константин Николаевич",
"Рылеев К.Ф.": "Рылеев, Кондратий Фёдорович",
"Северянин И.": "Игорь Северянин",
"Ходасевич В.Ф.": "Ходасевич, Владислав Фелицианович",
"Багрицкий Э.Г.": "Багрицкий, Эдуард Георгиевич",
"Скотт В.": "Скотт, Вальтер",
"Киплинг Р.": "Киплинг, Редьярд",
"Майн Рид Т.": "Майн Рид",
"Бульвер-Литтон Э.": "Бульвер-Литтон, Эдвард",
"Мережковский Д.С.": "Мережковский, Дмитрий Сергеевич",
"Аксаков С.Т.": "Аксаков, Сергей Тимофеевич",
"Помяловский Н.Г.": "Помяловский, Николай Герасимович",
"Белый А.": "Андрей Белый",
"Шмелёв И.С.": "Шмелёв, Иван Сергеевич",
"Суриков И.З.": "Суриков, Иван Захарович",
"Козлов И.И.": "Козлов, Иван Иванович",
"Языков Н.М.": "Языков, Николай Михайлович",
"Козьма Прутков": "Козьма Прутков",
"Поварнин С.И.": "Поварнин, Сергей Иннокентьевич",
"Виппер Р.Ю.": "Виппер, Роберт Юрьевич",
"Конрад Дж.": "Конрад, Джозеф",
"Теккерей У.": "Теккерей, Уильям Мейкпис",
"Конан Дойл А.": "Дойл, Артур Конан",
"Арцыбашев М.П.": "Арцыбашев, Михаил Петрович",
"Грибоедов А.С.": "Грибоедов, Александр Сергеевич",
"Брежнев Л.И.": "Брежнев, Леонид Ильич",
"Островский Н.А.": "Островский, Николай Алексеевич",
"Фонвизин Д.И.": "Фонвизин, Денис Иванович",
"Погорельский А.": "Антоний Погорельский",
"Писемский А.Ф.": "Писемский, Алексей Феофилактович",
"Успенский Г.И.": "Успенский, Глеб Иванович",
"Фурманов Д.А.": "Фурманов, Дмитрий Андреевич",
"Ломоносов М.В.": "Ломоносов, Михаил Васильевич",
"Баратынский Е.А.": "Баратынский, Евгений Абрамович",
"Дельвиг А.А.": "Дельвиг, Антон Антонович",
"Апухтин А.Н.": "Апухтин, Алексей Николаевич",
"Вяземский П.А.": "Вяземский, Пётр Андреевич",
"Огарёв Н.П.": "Огарёв, Николай Платонович",
"Дефо Д.": "Дефо, Даниель",
"Джером Дж. К.": "Джером, Джером Клапка",
"Голсуорси Дж.": "Голсуорси, Джон",
"Кэрролл Л.": "Кэрролл, Льюис",
"Бичер-Стоу Г.": "Бичер-Стоу, Гарриет",
"Ерофеев В.В.": "Ерофеев, Венедикт Васильевич",
"Драгунский В.Ю.": "Драгунский, Виктор Юзефович",
"Пастернак Б.Л.": "Пастернак, Борис Леонидович",
"Костюченко Е.Г.": "Костюченко, Елена Геннадьевна",
"Навальный А.А.": "Навальный, Алексей Анатольевич",
"Шолохов М.А.": "Шолохов, Михаил Александрович",
"Киз Д.": "Киз, Дэниел",
"Радищев А.Н.": "Радищев, Александр Николаевич",
"Ершов П.П.": "Ершов, Пётр Павлович",
"Гладков Ф.В.": "Гладков, Фёдор Васильевич",
"Чернышевский Н.Г.": "Чернышевский, Николай Гаврилович",
"Слепцов В.А.": "Слепцов, Василий Алексеевич",
"Решетников Ф.М.": "Решетников, Фёдор Михайлович",
"Боборыкин П.Д.": "Боборыкин, Пётр Дмитриевич",
"Серафимович А.С.": "Серафимович, Александр Серафимович",
"Бабель И.Э.": "Бабель, Исаак Эммануилович",
"Неверов А.С.": "Неверов, Александр Сергеевич",
"Плещеев А.Н.": "Плещеев, Алексей Николаевич",
"Надсон С.Я.": "Надсон, Семён Яковлевич",
"Случевский К.К.": "Случевский, Константин Константинович",
"Гиппиус З.Н.": "Гиппиус, Зинаида Николаевна",
"Кузмин М.А.": "Кузмин, Михаил Алексеевич",
"Саша Чёрный": "Саша Чёрный",
"Вахтеров В.П.": "Вахтеров, Василий Порфирьевич",
"Богораз-Тан В.Г.": "Богораз, Владимир Германович",
"Щерба Л.В.": "Щерба, Лев Владимирович",
"Олкотт Л. М.": "Олкотт, Луиза Мэй",
"Драйзер Т.": "Драйзер, Теодор",
"Гарди Т.": "Гарди, Томас",
"Бёрнетт Ф. Х.": "Бёрнетт, Фрэнсис Элиза Ходжсон",
"Беллами Э.": "Беллами, Эдвард",
"Хаггард Г. Р.": "Хаггард, Генри Райдер",
"Стокер Б.": "Стокер, Брэм",
"Уайльд О.": "Уайльд, Оскар",
"Троллоп Э.": "Троллоп, Энтони",
"Молотов В.М.": "Молотов, Вячеслав Михайлович",
"Горбачёв М.С.": "Горбачёв, Михаил Сергеевич",
"Ильф И. и Петров Е.": "Ильф и Петров"
}

GENRES = {
    "Short Stories": ["рассказ", "очерк", "новелла", "повесть", "сказка"],
    "Novellas": ["повесть", "рассказ"],
    "Novels": ["роман", "повесть"],
    "Plays": ["пьеса", "комедия", "драма", "трагедия", "водевиль"],
    "Poetry": ["стихотворение", "поэма", "баллада", "басня"],
    "Philosophy": ["диалог", "трактат", "книга", "Аристотель", "Макиавелли"],
}


def get(url, tries=6, data=None):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA, data=data)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                wait = int(e.headers.get("Retry-After") or 0) or 5 * (i + 1)
                print("    ...%s, waiting %ss" % (e.code, wait), flush=True)
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            print("    ...%s, retrying" % e, flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError("gave up on " + url)


def api(host, **params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    time.sleep(0.4)
    # POST: fifty Cyrillic titles percent-encoded overflow a URL (HTTP 414).
    return get("https://%s/w/api.php" % host, data=urllib.parse.urlencode(params).encode("utf-8"))


def sparql(q):
    time.sleep(1.0)
    return get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q))["results"]["bindings"]


def norm(s):
    s = str(s or "").lower().replace("ё", "е").replace("́", "")
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)          # «Тоска (рассказ)» → «тоска»
    s = re.sub(r"[«»\"'„“”.,!?…:;—–\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def author_qid(page):
    r = api("ru.wikipedia.org", action="query", prop="pageprops", ppprop="wikibase_item",
            redirects=1, titles=page)
    for p in r["query"]["pages"]:
        q = (p.get("pageprops") or {}).get("wikibase_item")
        if q:
            return q
    return None


def works_of(qid):
    rows = sparql("""
SELECT ?w ?ru ?en ?alias ?ruT ?enT WHERE {
  ?w wdt:P50 wd:%s .
  OPTIONAL { ?w rdfs:label ?ru FILTER(lang(?ru) = "ru") }
  OPTIONAL { ?w rdfs:label ?en FILTER(lang(?en) = "en") }
  OPTIONAL { ?w skos:altLabel ?alias FILTER(lang(?alias) = "ru") }
  OPTIONAL { ?a schema:about ?w ; schema:isPartOf <https://ru.wikipedia.org/> ; schema:name ?ruT }
  OPTIONAL { ?b schema:about ?w ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?enT }
}""" % qid)
    works = {}
    for r in rows:
        w = r["w"]["value"].rsplit("/", 1)[1]
        d = works.setdefault(w, {"keys": set(), "ru": None, "en": None})
        for k in ("ru", "en", "alias", "ruT"):
            if k in r:
                d["keys"].add(norm(r[k]["value"]))
        if "ruT" in r:
            d["ru"] = r["ruT"]["value"]
        if "enT" in r:
            d["en"] = r["enT"]["value"]
    return works


def p50_of(qids):
    out = {}
    qids = [q for q in qids if q]
    for i in range(0, len(qids), 50):
        r = api("www.wikidata.org", action="wbgetentities", ids="|".join(qids[i:i + 50]), props="claims|sitelinks")
        for q, e in (r.get("entities") or {}).items():
            claims = e.get("claims") or {}
            auth = set()
            for c in claims.get("P50", []):
                try:
                    auth.add(c["mainsnak"]["datavalue"]["value"]["id"])
                except Exception:
                    pass
            out[q] = {"authors": auth, "en": ((e.get("sitelinks") or {}).get("enwiki") or {}).get("title")}
    return out


def direct_pages(titles):
    """Russian Wikipedia: page title → (resolved title, wikidata qid) for those that exist."""
    found = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        r = api("ru.wikipedia.org", action="query", prop="pageprops", ppprop="wikibase_item|disambiguation",
                redirects=1, titles="|".join(chunk))
        q = r["query"]
        back = {}
        for n in q.get("normalized", []):
            back[n["to"]] = n["from"]
        for n in q.get("redirects", []):
            back[n["to"]] = back.get(n["from"], n["from"])
        for p in q.get("pages", []):
            if p.get("missing") or "disambiguation" in (p.get("pageprops") or {}):
                continue
            src = back.get(p["title"], p["title"])
            found[src] = (p["title"], (p.get("pageprops") or {}).get("wikibase_item"))
    return found


def extracts(host, titles):
    out = {}
    for i in range(0, len(titles), 20):
        r = api(host, action="query", prop="extracts", exintro=1, explaintext=1, redirects=1,
                titles="|".join(titles[i:i + 20]))
        q = r["query"]
        back = {}
        for n in q.get("normalized", []) + q.get("redirects", []):
            back[n["to"]] = back.get(n["from"], n["from"])
        for p in q.get("pages", []):
            t = p.get("extract") or ""
            if t:
                out[back.get(p["title"], p["title"])] = (p["title"], t)
    return out


ABBR = re.compile(r"(?:\b[A-ZА-ЯЁ]|\bMr|\bMrs|\bDr|\bSt|\bJr|\bvs|\bгг?|\bт\. ?е|\bт\. ?н|\bдр|\bим|\bсв|\bок|\bстр|\bсм|\bрус|\bангл|\bлат|\bнем|\bфр|\bпер)\.$")
NOT_A_WORK = re.compile(r"\b(film|album|song|band|TV series|television|opera by|ballet by|фильм|альбом|песня|группа|телесериал|опера|балет)\b", re.I)
LITERARY = re.compile(r"\b(short story|story by|novel|novella|poem|play by|play written|fable|ballad|рассказ|повесть|роман|стихотворени|поэм|пьес|басн|баллад|очерк|сказк)", re.I)


def sentences(t):
    """Split on sentence ends, but not after an initial («А. П. Чехова»)
    or a common abbreviation."""
    parts = re.split(r"(?<=[.!?…])\s+(?=[A-ZА-ЯЁ«\"(])", t)
    out = []
    for p in parts:
        if out and ABBR.search(out[-1]):
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


def lead(text):
    """The opening sentence or two of an article, as Wikipedia wrote it."""
    t = re.sub(r"\s+", " ", text).strip()
    # A hatnote ahead of the lead: «О карточной игре см. стос «Штосс» …»
    t = re.sub(r"^(?:О|Об|Это статья|Не следует путать)[^«]{0,120}?см\. [^«]{0,60}?(?=«)", "", t)
    t = re.sub(r"\s*\([^()]*(?:listen|pronounced)[^()]*\)", "", t)
    parts = sentences(t)
    if not parts or (NOT_A_WORK.search(parts[0]) and not LITERARY.search(parts[0])):
        return ""
    out = ""
    for n, s in enumerate(parts):
        # Two sentences at most: past that, an article's lead is usually
        # telling the plot, and a shelf should not.
        if n >= 2 or (out and len(out) + 1 + len(s) > MAXLEN):
            break
        out = (out + " " + s).strip()
        if len(out) >= 140:
            break
    if len(out) > MAXLEN:
        cut = out[:MAXLEN].rsplit(" ", 1)[0]
        out = cut.rstrip(",;:—– ") + "…"
    return out


def ru_titles_for(en_titles):
    """English article → its Russian counterpart, through the language links."""
    out = {}
    en_titles = sorted(set(en_titles))
    for i in range(0, len(en_titles), 50):
        r = api("en.wikipedia.org", action="query", prop="langlinks", lllang="ru", lllimit="max",
                redirects=1, titles="|".join(en_titles[i:i + 50]))
        q = r["query"]
        back = {}
        for n in q.get("normalized", []) + q.get("redirects", []):
            back[n["to"]] = back.get(n["from"], n["from"])
        for pg in q.get("pages", []):
            for ll in pg.get("langlinks", []) or []:
                if ll.get("lang") == "ru" and ll.get("title"):
                    out[back.get(pg["title"], pg["title"])] = ll["title"]
    return out


def wiki_url(host, title):
    return "https://%s/wiki/%s" % (host, urllib.parse.quote(title.replace(" ", "_")))


def refresh(state, allow_en=False):
    """Re-read the articles already found and cut their openings again —
    for when lead() changes, without searching for every work afresh. Unless
    English is allowed, an English article is swapped for its Russian one,
    and a work with no Russian article is dropped."""
    if not allow_en:
        en = {}
        for fn, h in state["works"].items():
            m = re.match(r"https://en\.wikipedia\.org/wiki/(.+)$", h["url"])
            if m:
                en[fn] = urllib.parse.unquote(m.group(1)).replace("_", " ")
        ru = ru_titles_for(en.values())
        gone = 0
        for fn, t in en.items():
            if t in ru:
                state["works"][fn].update(url=wiki_url("ru.wikipedia.org", ru[t]), lang="ru")
            else:
                state["works"].pop(fn, None)
                gone += 1
        print("%d English articles swapped for Russian, %d had no Russian article" % (len(en) - gone, gone))
    by_host = {}
    for fn, h in state["works"].items():
        m = re.match(r"https://([^/]+)/wiki/(.+)$", h["url"])
        if m:
            by_host.setdefault(m.group(1), {})[urllib.parse.unquote(m.group(2)).replace("_", " ")] = fn
    drop = []
    for host, titles in by_host.items():
        ex = extracts(host, sorted(titles))
        for t, fn in titles.items():
            got = ex.get(t)
            b = lead(got[1]) if got else ""
            if len(b) < 25:
                drop.append(fn)
            else:
                state["works"][fn]["blurb"] = b
    for fn in drop:
        state["works"].pop(fn, None)
    print("refreshed; %d dropped as not about a literary work" % len(drop))


def main():
    args = sys.argv[1:]
    en_only = "--en-only" in args
    # Russian Wikipedia is the source; English only with --allow-en.
    allow_en = "--allow-en" in args or en_only
    # --described: also the works that already have a (hand-written English)
    # description, so that every shelf description can be Russian.
    described = "--described" in args
    done_key = "authorsDoneDescribed" if described else "authorsDone"
    only = args[args.index("--author") + 1] if "--author" in args else None
    manifest = json.load(open(MANIFEST, encoding="utf-8"))

    if "--apply" in args:
        found = json.load(open(OUT, encoding="utf-8"))
        backup = MANIFEST + ".bak-wikiblurbs"
        if not os.path.exists(backup):
            shutil.copy(MANIFEST, backup)
        n = 0
        for b in manifest:
            hit = found.get("works", {}).get(b.get("filename"))
            if not hit or b.get("blurbSrc") == hit["url"]:
                continue
            if b.get("blurb") and not b.get("blurbSrc"):
                if hit.get("lang") != "ru":
                    continue
                b["blurbEn"] = b["blurb"]          # the English one is kept, just not shown
            if en_only and hit.get("lang") == "ru":
                continue
            b["blurb"] = hit["blurb"]
            b["blurbSrc"] = hit["url"]
            if hit.get("lang") == "ru":
                b["blurbLang"] = "ru"
            else:
                b.pop("blurbLang", None)
            n += 1
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("applied %d descriptions (backup: %s)" % (n, backup))
        return

    os.makedirs("tools/out", exist_ok=True)
    state = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"works": {}, "authorsDone": []}
    state.setdefault(done_key, [])
    if "--refresh" in args:
        refresh(state, allow_en)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        order = []
    missing = [b for b in manifest if b.get("author") in AUTHOR_PAGES and
               (not b.get("blurb") if not described else (b.get("blurb") and not b.get("blurbSrc")))]
    by_author = {}
    for b in missing:
        by_author.setdefault(b["author"], []).append(b)
    order = [] if "--refresh" in args else sorted(by_author, key=lambda a: -len(by_author[a]))
    if only:
        order = [only]
    for a in order:
        if a in state[done_key] and not only:
            continue
        books = by_author.get(a, [])
        print("%s — %d works" % (a, len(books)), flush=True)
        qid = author_qid(AUTHOR_PAGES[a])
        if not qid:
            print("  no Wikidata item for the author; skipped")
            continue
        works = works_of(qid)
        index = {}
        for w, d in works.items():
            for k in d["keys"]:
                index.setdefault(k, []).append(w)
        # 1. Wikidata title matches
        pick = {}
        for b in books:
            cands = index.get(norm(b.get("title")), [])
            cands = sorted(cands, key=lambda w: (not works[w]["en"], not works[w]["ru"]))
            for w in cands:
                if works[w]["en"] or works[w]["ru"]:
                    pick[b["filename"]] = {"ru": works[w]["ru"], "en": works[w]["en"]}
                    break
        # 2. Russian Wikipedia titles tried directly, checked against the author
        rest = [b for b in books if b["filename"] not in pick]
        tries = {}
        surname = re.split(r"[\s,]", AUTHOR_PAGES[a])[0]
        for b in rest:
            t = str(b.get("title") or "").strip()
            if not t:
                continue
            g = GENRES.get(b.get("category"), ["рассказ", "повесть"])
            for c in [t + " (" + x + ")" for x in g] + [t]:
                tries.setdefault(c, []).append(b["filename"])
        pages = direct_pages(list(tries))
        meta = p50_of(list({v[1] for v in pages.values() if v[1]}))
        for cand, (title, q) in pages.items():
            m = meta.get(q)
            if not m or qid not in m["authors"]:
                continue
            for fn in tries[cand]:
                if fn not in pick:
                    pick[fn] = {"ru": title, "en": m["en"]}
        # 3. The article openings
        ru_ex = {} if en_only else extracts("ru.wikipedia.org", sorted({p["ru"] for p in pick.values() if p["ru"]}))
        en_ex = extracts("en.wikipedia.org", sorted({p["en"] for p in pick.values() if p["en"] and (en_only or not p["ru"])})) if allow_en else {}
        got = 0
        for b in books:
            p = pick.get(b["filename"])
            if not p:
                continue
            if p["ru"] and p["ru"] in ru_ex:
                title, text = ru_ex[p["ru"]]
                host, lang = "ru.wikipedia.org", "ru"
            elif p["en"] and p["en"] in en_ex:
                title, text = en_ex[p["en"]]
                host, lang = "en.wikipedia.org", "en"
            else:
                continue
            blurb = lead(text)
            if len(blurb) < 25:
                continue
            state["works"][b["filename"]] = {
                "title": b.get("title"), "author": a, "lang": lang, "blurb": blurb,
                "url": wiki_url(host, title), "replaces": bool(b.get("blurb")),
            }
            got += 1
        print("  found %d of %d" % (got, len(books)), flush=True)
        if a not in state[done_key]:
            state[done_key].append(a)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
    with open(TSV, "w", encoding="utf-8") as f:
        f.write("author\ttitle\tlang\tdescription\tsource\n")
        for fn, h in sorted(state["works"].items(), key=lambda kv: (kv[1]["author"], kv[1]["title"] or "")):
            f.write("\t".join([h["author"], h["title"] or "", h["lang"], h["blurb"], h["url"]]) + "\n")
    w = state["works"]
    print("\n%d descriptions found (%d English, %d Russian) of %d works searched."
          % (len(w), sum(1 for h in w.values() if h["lang"] == "en"), sum(1 for h in w.values() if h["lang"] == "ru"), len(missing)))
    print("Review %s, then: python3 tools/wiki_blurbs.py --apply" % TSV)


if __name__ == "__main__":
    main()
