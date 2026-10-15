# Rebuild every book that has both halves, a few per call; progress in tools/translations/rerun.done
cd "$(dirname "$0")/../.."
touch tools/translations/rerun.done
todo=$(python3 -c "
import csv,os
done=set(open('tools/translations/rerun.done').read().split())
skip=set('$SKIP'.split())
for r in csv.reader(open('tools/translations/list.tsv',encoding='utf-8'),delimiter='\t'):
    if not r or r[0].startswith('#'): continue
    s=r[0]
    if s in done or s in skip: continue
    if os.path.exists('public/books/novel/%s.fb2'%s) and os.path.exists('tools/translations/en/%s.txt'%s): print(s)
" | head -${N:-6})
[ -z "$todo" ] && { echo ALLDONE; exit; }
timeout 165 python3 tools/translations_build.py --only $todo 2>&1 | grep -v "^$\|report →\|book(s)" && for s in $todo; do echo $s >> tools/translations/rerun.done; done
