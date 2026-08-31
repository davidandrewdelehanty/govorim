#!/usr/bin/env python3
# Build the paragraph maps for every book that still lacks them.
#
# sync_new.py picks its work by asking which books have no map directory yet,
# which means a book that FAILS its gates is asked again on every run and sits
# at the head of the queue forever. Slicing that queue by index — 0:8, then
# 8:16 — quietly skips whatever moved down as the successes dropped out, and
# thirteen books went unmapped that way without anything reporting a problem.
#
# So this keeps a record of what has been attempted, not only of what
# succeeded, and always works from the head of what remains.
import sys, json, os, io, glob
sys.path.insert(0, 'tools')
import sync_all

TRIED = 'tools/sync-tried.json'

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    tried = {}
    if os.path.exists(TRIED):
        tried = json.load(io.open(TRIED, encoding='utf-8'))
    d = json.load(io.open('private/books/index.json', encoding='utf-8'))
    todo = []
    for b in d:
        if not b.get('videos'): continue
        base = os.path.basename(b['filename']).rsplit('.', 1)[0]
        if glob.glob('public/books/audio-sync/%s/*.json' % base): continue
        if b['filename'] in tried: continue
        todo.append(b)
    print('%d books still unmapped and untried' % len(todo), flush=True)
    for b in todo[:n]:
        r = sync_all.run(b)
        tried[b['filename']] = r
        io.open(TRIED, 'w', encoding='utf-8').write(
            json.dumps(tried, ensure_ascii=False, indent=1) + '\n')
        print('%-34s %s' % ((b.get('title') or '')[:34], r), flush=True)
    print('remaining: %d' % max(0, len(todo) - n))

if __name__ == '__main__':
    main()
