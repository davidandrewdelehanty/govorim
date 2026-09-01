#!/usr/bin/env python3
"""Build Стихотворения в прозе: FB2 from az.lib Senilia + Garnett pairing."""
import html, io, json, os, re, sys
sys.path.insert(0, 'tools')
from pair_chapter import pair_prop

t = open('tools/sources/senilia.html','rb').read().decode('cp1251')
body = t[:t.find('ПРИМЕЧАНИЯ')]

# tokenize: centered heads and dd paragraphs, in document order
toks = []
for m in re.finditer(r'<div align="center" >\s*<p >\s*(.*?)\s*</p>\s*</div>|<dd>(.*?)(?=<dd>|<div align="center"|$)', body, re.S):
    if m.group(1) is not None:
        txt = html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>','',m.group(1)))).replace('\xa0',' ')
        txt = re.sub(r'\s+',' ',txt).strip()
        if txt: toks.append(('h', m.start(), txt))
    else:
        txt = html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>','',m.group(2)))).replace('\xa0',' ')
        txt = re.sub(r'\s+',' ',txt).strip()
        if txt: toks.append(('p', m.start(), txt))

# index heads
heads = [(i,tok[2]) for i,tok in enumerate(toks) if tok[0]=='h']
hn = 0
headnum = {}   # running head number -> token index
for i,tok in enumerate(toks):
    if tok[0]=='h':
        headnum[hn]=i; hn+=1

SUBS = set([14] + list(range(22,40)) + [46,47] + list(range(69,75)) + [83,88,90,105,115])
FIX = {
 'К ЧИТАТЕЛЮ':'К читателю','"УСЛЫШИШЬ СУД ГЛУПЦА..."':'«Услышишь суд глупца…»',
 'ПАМЯТИ Ю. П. ВРЕВСКОЙ':'Памяти Ю. П. Вревской','NECESSITAS, VIS, LIBERTAS {*}':'Necessitas, Vis, Libertas',
 'Н. Н.':'Н. Н.','"ПОВЕСИТЬ ЕГО!"':'«Повесить его!»','ЧТО Я БУДУ ДУМАТЬ?..':'Что я буду думать?..',
 '"КАК ХОРОШИ, КАК СВЕЖИ БЫЛИ РОЗЫ..."':'«Как хороши, как свежи были розы…»',
 'МЫ ЕЩЕ ПОВОЮЕМ!':'Мы еще повоюем!','ЗАВТРА! ЗАВТРА!':'Завтра! Завтра!',
 'МНЕ ЖАЛЬ...':'Мне жаль…','С КЕМ СПОРИТЬ...':'С кем спорить…',
 '"О МОЯ МОЛОДОСТЬ! О МОЯ СВЕЖЕСТЬ!"':'«О моя молодость! о моя свежесть!»','К ***':'К ***',
 'Я ШЕЛ СРЕДИ ВЫСОКИХ ГОР...':'Я шел среди высоких гор…','КОГДА МЕНЯ НЕ БУДЕТ...':'Когда меня не будет…',
 'Я ВСТАЛ НОЧЬЮ...':'Я встал ночью…','КОГДА Я ОДИН':'Когда я один… (Двойник)',
 'NESSUN MAGGIOR DOLORE {*}':'Nessun maggior dolore','У-А... У-А!':'У-а… У-а!','ТЫ ЗАПЛАКАЛ...':'Ты заплакал…',
 'ПОСЛЕДНЕЕ СВИДАНИЕ':'Последнее свидание','СТОЙ!':'Стой!','ДВА ЧЕТВЕРОСТИШИЯ':'Два четверостишия',
}
def rutitle(h):
    if h in FIX: return FIX[h]
    return h.capitalize()

poems = []   # (title, [paras])
title_heads = [n for n in range(3,119) if n not in SUBS and n not in (88,90)]
for k,hnum in enumerate(title_heads):
    ti = headnum[hnum]
    name = toks[ti][2]
    if hnum==82: name='Встреча (Сон)'
    elif hnum==87: name='Дрозд (I)'
    elif hnum==89: name='Дрозд (II)'
    else: name=rutitle(name)
    end = headnum[title_heads[k+1]] if k+1<len(title_heads) else len(toks)
    paras=[]
    j=ti+1
    while j<end:
        typ,_,txt=toks[j]
        if typ=='h':
            n2=[n for n,i2 in headnum.items() if i2==j][0]
            if n2 in (88,90): j+=1; continue
            paras.append(txt)
        else:
            paras.append(txt)
        j+=1
    paras=[p for p in paras if p]
    poems.append((name,paras))

print("poems:",len(poems))
for nm,ps in poems[:3]+poems[-2:]: print(" ",nm,len(ps),"|",ps[0][:60])

# ---- FB2 ----
def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
out=io.StringIO()
out.write('<?xml version="1.0" encoding="utf-8"?>\n')
out.write('<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">\n')
out.write('<description><title-info><genre>prose_classic</genre>'
          '<author><first-name>Иван</first-name><middle-name>Сергеевич</middle-name><last-name>Тургенев</last-name></author>'
          '<book-title>Стихотворения в прозе</book-title><lang>ru</lang></title-info>'
          '<document-info><program-used>tools/build_senilia.py</program-used>'
          '<src-url>http://az.lib.ru/t/turgenew_i_s/text_0920.shtml</src-url><version>1.0</version></document-info>'
          '</description>\n<body>\n<title><p>Стихотворения в прозе</p></title>\n')
for nm,ps in poems:
    out.write('<section>\n<title><p>%s</p></title>\n'%esc(nm))
    for p in ps: out.write('<p>%s</p>\n'%esc(p))
    out.write('</section>\n')
out.write('</body>\n</FictionBook>\n')
io.open('public/books/novel/stikhotvoreniya-v-proze.fb2','w',encoding='utf-8').write(out.getvalue())
print("FB2 written")
