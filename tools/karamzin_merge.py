#!/usr/bin/env python3
"""Join the Karamzin volumes into one book, «История государства Российского».

Each volume becomes a part (<section> Том N) holding its chapters, so the
reader's contents nest Том > Глава the way Anna Karenina nests Часть > глава.
Wikisource repeats each chapter's full name as the first line(s) of the page
("Глава I. Великий князь Святополк. Годы 1015—1019"); that line becomes the
chapter's title and leaves the text, and the chapter opens on Karamzin's own
summary of its events.

    python3 tools/karamzin_merge.py      # after tools/karamzin.py
"""
import re, html, json, io

VOLS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '11', '12']
ROM = dict(zip(VOLS, ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'XI', 'XII']))
YEARS = re.compile(r'^(?:Г\.|г\.|Годы|Год)?\s*(\d{3,4})\s*[—–-]\s*(\d{3,4})\.?$')


def plain(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', x))).strip()


def sentence(t):
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) > 0.7 * len(letters):
        t = t.lower()
        t = t[:1].upper() + t[1:]
    return t


def chapter(sec):
    m = re.search(r'<title>\s*<p>(.*?)</p>\s*</title>', sec, re.S)
    if not m:
        return '<section>' + sec
    label = plain(m.group(1))
    if not re.fullmatch(r'Глава [IVXL]+', label):
        return '<section>' + sec
    rest = sec[m.end():]
    paras = list(re.finditer(r'\s*<p>([\s\S]*?)</p>', rest))
    name, years, used = [], None, 0
    for pm in paras[:4]:
        raw, txt = pm.group(1).strip(), plain(pm.group(1))
        strong = raw.startswith('<strong>') and raw.endswith('</strong>')
        txt = re.sub(r'^Глава [IVXL]+\.?\s*', '', txt).strip()
        y = YEARS.match(txt) or re.search(r'\.?\s*(?:Годы|Год|Г\.|г\.)\s*(\d{3,4})\s*[—–-]\s*(\d{3,4})\.?$', txt)
        # A summary is a run of short phrases; a heading is one name.
        is_summary = txt.count('. ') >= 3 and not strong
        if is_summary or len(txt) > 140:
            break
        if not (strong or len(txt) <= 110):
            break
        used = pm.end()
        if y:
            years = '%s—%s' % (y.group(1), y.group(2))
            txt = txt[:y.start()].strip() if not YEARS.match(txt) else ''
        txt = txt.rstrip('.').strip()
        if txt:
            name.append(sentence(txt))
    title = label
    # All-capitals headings lose their proper nouns' capitals in sentence();
    # these are the ones that do, set by hand.
    FIX = {'Великий князь ярополк': 'Великий князь Ярополк',
           'Великий князь владимир, названный в крещении василием': 'Великий князь Владимир, названный в крещении Василием',
           'Продолжение государствования иоаннова': 'Продолжение государствования Иоаннова'}
    name = [FIX.get(x, x) for x in name]
    # Ярополк's page sets the first lines of his summary as headings too.
    if name and name[0] == 'Великий князь Ярополк':
        name = name[:1]
    if name:
        title += '. ' + '. '.join(name)
    if years:
        title += ' (%s)' % years
    return '<section>\n<title><p>%s</p></title>%s' % (
        html.escape(title, quote=False), rest[used:]) if used else \
        '<section>\n<title><p>%s</p></title>%s' % (html.escape(title, quote=False), rest)


def main():
    out, words = [], 0
    for v in VOLS:
        t = io.open('public/books/novel/karamzin-igr-%s.fb2' % v, encoding='utf-8').read()
        body = t[t.index('<body>') + 6:t.rindex('</body>')].strip()
        body = re.sub(r'^<title>[\s\S]*?</title>', '', body).strip()
        secs = re.findall(r'<section>[\s\S]*?</section>', body)
        secs = [chapter(s[len('<section>'):]) if s.startswith('<section>') else s for s in secs]
        out.append('<section><title><p>Том %s</p></title>\n%s\n</section>' % (ROM[v], '\n'.join(secs)))
    fb2 = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">\n'
           '<description><title-info><genre>sci_history</genre><author><first-name>Николай</first-name>'
           '<last-name>Карамзин</last-name></author><book-title>История государства Российского</book-title>'
           '<lang>ru</lang></title-info></description>\n<body>\n' + '\n'.join(out) + '\n</body>\n</FictionBook>\n')
    io.open('public/books/novel/karamzin-igr.fb2', 'w', encoding='utf-8', newline='\n').write(fb2)
    words = len(re.findall(r'[А-Яа-яЁё]+', re.sub(r'<[^>]+>', ' ', fb2[fb2.index('<body>'):])))
    # One catalogue entry for the whole work, in place of the per-volume ones.
    idx = json.load(io.open('private/books/index.json', encoding='utf-8'))
    keep = [b for b in idx if not re.fullmatch(r'karamzin-igr-\d\d', b.get('slug') or '')]
    old = next((b for b in idx if b.get('slug') == 'karamzin-igr'), {})
    entry = dict(old)
    entry.update({
        'filename': 'novel/karamzin-igr.fb2', 'title': 'История государства Российского',
        'author': 'Карамзин Н.М.', 'category': 'History', 'slug': 'karamzin-igr', 'public': True,
        'words': words,
        'blurb': "Karamzin's great narrative history of Russia from the earliest peoples to the Time of "
                 "Troubles, the chronicles retold as one continuous story; every chapter opens with a "
                 "summary of its events. Wikisource lacks volume X and the end of volume VI.",
        '_note': 'Text from Russian Wikisource: https://ru.wikisource.org/wiki/'
                 '%D0%98%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F_%D0%B3%D0%BE%D1%81%D1%83%D0%B4%D0%B0%D1%80%D1%81%D1%82%D0%B2%D0%B0_'
                 '%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B9%D1%81%D0%BA%D0%BE%D0%B3%D0%BE_(%D0%9A%D0%B0%D1%80%D0%B0%D0%BC%D0%B7%D0%B8%D0%BD); '
                 'volumes I–IX, XI, XII (tools/karamzin.py, tools/karamzin_merge.py)',
    })
    if not old:
        keep.append(entry)
    else:
        keep = [entry if b.get('slug') == 'karamzin-igr' else b for b in keep]
    io.open('private/books/index.json', 'w', encoding='utf-8').write(json.dumps(keep, ensure_ascii=False, indent=2) + '\n')
    print('karamzin-igr.fb2: %d words; catalogue now %d entries' % (words, len(keep)))


if __name__ == '__main__':
    main()
