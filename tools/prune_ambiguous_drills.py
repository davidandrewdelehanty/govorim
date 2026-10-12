#!/usr/bin/env python3
# Removes case drills with more than one grammatical answer, and decodes HTML
# entities (&nbsp; and the like) left in drill text. Run from the repo root:
#   python3 tools/prune_ambiguous_drills.py 0 99999 --write
# Needs pymorphy3. Rules, each a place where another option would also be
# correct Russian with a different meaning:
#   prep-two-cases       в/на/за/под/с/по/о take two cases (в дом / в доме)
#   nom-or-instr         straight after был/стал/... (был учитель / учителем)
#   gen-or-acc           after не/ни/нет or ждать, искать, хотеть... (ждать поезд / поезда)
#   after-noun-genitive  right after a noun, a genitive also fits (письмо брату / брата)
#   not-a-case-drill     the label names no case

import json,os,re,sys,time,collections,html
from functools import lru_cache
import pymorphy3
M=pymorphy3.MorphAnalyzer()
D='public/books/exercises'
LABEL=[('Именит','nomn'),('Родит','gent'),('Датель','datv'),('Винит','accs'),('Творит','ablt'),('Предложн','loct')]
NORM={'gen2':'gent','gen1':'gent','acc2':'accs','loc2':'loct','loc1':'loct','voct':'nomn'}
PREP={'в':{'accs','loct'},'во':{'accs','loct'},'на':{'accs','loct'},'за':{'accs','ablt'},'под':{'accs','ablt'},'подо':{'accs','ablt'},
      'с':{'gent','ablt'},'со':{'gent','ablt'},'по':{'datv','loct','accs'},'о':{'loct','accs'},'об':{'loct','accs'},'обо':{'loct','accs'}}
ONEPREP={'к','ко','от','ото','из','изо','у','для','без','до','при','через','про','над','надо','перед','передо','между','около','возле','после','среди','вокруг','из-за','из-под','ради','кроме','мимо','сквозь','вместо','напротив','вдоль','против','благодаря','согласно','вопреки','навстречу','подле','близ','вне','внутри'}
COPULA=re.compile(r'(был|была|было|были|быть|будет|будут|будь|будучи|стал|стала|стало|стали|стать|станет|станут|становится|становился|являлся|являлась|является|являются|казался|казалась|кажется|оказался|оказалась|оказались|считался|считалась|остался|осталась|остались|сделался|сделалась|служил|работал|слыл|назвал|назвали|звали|зовут)',re.I)
GENACC=re.compile(r'(жд\w*|ожида\w*|иска\w*|ищ(?:у|ет|ут|ешь|ем|ете|ут|а|ущ\w*)|хоте\w*|хоч\w*|проси(?:ть|л|ла|ло|ли|т|м|шь|те)|прош(?:у|у)|требова\w*|требу\w*|жела\w*|добива\w*|добил\w*|достиг\w*)',re.I)
W=re.compile(r"[А-Яа-яЁё-]+")
@lru_cache(maxsize=None)
def parses(w): return M.parse(w.lower())
def cases_of(phrase, lemma, number=None):
    words=W.findall(phrase)
    if not words: return set(),None
    tot=None; num=None
    for w in words:
        ps=parses(w)
        head=[p for p in ps if p.normal_form==lemma.lower().replace('ё','е') or p.normal_form==lemma.lower()]
        use=head or [p for p in ps if p.tag.POS in ('NOUN','ADJF','PRTF','NPRO','NUMR','ADJS') ] or ps
        if number: use=[p for p in use if (p.tag.number in (number,None))] or use
        cs={NORM.get(p.tag.case,p.tag.case) for p in use if p.tag.case}
        if head and num is None: num=head[0].tag.number
        tot=cs if tot is None else (tot & cs or tot|cs)
    return tot or set(), num
def label_case(lbl):
    l=(lbl or '').lower()
    for k,v in LABEL:
        if k.lower() in l: return v
    return None
def nounish(w):
    ps=parses(w)
    return ps and ps[0].tag.POS=='NOUN' and ps[0].score>0.5
