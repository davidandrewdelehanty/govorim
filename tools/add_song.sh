#!/usr/bin/env bash
# add_song.sh — add a song to Govorim's Music tab
# Prompts for a lyrics .txt file, song title, artist, and YouTube link,
# merges it into public/music/music.json, and optionally commits + pushes.
set -e
REPO="/mnt/c/Users/david/projects/govorim-app"
cd "$REPO"

read -rp "Path to lyrics .txt file: " LYR
# accept Windows-style paths (C:\Users\... or C:/Users/...)
case "$LYR" in
  [A-Za-z]:\\*|[A-Za-z]:/*) LYR="$(wslpath "$LYR")" ;;
esac
LYR="${LYR/#\~/$HOME}"
if [ ! -f "$LYR" ]; then echo "File not found: $LYR"; exit 1; fi

read -rp "Song title: " TITLE
read -rp "Artist name: " ARTIST
read -rp "YouTube link (or bare video ID): " YT

python3 - "$LYR" "$TITLE" "$ARTIST" "$YT" <<'PYEOF'
import json, sys, re
lyr_path, title, artist, yt = sys.argv[1:5]

m = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})', yt) \
    or re.fullmatch(r'\s*([A-Za-z0-9_-]{11})\s*', yt)
if not m:
    sys.exit("ERROR: could not extract a YouTube video ID from: " + yt)
vid = m.group(1)

lyrics = open(lyr_path, encoding='utf-8-sig').read().replace('\r\n', '\n').strip()
if not lyrics:
    sys.exit("ERROR: the lyrics file is empty.")

p = 'public/music/music.json'
data = json.load(open(p, encoding='utf-8'))

for a in data:
    if a['artist'].strip().lower() == artist.strip().lower():
        entry = a
        break
else:
    entry = {'artist': artist.strip(), 'songs': []}
    data.append(entry)

for s in entry['songs']:
    if s['title'].strip().lower() == title.strip().lower():
        sys.exit("ERROR: «%s» already exists for %s — not overwriting." % (title, entry['artist']))

entry['songs'].append({'title': title.strip(), 'youtube': vid, 'lyrics': lyrics})
json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("Added «%s — %s» (video %s). %d artist(s) in music.json." %
      (entry['artist'], title.strip(), vid, len(data)))
PYEOF

echo
read -rp "Commit and push now? [y/N] " OK
if [[ "$OK" =~ ^[Yy] ]]; then
  git add public/music/music.json
  git commit -m "Music: add ${ARTIST} — ${TITLE}"
  git push
  echo "Pushed — the song will be live after Vercel redeploys."
else
  echo "Saved to public/music/music.json (not committed yet)."
fi
