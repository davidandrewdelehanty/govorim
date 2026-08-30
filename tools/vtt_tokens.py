import re, io
def load(path):
    raw = io.open(path, encoding='utf-8', errors='replace').read()
    cues = []
    for blk in raw.split('\n\n'):
        m = re.search(r'(\d\d):(\d\d):(\d\d)\.(\d+)\s+-->', blk)
        if not m: continue
        t = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) \
            + int(m.group(4)[:3].ljust(3, '0')) / 1000.0
        txt = re.sub(r'<[^>]*>', '', blk[blk.index('-->'):])
        txt = re.sub(r'^[^\n]*\n', '', txt)
        cues.append((t, ' '.join(txt.split())))
    # Rolling captions repeat the previous line, so each cue contributes only
    # its new tail. Stamping every new word with the CUE's start put a word
    # that arrives late in a five-second cue five seconds early — which is
    # exactly the "jumps a few seconds before the word" a reader feels. The
    # new words are instead spread evenly from this cue's start to the next
    # cue's, since that span is the time in which they were actually spoken.
    toks = []
    for ci, (t, txt) in enumerate(cues):
        ws = txt.split()
        if toks:
            prev = [w for _, w in toks[-40:]]
            best = 0
            for k in range(min(len(ws), len(prev)), 0, -1):
                if prev[-k:] == ws[:k]: best = k; break
            ws = ws[best:]
        if not ws: continue
        t_next = cues[ci + 1][0] if ci + 1 < len(cues) else t + 4.0
        span = max(0.5, t_next - t)
        for wi, w in enumerate(ws):
            toks.append((t + span * wi / len(ws), w))
    return toks
def norm(w):
    return re.sub(r'[^а-яё]', '', w.lower().replace('ё', 'е'))
