#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_published.py — set a book's timings from its videos' own chapter lists.

For every video the book uses that has a saved description with a timestamp
list, the chapters on that video are assigned to the list's entries by optimal
monotone alignment of the text spoken at each mark (dynamic programming, the
sequence-alignment recurrence — greedy assignment fails: one wrong early pick
drags every later chapter forward). Each assigned chapter is then set to the
creator's time and marked manual.

    python3 tools/apply_published.py --slug anna-karenina          # dry run
    python3 tools/apply_published.py --slug anna-karenina --write
"""
import argparse, bisect, importlib.util, io, json, os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
sp=importlib.util.spec_from_file_location("st",os.path.join(HERE,"scan_timestamps.py")); st=importlib.util.module_from_spec(sp); sp.loader.exec_module(st)
av=st.av_mod()

def dp_assign(S):
    n,m=len(S),len(S[0]); NEG=-1e9
    best=[[NEG]*m for _ in range(n)]; back=[[-1]*m for _ in range(n)]
    for j in range(m): best[0][j]=S[0][j]
    for i in range(1,n):
        run=NEG; arg=-1
        for j in range(m):
            if j>0 and best[i-1][j-1]>run: run,arg=best[i-1][j-1],j-1
            if run>NEG: best[i][j]=run+S[i][j]; back[i][j]=arg
    j=max(range(m),key=lambda j:best[n-1][j]); out=[0]*n
    for i in range(n-1,-1,-1): out[i]=j; j=back[i][j]
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--slug",required=True); ap.add_argument("--write",action="store_true")
    ap.add_argument("--min-mean",type=float,default=0.60,help="refuse a video whose mean match is below this")
    ap.add_argument("--video",help="only this video id")
    a=ap.parse_args()
    P=os.path.join(ROOT,"private","books","index.json"); man=json.load(io.open(P,encoding="utf-8"))
    e=next(x for x in man if x.get("slug")==a.slug); v=e["videos"]
    ch=av.fb2_chapters_body(os.path.join(ROOT,"public","books",e["filename"]),16)
    byvid={}
    for k in sorted(v,key=int):
        seg=v[k]
        if isinstance(seg,dict) and seg.get("youtube") and seg.get("start") is not None: byvid.setdefault(seg["youtube"],[]).append(int(k))
    changed=0
    for vid,chs in byvid.items():
        if len(chs)<2: continue
        if a.video and vid!=a.video: continue
        dpath=os.path.join(HERE,"captions",vid+".description"); cpath=os.path.join(HERE,"captions",vid+".ru.vtt")
        if not (os.path.exists(dpath) and os.path.exists(cpath)): print("  %s: no description/captions — skipped"%vid); continue
        pub=st.marks(io.open(dpath,encoding="utf-8").read())
        if len(pub)<len(chs): print("  %s: list has %d entries for %d chapters — skipped"%(vid,len(pub),len(chs))); continue
        w=av.parse_vtt(cpath); times=[x["b"] for x in w]
        # Band: chapter i can only land within `band` entries of where it would
        # sit if the two lists ran in step. Scoring every pair is 60x the work
        # for nothing — a chapter never maps forty entries away.
        # ...unless the counts differ by more than a few, in which case the map
        # covers only part of the list and nothing says which part. Anna
        # Karenina's third video carries 58 chapters of which the map uses the
        # last 37; an even spread put every band in the wrong place and
        # proposed a 3.7-hour move. Then score everything.
        band=8 if abs(len(pub)-len(chs))<=3 else len(pub); S=[]
        for k2,ci in enumerate(chs):
            pr=ch[ci]["probe"] if ci<len(ch) else []
            centre=round(k2*(len(pub)-1)/max(1,len(chs)-1))
            row=[]
            for j,(t,l) in enumerate(pub):
                if abs(j-centre)>band or len(pr)<6: row.append(0.0); continue
                lo=bisect.bisect_left(times,t-20); hi=bisect.bisect_right(times,t+75)
                row.append(av.cbt.best_match(w,pr,lo,max(lo,hi))[1])
            S.append(row)
        assign=dp_assign(S)
        mean=sum(S[i][j] for i,j in enumerate(assign))/len(assign)
        strong=sum(1 for i,j in enumerate(assign) if S[i][j]>=0.62)
        print("== %s: %d chapters vs %d published entries — mean %.2f, %d strong"%(vid,len(chs),len(pub),mean,strong))
        if mean<a.min_mean: print("   REFUSED: alignment too weak to trust"); continue
        for i,(ci,j) in enumerate(zip(chs,assign)):
            t,l=pub[j]; seg=v[str(ci)]; old=seg.get("start")
            if seg.get("manual") and old!=t: print("   ch%-4d KEEP %s (manual)"%(ci,av.clock(old))); continue
            mv="" if abs((old or 0)-t)<=10 else "  <-- %s -> %s (%+ds)"%(av.clock(old or 0),av.clock(t),t-(old or 0))
            if mv or a.write: print("   ch%-4d %-9s %-24s %.2f%s"%(ci,av.clock(t),l.strip("*")[:24],S[i][j],mv))
            if old!=t: changed+=1
            seg["start"]=t; seg["manual"]=True
            nxt=v.get(str(ci+1))
            if i+1<len(chs): seg["end"]=pub[assign[i+1]][0]
            elif "end" in seg: del seg["end"]
    print("\n%d start(s) would change"%changed)
    if a.write:
        e["timingSource"]=(e.get("timingSource") or "")+" | chapters on videos with a published list set from the creator's own timestamps (apply_published.py)"
        json.dump(man,io.open(P,"w",encoding="utf-8"),ensure_ascii=False,indent=2); print("written")
    return 0
if __name__=="__main__": sys.exit(main())
