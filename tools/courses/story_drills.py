#!/usr/bin/env python3
"""Exercises from whole public-domain stories in the library — the stories an
intermediate reading course is built around, in their original text. Every
sentence of a story that shows one of the grammar themes (time, condition,
cause, concession, purpose, place, manner, negation, comparison,
indefiniteness, aspect, the cases) is filed; the answer is the story's own
word. Explanations are the DLI's sentences for each rule.

    python3 tools/courses/story_drills.py   → tools/courses/story_drills.json
"""
import hashlib, html, io, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
sys.argv = sys.argv[:1]
import case_drills as cd
import adv_drills as ad
import case_courses as cc

STORIES = [  # in the order an intermediate reading course takes them; txt: ones come from tools/fetch_stories.py
    ("kust-sireni", "novel/kust-sireni.fb2", "Александр Куприн", "Куст сирени", None),
    ("sostyazanie", "txt:sostyazanie", "Викентий Вересаев", "Состязание", None),
    ("nuncha", "novel/skazki-ob-italii.fb2", "Максим Горький", "Нунча («Сказки об Италии», XXII)", "Квартал святого Якова справедливо"),
    ("glupyy-frantsuz", "novel/glupyy-frantsuz.fb2", "Антон Чехов", "Глупый француз", None),
    ("na-dache", "novel/na-dache-chekhov.fb2", "Антон Чехов", "На даче", None),
    ("torgovoe", "novel/istoriya-odnogo-torgovogo-predpriyatiya.fb2", "Антон Чехов", "История одного торгового предприятия", None),
    ("attalea", "novel/attalea-princeps.fb2", "Всеволод Гаршин", "Attalea princeps", None),
    ("zelyonaya-lampa", "novel/zelyonaya-lampa.fb2", "Александр Грин", "Зелёная лампа", None),
    ("anna-na-shee", "novel/anna-na-shee-grouped.fb2", "Антон Чехов", "Анна на шее", None),
    ("smotritel", "novel/pushkin-povesti-belkina.fb2", "Александр Пушкин", "Станционный смотритель", "Станционный смотритель"),
    ("yolka", "novel/yolka-i-svadba.fb2", "Фёдор Достоевский", "Ёлка и свадьба", None),
    ("moya-ona", "novel/moya-ona.fb2", "Антон Чехов", "Моя «она»", None),
    # the file is the volume of letters, 1875–1886; the one letter is cut out of it
    ("pismo-bratu", "txt:pismo-bratu-nikolayu", "Антон Чехов", "Письмо брату Николаю (1886)", "Мне передавали, что ты оскорблен", "30 лет скоро! Пора!"),
    ("zhemchuzhnoe-ozherelie", "txt:zhemchuzhnoe-ozherelie", "Николай Лесков", "Жемчужное ожерелье", None),
]
THEMES = ["time:", "condconj", "cause", "concession", "chtoby", "complex", "loct:prep", "where", "home", "ablt:tool", "negpron", "negadv",
          "gent:neg", "comp", "sup:", "indef", "asp:", "poka", "timeconj", "short", "kotoryi", "svoi", "sebya", "gent:", "datv:", "accs:", "ablt:", "nomn:", "conj:", "sya", "pos"]
P = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
TAG = re.compile(r"<[^>]+>")
SENT = re.compile(r"(?<=[.!?…])\s+(?=[—–-]?\s*[А-ЯЁ«])")


def story_text(path, start, end=None):
    if path.startswith("txt:"):
        p = os.path.join(ROOT, "private", "stories", path[4:] + ".txt")
        paras = io.open(p, encoding="utf-8").read().split("\n")[1:] if os.path.exists(p) else []
        paras = [x.replace("\xa0", " ").replace("\u202f", " ").strip() for x in paras if x.strip()]
        if start:
            i = next((k for k, x in enumerate(paras) if x.startswith(start)), None)
            if i is not None:
                paras = paras[i:]
        if end:
            j = next((k for k, x in enumerate(paras) if end in x), None)
            if j is not None:
                paras = paras[:j + 1]
        return paras
    raw = io.open(os.path.join(ROOT, "public", "books", path), encoding="utf-8", errors="replace").read()
    body = raw.split("<body", 1)[-1]
    if start:
        k = body.find(start)
        if k < 0:
            return []
        body = body[k - 2000 if k > 2000 else 0:]
        # to the next section of the book
        m = re.search(r"<section", body[2500:])
        body = body[:2500 + m.start()] if m else body
    paras = []
    for para in P.findall(body):
        t = html.unescape(TAG.sub("", para)).replace("\xa0", " ").strip()
        if t:
            paras.append(t)
    if start:
        paras = paras[next((i for i, x in enumerate(paras) if x.startswith(start[:20])), 0):]
    return paras


def main():
    out = {}
    for row in STORIES:
        slug, path, author, title, start = row[:5]
        paras = story_text(path, start, row[5] if len(row) > 5 else None)
        if not paras:
            continue
        # The book's title page comes through as paragraphs — «Куприн А.И.»,
        # «Куст сирени» — before the story starts; they are not the story.
        surname = author.split()[-1].lower()
        short_title = title.split(" («")[0].lower()
        paras = [re.sub(r"\[\d+\]", "", x).strip() for x in paras]       # footnote marks
        def furniture(x):
            low = x.lower().strip()
            if re.match(r"^[а-яё-]+\s+[а-яё]\.\s*[а-яё]\.$", low):                       # «Куприн А.И.»
                return True
            if len(low) <= 70 and (low == short_title or low.rstrip(".") == short_title):   # the title, once or thrice
                return True
            if "если произведение является переводом" in low or "собрание сочинений" in low or "полное собрание" in low:
                return True                                                                   # Wikisource's licence line, the edition
            return len(low) <= 40 and surname in low and not re.search(r"[.!?…]\s+\S", low)
        while paras and furniture(paras[0]):
            paras = paras[1:]
        cite = "%s, «%s»" % (author, title.split(" («")[0])
        found = defaultdict(list)
        n_s = 0
        for para in paras:
            for s in SENT.split(para):
                s = re.sub(r"^[—–-]\s*", "", s.strip())
                if not (12 <= len(s) <= 140) or re.search(r"[A-Za-z\d]", s):
                    continue
                n_s += 1
                for key, d in cd.scan(s, "", cite):
                    e = cd.exercise(d, len(found[key]))
                    if e:
                        r = cc.rule_for(key)
                        if r:
                            e["why"] = r + " From %s." % cite
                        found[key].append(e)
                for key, d in ad.scan(s, "", cite):
                    e = ad.exercise(d, len(found[key]))
                    if e:
                        found[key].append(e)
        # in theme order, a few of each, round after round
        order = sorted(found, key=lambda k: next((i for i, t in enumerate(THEMES) if k.startswith(t)), 99))
        exs, seen = [], set()
        rnd = 0
        while len(exs) < 220 and any(len(found[k]) > rnd for k in order):
            for k in order:
                if len(found[k]) > rnd:
                    e = found[k][rnd]
                    sk = e.get("q", "") + e.get("ru", "")
                    if sk not in seen:
                        seen.add(sk); exs.append(e)
            rnd += 1
        out[slug] = {"author": author, "title": title, "intro": paras[:3], "story": paras, "exercises": exs}
        print("%-16s %4d sentences, %3d exercises" % (slug, n_s, len(exs)), flush=True)
    io.open(os.path.join(HERE, "story_drills.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
