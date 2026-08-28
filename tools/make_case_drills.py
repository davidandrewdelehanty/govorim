#!/usr/bin/env python3
# Case-drill generator: adjective+noun declension exercises harvested from a
# book's own sentences, with the English line taken from the book's parallelEn
# translation. Runs OFFLINE (WSL) — the site stays AI-free; output is the same
# static JSON the exercises tab already reads.
#
#     # WSL, once:  pip install pymorphy3 natasha
#     cd /mnt/c/Users/david/projects/govorim-app
#     python3 tools/make_case_drills.py --book moskva-petushki.fb2
#     python3 tools/make_case_drills.py --all-parallel        # every tagged book
#
# Reliability by construction, not by model:
#   - candidate pairs come from the dependency parse (Natasha) and are kept
#     ONLY if adjective and noun agree in case/number/gender AND pymorphy3
#     independently confirms both readings — anything ambiguous is discarded;
#   - the option list is built by pymorphy3 dictionary inflection (deterministic);
#   - the correct answer is the surface form from the text, by definition;
#   - no English: a translator's sentence rarely maps 1:1 onto the Russian,
#     so the drill shows the Russian sentence alone.
#
# Output: public/books/exercises/<slug>__ch<cidx>.json  {"cases":[...]}
# Existing files are left alone unless --force.

import argparse, json, os, re, sys, hashlib, random

# ── FB2 → chapters (same logic as the reader; trimmed port) ──────────────────
import xml.etree.ElementTree as ET
HOMO={'Х':'X','І':'I','Ѵ':'V','С':'C','М':'M','Д':'D'}
MARK_RE=re.compile(r'^(?:глава\s+)?([ivxlcdm]+)\.?(?:\s+\S[\s\S]*)?$',re.I)
DECO=r'[\s*_·•—–\-.,:;!?()"\'«»\[\]]*'
NOTES_RE=re.compile('^'+DECO+r'(сноски?|примечани[ея]|комментари[ий]|notes?|footnotes?|endnotes?)'+DECO+'$',re.I)
MIN_MEDIAN=150
def chapter_marker(t):
    s=(t or '').strip()
    if not s: return ''
    s=''.join(HOMO.get(c,c) for c in s)
    m=MARK_RE.match(s)
    return m.group(1).upper() if m else ''
def text_of(el): return ' '.join(''.join(el.itertext()).split())

def read_fb2(path):
    """Read an FB2 as text, honouring the encoding its XML declaration names.

    Four books in this library are windows-1251 (Мёртвые души, Смерть Ивана
    Ильича, Отцы и дети, Преступление и наказание). Decoding those as UTF-8
    with errors='replace' turns every Cyrillic byte into U+FFFD, so the
    ">=5 Cyrillic characters" test in push() rejects every chapter and the
    book silently extracts as "0 chapters".
    """
    raw = open(path, 'rb').read()
    m = re.search(rb'encoding=["\']([\w-]+)["\']', raw[:400])
    enc = m.group(1).decode('ascii') if m else 'utf-8'
    try:
        return raw.decode(enc, errors='replace')
    except LookupError:
        return raw.decode('utf-8', errors='replace')
