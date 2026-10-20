#!/usr/bin/env python3
"""Remove exercises that do not exercise the thing their course teaches.

The time course was harvested by PREPOSITION (на/за + accusative), so it caught
"Спасибо за обед", "Сели за ужин", "Что за праздник?" — right preposition,
nothing to do with time. Same trap for any course whose subject is semantic
rather than purely grammatical.

Removed items are written to _dropped/<course>.json rather than deleted, so a
wrong call can be put back.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/drop_offtopic.py --course time
    python3 tools/courses/drop_offtopic.py --course time --apply
"""
import argparse, io, json, os, re

ROOT = "public/courses"
# A course is only checkable when its subject shows in the words themselves.
LEXICON = {
    # год(?!ит) so годы/годам count but "годится" (to suit) does not.
    "time": r"(час|минут|секунд|врем|год(?!ит)|лет\b|лета\b|мес[яц]|недел|дня|дней|день|дне|сутк|утр|вечер|ноч|днём|днем|полдень|полноч|полчаса|четверт|сегодня|вчера|завтра|сейчас|пора|срок|рано|поздно|долго|давно|когда|тогда|теперь|всегда|никогда|часто|редко|иногда|пока\b|сразу|потом|début|понедельник|вторник|сред|четверг|пятниц|суббот|воскрес|январ|феврал|март|апрел|ма[йя]\b|июн|июл|август|сентябр|октябр|ноябр|декабр|весн|осен|зим|лето|каникул|возраст|эпох|век\b|века|веко|\d)",
    # cardinals, ordinals and quantity words alike — "(первый)" is a number too.
    "count": r"(\d|один|одна|одно|два|две|три|четыр|пят|шест|сем|восьм|восем|девят|десят|одиннадц|двенадц|двадц|тридц|сорок|пятьдесят|сто\b|сот|тысяч|миллион|миллиард|перв|втор|трет|дво[еи]|тро[еи]|четвер|пятер|шестер|седьм|семер|восьмер|девятер|десятер|девяност|сколько|много|мало|немного|несколько|пар[аы]|оба|обе|половин|полтора|дюжин|номер|раз\b|раза\b|счёт|счет|количеств|больше|меньше)",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.course not in LEXICON:
        raise SystemExit("no lexicon for %r — only %s are checkable this way"
                         % (args.course, ", ".join(sorted(LEXICON))))
    # Match with ё folded to е: "четвёртый" must hit the stem "четверт", and the
    # whole codebase treats the two as one letter anyway.
    rx = re.compile(LEXICON[args.course].replace("ё", "е"), re.I)
    fold = lambda t: t.replace("ё", "е").replace("Ё", "Е")
    d = os.path.join(ROOT, args.course)
    dropped, kept, files = [], 0, 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        p = os.path.join(d, f)
        doc = json.load(io.open(p, encoding="utf-8"))
        exs = doc.get("exercises") or []
        if not exs:
            continue
        keep = []
        for e in exs:
            blob = fold(" ".join(str(e.get(k) or "") for k in ("q", "prompt", "ru")))
            (keep if rx.search(blob) else dropped).append(e if rx.search(blob) else
                                                          dict(e, _from=f))
        kept += len(keep)
        if len(keep) != len(exs):
            files += 1
            doc["exercises"] = keep
            if args.apply:
                io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print("%s: keeping %d, dropping %d, across %d file(s)" % (args.course, kept, len(dropped), files))
    for e in dropped[:6]:
        print("   drop: %s" % (str(e.get("q") or "")[:90]))
    if args.apply:
        out = "tools/courses/_dropped"
        os.makedirs(out, exist_ok=True)
        io.open(os.path.join(out, args.course + ".json"), "w", encoding="utf-8").write(
            json.dumps(dropped, ensure_ascii=False, indent=1))
        print("\ndropped items saved to %s/%s.json" % (out, args.course))
    else:
        print("\nreport only — add --apply to write")


if __name__ == "__main__":
    main()
