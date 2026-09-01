#!/usr/bin/env python3
"""Print each FB2's section tree: nesting depth, titles, chapter counts."""
import io, json, os, re, sys
import xml.etree.ElementTree as ET
ROOT='.'
def local(e): return e.tag.split('}')[-1]
def load(fn):
    p=os.path.join('public/books',fn)
    if not os.path.exists(p): p=os.path.join('private/books',fn)
    raw=io.open(p,'rb').read()
    m=re.match(rb"<\?xml[^>]*encoding=[\"\']([\w-]+)",raw[:200])
    encs=([m.group(1).decode()] if m else [])+["utf-8","cp1251"]
    for enc in encs:
        try: src=raw.decode(enc); break
        except: continue
    src=re.sub(r"<binary[\s\S]*?</binary>","",src)
    src=re.sub(r"^\s*<\?xml[^>]*\?>","",src,count=1)
    return ET.fromstring(src.encode('utf-8'))
def title_of(sec):
    for c in sec:
        if local(c)=='title':
            return re.sub(r'\s+',' ',''.join(c.itertext())).strip()
    return ''
def tree(sec,depth,out):
    subs=[c for c in sec if local(c)=='section']
    t=title_of(sec)
    out.append((depth,t,len(subs)))
    if depth<2:
        for s in subs: tree(s,depth+1,out)
    elif subs:
        out.append((depth+1,'…%d subsections'%len(subs),0))
man=json.load(open('private/books/index.json',encoding='utf-8'))
seen=set()
for e in man:
    fn=e.get('filename')
    if not fn or e.get('isBible') or fn in seen: continue
    seen.add(fn)
    try: root=load(fn)
    except Exception as ex: print("##",e['title'],fn,"PARSE FAIL",ex); continue
    bodies=[b for b in root if local(b)=='body']
    main=next((b for b in bodies if not b.get('name')),None) or (bodies[0] if bodies else None)
    if main is None: continue
    secs=[c for c in main if local(c)=='section']
    out=[]
    for s in secs: tree(s,0,out)
    top_titled=[t for d,t,n in out if d==0 and t]
    nested=any(n>0 for d,t,n in out if d==0)
    print("## %s | top:%d nested:%s" % (e['title'], len(secs), "Y" if nested else "n"))
    shown=0
    for d,t,n in out:
        if d==0 or (d==1 and t and n>0) or (d==0 and n>0):
            print("   "+"  "*d+("[%d sub] "%n if n else "")+ (t[:60] or "(untitled)"))
            shown+=1
            if shown>14: print("   …"); break