def bible_chapters(path):
    """Scripture mode: one chapter per 'Глава N' section, verse-split paragraphs
       exactly as the reader produces them (Testament > Book > Chapter)."""
    raw=read_fb2(path)
    raw=re.sub(r'\sxmlns(:\w+)?="[^"]*"','',raw)
    raw=re.sub(r'\s\w+:(\w+)="[^"]*"',r' \1="x"',raw)
    root=ET.fromstring(raw)
    bodies=[b for b in root if b.tag=='body']
    main=next((b for b in bodies if not b.get('name')), bodies[0])
    sections=[c for c in main if c.tag=='section']
    def title_of(sec):
        t=next((c for c in sec if c.tag=='title'),None)
        return text_of(t) if t is not None else ''
    chapters=[]
    def gather(sec):
        out=[]
        dt=next((c for c in sec if c.tag=='title'),None)
        for node in sec.iter():
            if node.tag in ('title','subtitle'): continue
            if node.tag in ('p','v'):
                t=' '.join(''.join(node.itertext()).split())
                if not t: continue
                t=re.sub(r'([.!?…»"])\s+(?=\d{1,3}\s[«"„(\[—–А-ЯЁ])', '\\1\n\n', t)
                out.append(t)
        return '\n\n'.join(out)
    def is_chap(t): return bool(re.match(r'^(глава|псалом|песнь)\s*\d+',t,re.I))
    def emit(sec,testament,book):
        te=title_of(sec)
        childs=[c for c in sec if c.tag=='section']
        if is_chap(te):
            body=gather(sec)
            if len(re.findall(r'[а-яёА-ЯЁ]',body))>=5:
                chapters.append({'heading':' — '.join(x for x in (testament,book,te) if x),'text':body})
            return
        if childs:
            anychap=any(is_chap(title_of(c)) for c in childs)
            if anychap:
                for c in childs: emit(c,testament,te)
            else:
                deeper=any(any(x.tag=='section' for x in c) for c in childs)
                if deeper:
                    if not testament:
                        for c in childs: emit(c,te,'')
                    else:
                        for c in childs: emit(c,testament,book)
                else:
                    body=gather(sec)
                    if len(re.findall(r'[а-яёА-ЯЁ]',body))>=5:
                        chapters.append({'heading':' — '.join(x for x in (testament,book or te,'Глава 1') if x),'text':body})
        else:
            body=gather(sec)
            if len(re.findall(r'[а-яёА-ЯЁ]',body))>=5:
                chapters.append({'heading':' — '.join(x for x in (testament,book or te,'Глава 1') if x),'text':body})
    for sec in sections: emit(sec,'','')
    for c in chapters:
        c['paras']=[p for p in re.split(r'\n{2,}',c['text']) if p.strip()]
    return chapters

