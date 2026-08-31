#!/usr/bin/env python3
# Rebuild every paragraph map, whether or not one already exists.
#
# sync_new.py and sync_rest.py both skip a book that already has maps, which
# is right when the job is to fill gaps and wrong when the maps themselves
# need to change — as when they stopped carrying interpolated paragraphs.
import sys, json, io, os
sys.path.insert(0, 'tools')
import sync_all

DONE = 'tools/sync-rebuilt.json'

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    done = json.load(io.open(DONE, encoding='utf-8')) if os.path.exists(DONE) else {}
    d = json.load(io.open('private/books/index.json', encoding='utf-8'))
    todo = [b for b in d if b.get('videos') and b['filename'] not in done]
    print('%d books left to rebuild' % len(todo), flush=True)
    for b in todo[:n]:
        r = sync_all.run(b)
        done[b['filename']] = r
        io.open(DONE, 'w', encoding='utf-8').write(json.dumps(done, ensure_ascii=False, indent=1) + '\n')
        print('%-34s %s' % ((b.get('title') or '')[:34], r), flush=True)
    print('remaining: %d' % max(0, len(todo) - n))

if __name__ == '__main__':
    main()
