#!/usr/bin/env bash
# Lists the «Библия Онлайн» book playlists and downloads the Russian captions
# for every chapter video the Synodal entry does not have yet. Needs YouTube,
# so run it in WSL:   bash tools/bible_fetch.sh
# Safe to stop and re-run: anything already on disk is skipped.
cd "$(dirname "$0")/.."
mkdir -p tools/bible-pl tools/vtt
python3 -c "
import json
d=json.load(open('tools/bible-channel.json',encoding='utf-8'))
for e in d.get('entries',[]):
    if 'Ветхий Завет' in (e.get('title') or ''): continue
    print(e['id'])
" | while read -r pl; do
  [ -s "tools/bible-pl/$pl.json" ] && continue
  echo "playlist $pl"
  yt-dlp --flat-playlist -J "https://www.youtube.com/playlist?list=$pl" > "tools/bible-pl/$pl.json" || rm -f "tools/bible-pl/$pl.json"
  sleep 1
done
python3 tools/bible_videos.py --ids > /tmp/bible_ids.txt
echo "$(wc -l < /tmp/bible_ids.txt) chapter videos to caption"
n=0
while read -r id; do
  [ -s "tools/vtt/$id.ru.vtt" ] && continue
  n=$((n+1)); echo "[$n] $id"
  # Auto captions first; a video can instead carry uploaded captions, or
  # label its Russian track "ru-orig" — any of those will do.
  yt-dlp --write-sub --write-auto-sub --sub-langs "ru,ru-orig,ru.*" --sub-format vtt --skip-download \
         -o "tools/vtt/%(id)s" "https://youtu.be/$id" >/dev/null 2>&1 || echo "  failed: $id"
  if [ ! -s "tools/vtt/$id.ru.vtt" ]; then
    alt=$(ls "tools/vtt/$id".ru*.vtt 2>/dev/null | head -1)
    if [ -n "$alt" ]; then mv "$alt" "tools/vtt/$id.ru.vtt"; else echo "  no Russian captions: $id"; fi
  fi
  sleep 2
done < /tmp/bible_ids.txt
python3 tools/bible_videos.py
echo "Now run:  python3 tools/bible_videos.py --write"