def fb2_chapters(path):
    raw=read_fb2(path)
    raw=re.sub(r'\sxmlns(:\w+)?="[^"]*"','',raw)
    raw=re.sub(r'\s\w+:(\w+)="[^"]*"',r' \1="x"',raw)
    root=ET.fromstring(raw)
    bodies=[b for b in root if b.tag=='body']
    main=next((b for b in bodies if not b.get('name')), bodies[0])
    sections=[c for c in main if c.tag=='section']
    def title_of(sec):
        t=next((c for c in sec if c.tag=='title'),None)
        return text_of(t) if t is not None else ''
    def paras_of(sec,own):
        out=[]
        def walk(el):
            for c in el:
                if c.tag=='section':
                    if not own: walk(c)
                elif c.tag=='title': continue
                elif c.tag in ('p','v','subtitle'):
                    t=text_of(c)
                    if t: out.append(t)
                else: walk(c)
        walk(sec); return out
    def wcount(t): return len(re.findall(r'\S+',t))
    def push(out,heading,paras):
        body='\n\n'.join(paras)
        if len(re.findall(r'[а-яёА-ЯЁ]',body))>=5:
            out.append({'heading':heading or 'Глава %d'%(len(out)+1),'text':body})
    def walk_section(sec,out):
        nested=[c for c in sec if c.tag=='section']
        part=title_of(sec)
        if NOTES_RE.match(part.strip()): return
        grand=any(any(g.tag=='section' for g in c) for c in nested)
        if nested and not grand:
            unt=sum(1 for c in nested if not title_of(c))
            if unt*3>len(nested): nested=[]
        subs=[c for c in sec if c.tag=='subtitle' and chapter_marker(text_of(c))]
        distinct={chapter_marker(text_of(c)) for c in subs}
        if not nested and len(distinct)>=2:
            split=[]; ms=set(id(x) for x in subs); cur=None; ps=[]
            def flush():
                if cur is None: return
                b='\n\n'.join(ps)
                if len(re.findall(r'[а-яёА-ЯЁ]',b))>=5:
                    split.append({'heading':(part+' — ' if part else '')+cur,'text':b})
            for ch in sec:
                if ch.tag=='title': continue
                t=text_of(ch)
                if ch.tag=='subtitle' and id(ch) in ms:
                    flush(); cur=t; ps=[]; continue
                if t and cur is not None: ps.append(t)
            flush()
            sizes=sorted(wcount(c['text']) for c in split)
            if len(split)>=2 and sizes and sizes[len(sizes)//2]>=MIN_MEDIAN:
                out.extend(split); return
        if not nested:
            leaf=paras_of(sec,False)
            if not part and wcount(' '.join(leaf))<MIN_MEDIAN: return
            push(out,part,leaf); return
        sub=[]; push(sub,part,paras_of(sec,True))
        for n in nested: walk_section(n,sub)
        sizes=sorted(wcount(c['text']) for c in sub)
        if sub and sizes[len(sizes)//2]<MIN_MEDIAN:
            push(out,part,paras_of(sec,False)); return
        out.extend(sub)
    chapters=[]
    for s in sections: walk_section(s,chapters)
    bt=root.find('.//book-title'); title=text_of(bt) if bt is not None else ''
    if re.search(r'Каренин',title,re.I) and chapters:
        ded='«Мне отмщение и Аз воздам»'
        if ded not in chapters[0]['text']: chapters[0]['text']=ded+'\n\n'+chapters[0]['text']
    if re.search(r'Война и мир',title,re.I) and chapters:
        intro='Лев Николаевич Толстой. Война и мир. Том первый. Часть первая. Глава первая.'
        if intro not in chapters[0]['text']: chapters[0]['text']=intro+'\n\n'+chapters[0]['text']
    if re.search(r'Каренин',title,re.I) and len(chapters)==240:
        for ci in range(len(chapters)-1):
            if len(chapters[ci]['text'])<1000:
                chapters[ci]['text']+='\n\n'+chapters[ci+1]['text']; del chapters[ci+1]; break
    for c in chapters:
        c['paras']=[p for p in re.split(r'\n{2,}',c['text']) if p.strip()]
    return chapters

# ── NLP ──────────────────────────────────────────────────────────────────────
try:
    import pymorphy3
    from natasha import Segmenter, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, Doc
except ImportError as e:
    sys.exit("Missing NLP packages (%s).\nInstall once with:  pip install pymorphy3 natasha" % e)

MORPH=pymorphy3.MorphAnalyzer()
SEG=Segmenter(); EMB=NewsEmbedding()
TAGGER=NewsMorphTagger(EMB); SYNTAX=NewsSyntaxParser(EMB)

CASES=['nomn','gent','datv','accs','ablt','loct']
CASE_UD={'Nom':'nomn','Gen':'gent','Dat':'datv','Acc':'accs','Ins':'ablt','Loc':'loct'}
CASE_LABEL={'nomn':'Именительный (Nominative)','gent':'Родительный (Genitive)',
            'datv':'Дательный (Dative)','accs':'Винительный (Accusative)',
            'ablt':'Творительный (Instrumental)','loct':'Предложный (Prepositional)'}
CASE_WHY={'nomn':'the subject of the sentence stands in the nominative',
          'gent':'the genitive here marks possession, absence, or quantity',
          'datv':'the dative marks the indirect object or recipient',
          'accs':'the accusative marks the direct object of the verb',
          'ablt':'the instrumental marks the means, company, or complement',
          'loct':'the prepositional is used only after a preposition, for location or topic'}

def sentences(par):
    out=[];cur=0
    for m in re.finditer(r'(?<=[.!?…])\s+(?=[А-ЯЁ«—•(])',par):
        out.append(par[cur:m.start()+1]); cur=m.end()
    out.append(par[cur:])
    return [s.strip() for s in out if s.strip()]

def confirm(word, lemma_pos, case, number):
    """pymorphy3 must offer a reading of `word` with this POS/case/number."""
    for p in MORPH.parse(word):
        t=p.tag
        if lemma_pos in t and case in t and (number is None or number in t):
            return p
    return None

def inflect_pair(adj_p, noun_p, case, number):
    gs={case}
    if number: gs.add(number)
    n2=noun_p.inflect(gs)
    if not n2: return None
    ag={case}
    if number: ag.add(number)
    g=noun_p.tag.gender
    if g and (number!='plur'): ag.add(g)
    if case=='accs':
        anim=noun_p.tag.animacy
        if anim: ag.add(anim)
    a2=adj_p.inflect(ag)
    if not a2: return None
    return a2.word, n2.word

def drills_for_sentence(sent, seed):
    if not (25<=len(sent)<=220): return []
    doc=Doc(sent)
    doc.segment(SEG); doc.tag_morph(TAGGER); doc.parse_syntax(SYNTAX)
    toks={t.id:t for t in doc.tokens}
    out=[]
    for t in doc.tokens:
        if t.rel!='amod' or t.pos!='ADJ': continue
        head=toks.get(t.head_id)
        if head is None or head.pos!='NOUN': continue
        fa,fn=t.feats or {}, head.feats or {}
        if fa.get('Case')!=fn.get('Case') or fa.get('Number')!=fn.get('Number'): continue
        ud=fa.get('Case')
        case=CASE_UD.get(ud)
        if not case: continue
        number='plur' if fa.get('Number')=='Plur' else 'sing'
        # adjacency: adjective directly before its noun in the raw text
        if not re.search(re.escape(t.text)+r'\s+'+re.escape(head.text), sent): continue
        ap=confirm(t.text,'ADJF',case,number)
        np_=confirm(head.text,'NOUN',case,number)
        if not ap or not np_: continue
        # inflection bases: the dictionary (lemma) parses with the right POS
        def base(lemma,pos):
            for cand in MORPH.parse(lemma):
                if pos in cand.tag: return cand
            return None
        ab, nb = base(ap.normal_form,'ADJF'), base(np_.normal_form,'NOUN')
        if not ab or not nb: continue
        # build distinct options across cases
        opts={}
        for c in CASES:
            pair=inflect_pair(ab, nb, c, number)
            if pair: opts[c]=pair[0]+' '+pair[1]
        correct=t.text+' '+head.text
        # the correct case's generated form must equal the text form (guards
        # against homonym parses); if not, drop the candidate entirely
        if opts.get(case,'').lower()!=correct.lower(): continue
        distinct={}
        if case in opts:
            distinct[case]=opts[case]
        for c,o in opts.items():
            if c==case: continue
            if o.lower() not in {v.lower() for v in distinct.values()}:
                distinct[c]=o
        if len(distinct)<4 or case not in distinct: continue
        rnd=random.Random(seed+correct)
        others=[c for c in distinct if c!=case]
        pick=rnd.sample(others,3)
        options=[distinct[case]]+[distinct[c] for c in pick]
        rnd.shuffle(options)
        blanked=re.sub(re.escape(t.text)+r'\s+'+re.escape(head.text),'___',sent,count=1)
        # preposition governing the noun?
        prep=None
        for t2 in doc.tokens:
            if t2.head_id==head.id and t2.pos=='ADP': prep=t2.text.lower()
        why=CASE_WHY[case]
        if prep: why='after the preposition «%s», %s'%(prep,why.split(', ',1)[-1] if case=='loct' else why)
        out.append({'sentence':blanked,'lemma':np_.normal_form,
                    'options':options,'correct':distinct[case],
                    'case':CASE_LABEL[case],
                    'explain':'«%s %s» — %s.'%(t.text,head.text,why)})
    return out

# RETIRED. This picked the English sentence sitting at roughly the same position
# within the paragraph, which is a guess and was wrong often enough to be worse
# than nothing: translators merge and split sentences, so drill 3 of a 5-sentence
# paragraph routinely showed the English of a neighbouring clause. A case drill
# does not need the English — the Russian sentence is the whole prompt — so the
# field is no longer generated, and the reader no longer displays it.
# Kept here (unused) because the position-mapping idea is still the right
# starting point if per-sentence alignment is ever built properly.
def sentence_translation(en_par, ridx, rtotal):
    """Pick the EN sentence at roughly the same position in the paragraph."""
    if not en_par: return ''
    es=sentences(en_par)
    if len(es)<=1: return en_par
    k=min(len(es)-1, round(ridx/max(rtotal-1,1)*(len(es)-1)))
    return es[k]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',default='/mnt/c/Users/david/projects/govorim-app')
    ap.add_argument('--book',help='FB2 filename as in the catalogue, e.g. moskva-petushki.fb2')
    ap.add_argument('--all-parallel',action='store_true')
    ap.add_argument('--max-per-chapter',type=int,default=100000)
    ap.add_argument('--force',action='store_true')
    ap.add_argument('--bible',action='store_true',help='Bible only')
    ap.add_argument('--all',action='store_true',help='every parallelEn book AND the Bible')
    a=ap.parse_args()
    idx=json.load(open(os.path.join(a.repo,'private/books/index.json'),encoding='utf-8'))
    if a.all: a.all_parallel=True
    if a.bible:
        run_bible(a, idx); return
    books=[b for b in idx if 'parallelEn' in b]
    if a.book: books=[b for b in books if b['filename'].endswith('/'+a.book) or b['filename']==a.book]
    if not a.all_parallel and not a.book and not a.all:
        sys.exit('Pick --book <file.fb2>, --all-parallel, --bible, or --all. Tagged books:\n  '+
                 '\n  '.join(b['filename'] for b in [x for x in idx if 'parallelEn' in x]))
    outdir=os.path.join(a.repo,'public/books/exercises')
    os.makedirs(outdir,exist_ok=True)
    for b in books:
        fb2=os.path.join(a.repo,'public/books',b['filename'])
        endir=os.path.join(a.repo,'public/books',b['parallelEn'])
        slug=re.sub(r'[^A-Za-z0-9_-]','_',re.sub(r'\.[^.]+$','',os.path.basename(b['filename'])))
        chapters=fb2_chapters(fb2)
        print('%s: %d chapters'%(b['title'],len(chapters)))
        for ci,ch in enumerate(chapters):
            fkey='%s__ch%d.json'%(slug,ci)
            fpath=os.path.join(outdir,fkey)
            if os.path.exists(fpath) and not a.force:
                print('  ch%d: exists, skipping'%ci); continue
            nn=str(ci+1); nn='0'+nn if len(nn)<2 else nn
            try: enmap=json.load(open(os.path.join(endir,nn+'.json'),encoding='utf-8'))
            except Exception: enmap={}
            drills=[]
            for pi,par in enumerate(ch['paras']):
                sents=sentences(par)
                for si,s in enumerate(sents):
                    for d in drills_for_sentence(s, slug+str(ci)):
                        d['id']='c%d'%(len(drills)+1)
                        drills.append(d)
                if len(drills)>=a.max_per_chapter: break
            if len(drills)>=3:
                json.dump({'cases':drills},open(fpath,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
                print('  ch%d: %d drills → %s'%(ci,len(drills),fkey))
            else:
                print('  ch%d: only %d clean candidates, skipped'%(ci,len(drills)))
    if a.all:
        run_bible(a, idx)

def run_bible(a, idx):
    book=next(b for b in idx if b.get('isBible') or 'Библи' in (b.get('title') or ''))
    fb2=os.path.join(a.repo,'public/books',book['filename'])
    chs=book['audiobook']['chapters']
    chapters=bible_chapters(fb2)
    print('Bible: %d reading chapters, %d audio keys'%(len(chapters),len(chs)))
    outdir=os.path.join(a.repo,'public/books/exercises')
    os.makedirs(outdir,exist_ok=True)
    made=skipped=0
    for ci,ch in enumerate(chapters):
        if ci>=len(chs) or not chs[ci]: continue
        key=os.path.basename(str(chs[ci])).replace('.json','')     # e.g. 01-03
        fpath=os.path.join(outdir,key+'.json')
        if os.path.exists(fpath) and not a.force:
            skipped+=1; continue
        try:
            enmap=json.load(open(os.path.join(a.repo,'public/books/bible-en',key+'.json'),encoding='utf-8'))
        except Exception:
            enmap={}
        drills=[]
        for par in ch['paras']:
            vm=re.match(r'^\s*(\d{1,3})\s+(.*)$',par,re.S)
            vno, body = (vm.group(1), vm.group(2)) if vm else (None, par)
            for si,sent in enumerate(sentences(body)):
                for d in drills_for_sentence(sent, key):
                    d['id']='c%d'%(len(drills)+1)
                    drills.append(d)
            if len(drills)>=a.max_per_chapter: break
        if len(drills)>=3:
            json.dump({'cases':drills},open(fpath,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
            made+=1
            if made%50==0: print('  %d chapters written (latest %s, %d drills)'%(made,key,len(drills)),flush=True)
        else:
            skipped+=1
    print('done: %d chapter files written, %d skipped (existing or <3 drills)'%(made,skipped))

if __name__=='__main__':
    main()
