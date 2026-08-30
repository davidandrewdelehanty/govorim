import re, io
def load(path):
    raw = io.open(path, encoding='utf-8', errors='replace').read()
    cues = []
    for blk in raw.split('\n\n'):
        m = re.search(r'(\d\d):(\d\d):(\d\d)\.(\d+)\s+-->', blk)
        if not m: continue
        t = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
        txt = re.sub(r'<[^>]*>', '', blk[blk.index('-->'):])
        txt = re.sub(r'^[^\n]*\n', '', txt)
        cues.append((t, ' '.join(txt.split())))
    toks = []
    for t, txt in cues:
        ws = txt.split()
        if toks:
            prev = [w for _, w in toks[-40:]]
            best = 0
            for k in range(min(len(ws), len(prev)), 0, -1):
                if prev[-k:] == ws[:k]: best = k; break
            ws = ws[best:]
        for w in ws: toks.append((t, w))
    return toks
def norm(w):
    return re.sub(r'[^а-яё]', '', w.lower().replace('ё', 'е'))