def verdict(c):
    lc=label_case(c.get('case'))
    if not lc: return 'not-a-case-drill'
    s=c['sentence']; corr=c['correct']
    _,num=cases_of(corr,c['lemma'])
    other=set()
    for o in c['options']:
        if o==corr: continue
        cs,_=cases_of(o,c['lemma'],num)
        other|=cs
    other.discard(lc)
    before=W.findall(s.split('___')[0])
    after=W.findall(s.split('___',1)[1]) if '___' in s else []
    prev=before[-1].lower() if before else ''
    if prev in PREP:
        alt=PREP[prev]-{lc}
        if lc in PREP[prev] and other & alt: return 'prep-two-cases:'+prev
        return None
    if prev in ONEPREP: return None
    # Negation and verbs taking either case: genitive or accusative.
    ctx=[w.lower() for w in before[-3:]]
    genacc = any(w in ('не','ни','нет') for w in ctx) or any(GENACC.fullmatch(w) for w in ctx if w not in ('нет','ни'))
    if {lc}|other >= {'accs','gent'} and lc in ('accs','gent') and genacc:
        return 'gen-or-acc'
    if {lc}|other >= {'nomn','ablt'} and lc in ('nomn','ablt') and COPULA.fullmatch(prev or '-'):
        return 'nom-or-instr'
    # Right after a noun almost anything can also be a genitive of that noun.
    pp=parses(prev)[0] if prev else None
    if (prev and lc in ('datv','ablt','accs') and 'gent' in other and nounish(prev)
            and not ({'Name','Surn','Patr','Geox'} & set(pp.tag.grammemes))
            and lc not in {NORM.get(x.tag.case,x.tag.case) for x in parses(prev) if x.tag.POS=='NOUN'}):
        return 'after-noun-genitive'
    # Who does what to whom: subject and object can swap when another noun
    # in the sentence could itself be either.
    blank_anim=any(p.tag.animacy=='anim' for p in parses(W.findall(corr)[-1]) if p.normal_form==c['lemma'].lower()) if W.findall(corr) else False
    if False and lc in ('nomn','accs') and {'nomn','accs'} <= ({lc}|other) and blank_anim:
        for w in before+after:
            ps=parses(w)
            top=ps[0] if ps else None
            if not top or top.tag.POS!='NOUN' or top.tag.animacy!='anim': continue
            cs={NORM.get(p.tag.case,p.tag.case) for p in ps if p.tag.POS=='NOUN' and p.normal_form==top.normal_form}
            if {'nomn','accs'} <= cs:
                return 'subject-or-object'
    return None
if __name__=='__main__':
    start,end=int(sys.argv[1]),int(sys.argv[2]); write='--write' in sys.argv
    names=sorted(n for n in os.listdir(D) if n.endswith('.json') and not n.startswith('_'))[start:end]
    st=collections.Counter(); ex=collections.defaultdict(list); t0=time.time(); last=start
    for i,n in enumerate(names):
        if time.time()-t0>140: break
        last=start+i+1
        p=os.path.join(D,n); j=json.load(open(p,encoding='utf-8'))
        cs=j.get('cases') or []; keep=[]; changed=False
        for c in cs:
            # HTML entities left in the text (&nbsp; and the like).
            for k in ('sentence','correct','explain'):
                if isinstance(c.get(k),str) and '&' in c[k]:
                    v=html.unescape(c[k]).replace(' ',' ') if k!='sentence' else html.unescape(c[k])
                    if v!=c[k]: c[k]=v; changed=True; st['entity-fixed']+=1
            if isinstance(c.get('options'),list):
                nv=[html.unescape(o) for o in c['options']]
                if nv!=c['options']: c['options']=nv; changed=True
            v=verdict(c); st['total']+=1
            if v:
                st[v.split(':')[0]]+=1
                if len(ex[v.split(':')[0]])<12: ex[v.split(':')[0]].append((s:=c['sentence'], c['correct'], [o for o in c['options'] if o!=c['correct']]))
                changed=True
            else: keep.append(c)
        if changed and write:
            j['cases']=keep
            with open(p,'w',encoding='utf-8') as f: json.dump(j,f,ensure_ascii=False,indent=1)
    out=os.path.expanduser('~/xl/amb_%d.json'%start)
    json.dump({'st':st,'ex':ex,'last':last},open(out,'w'),ensure_ascii=False)
    print('NEXT',last,'of',start+len(names), dict(st), round(time.time()-t0))
