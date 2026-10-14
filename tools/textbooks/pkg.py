import os,shutil,re,json
R='/tmp/claude-0/tb'
shutil.rmtree(f"{R}/pkg", ignore_errors=True)
os.makedirs(f"{R}/pkg/public/books/novel"); os.makedirs(f"{R}/pkg/public/books/textbooks")
names={"povarnin-logika2":"povarnin-logika"}
slugs=["povarnin-kak-chitat","povarnin-iskusstvo-spora","povarnin-logika2","rebelsky-azbuka","vipper-drevnost","vipper-srednie-veka","vipper-novoe-vremya","bogoraz-bukvar","vakhterov-bukvar","mayakovsky-azbuka","shcherba-kak-izuchat"]
stats={}
for s in slugs:
    n=names.get(s,s)
    fb=open(f"{R}/out/{s}/{s}.fb2",encoding='utf-8').read().replace(f'textbooks/{s}/',f'textbooks/{n}/')
    open(f"{R}/pkg/public/books/novel/{n}.fb2",'w',encoding='utf-8').write(fb)
    a=f"{R}/out/{s}/assets"
    if os.path.isdir(a) and os.listdir(a):
        shutil.copytree(a,f"{R}/pkg/public/books/textbooks/{n}")
    body=fb[fb.index('<body>'):]
    words=len(re.findall(r"\S+",re.sub(r"<[^>]+>"," ",re.sub(r"<title>[\s\S]*?</title>"," ",body))))
    stats[n]={"words":words,"cover":os.path.exists(f"{a}/cover.webp")}
json.dump(stats,open(f"{R}/pkg/stats.json","w"),ensure_ascii=False,indent=1)
print(stats)
