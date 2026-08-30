import sys, json, os, glob
sys.path.insert(0,'tools')
import sync_all
d=json.load(open('private/books/index.json',encoding='utf-8'))
todo=[]
for b in d:
    if not b.get('videos'): continue
    base=os.path.basename(b['filename']).rsplit('.',1)[0]
    if glob.glob('public/books/audio-sync/%s/*.json'%base): continue
    todo.append(b)
a=int(sys.argv[1]); z=int(sys.argv[2])
for b in todo[a:z]:
    r=sync_all.run(b)
    print('%-34s %s'%((b.get('title') or '')[:34], r), flush=True)
print('remaining after this batch:', max(0,len(todo)-z))
