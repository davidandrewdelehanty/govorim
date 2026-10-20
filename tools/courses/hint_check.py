import json,glob,re,collections,pymorphy3,sys
m=pymorphy3.MorphAnalyzer(); Y=lambda s:s.lower().replace("ё","е")
C={}
def lem(w):
    w=Y(w)
    if w not in C: C[w]={Y(p.normal_form) for p in m.parse(w)}|{w}
    return C[w]
W=lambda s:re.findall(r"[а-яё]+(?:-[а-яё]+)?", Y(s))
NUML={"один","оба","обе","тысяча","миллион","миллиард","полтора","первый","второй","третий","четвертый","пятый","шестой","седьмой","восьмой","девятый","десятый","одиннадцатый","двенадцатый","тринадцатый","четырнадцатый","пятнадцатый","шестнадцатый","семнадцатый","восемнадцатый","девятнадцатый","двадцатый","тридцатый","сороковой","пятидесятый","шестидесятый","семидесятый","восьмидесятый","девяностый","сотый"}
def numeral(w):
    return any(p.tag.POS=="NUMR" or Y(p.normal_form) in NUML for p in m.parse(Y(w)))
def good(e):
    h=re.findall(r"___ \(([^)]*)\)", e["q"])
    if not h: return None
    a=W(e["answers"][0])
    # a figure for a hint — «___ (2) часов», «___ (3-й) день» — when the answer is the numeral itself
    if re.fullmatch(r"\d+(-[а-яё]{1,3})?", h[0].strip()): return bool(a) and all(numeral(x) for x in a)
    for opt in re.split(r"\s*/\s*|,\s*", h[0]):
        o=W(opt)
        if len(o)==len(a) and all(lem(x)&lem(y) for x,y in zip(o,a)): return True
        if len(o)==1 and len(a)>1 and any(lem(o[0])&lem(y) for y in a): return True  # compound forms: буду писать, самый …
    return False
if False:
    ok=bad=0; s=[]
    for f in glob.glob("public/courses/*/*.json"):
        for e in json.load(open(f))["exercises"]:
            g=good(e)
            if g is True: ok+=1
            elif g is False: bad+=1; s.append(f.split("/")[2]+": "+re.findall(r"___ \(([^)]*)\)", e["q"])[0]+" → "+e["answers"][0])
    print(ok,bad); import random; random.seed(1); print(random.sample(s,30))
