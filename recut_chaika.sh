#!/usr/bin/env bash
# Re-cut the 6 Чайка recordings into 4 act-aligned MP3s and upload them to R2.
# Requires: ffmpeg + aws CLI (same config you used for the mfa_staging download).
# The trim points below are exact and match the word_timings in the act JSONs,
# so DO NOT change them.
set -euo pipefail

BUCKET="s3://govorim-audio"
SRC="chaika6"        # where the 6 source recordings live on R2
DST="chaika-acts"    # where the 4 act files will be uploaded
# R2 endpoint (a 403 means aws was hitting real AWS instead of R2). If your
# credentials use a named profile, add e.g.  export AWS_PROFILE=r2  below too.
export AWS_ENDPOINT_URL="https://34e5181838c8f719758264dbb7b02b46.r2.cloudflarestorage.com"

command -v ffmpeg >/dev/null || { echo "ffmpeg not found — install it first (e.g. sudo apt install ffmpeg)"; exit 1; }
command -v aws    >/dev/null || { echo "aws CLI not found"; exit 1; }

WORK="$(mktemp -d)"; echo "workdir: $WORK"; cd "$WORK"

echo "== downloading the 6 source recordings =="
for n in 01 02 03 04 05 06; do
  aws s3 cp "$BUCKET/$SRC/chaika-ch$n.mp3" "ch$n.mp3"
done

# normalize + trim + concat in a single re-encode; the first segment's trimmed
# length is the exact offset baked into the act JSON word_timings.
FMT="aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS"
ENC="-c:a libmp3lame -q:a 3"

echo "== Act 1 = ch01[0:1350.74] + ch02[0:716.14] =="
ffmpeg -y -i ch01.mp3 -i ch02.mp3 -filter_complex \
 "[0:a]atrim=0:1350.74,$FMT[a];[1:a]atrim=0:716.14,$FMT[b];[a][b]concat=n=2:v=0:a=1[o]" \
 -map "[o]" $ENC chaika-act1.mp3

echo "== Act 2 = ch02[716.14:1303.945] + ch03 =="
ffmpeg -y -i ch02.mp3 -i ch03.mp3 -filter_complex \
 "[0:a]atrim=716.14:1303.945,$FMT[a];[1:a]$FMT[b];[a][b]concat=n=2:v=0:a=1[o]" \
 -map "[o]" $ENC chaika-act2.mp3

echo "== Act 3 = ch04[0:1294.343] + ch05[0:257.35] =="
ffmpeg -y -i ch04.mp3 -i ch05.mp3 -filter_complex \
 "[0:a]atrim=0:1294.343,$FMT[a];[1:a]atrim=0:257.35,$FMT[b];[a][b]concat=n=2:v=0:a=1[o]" \
 -map "[o]" $ENC chaika-act3.mp3

echo "== Act 4 = ch05[257.35:1251.16] + ch06 =="
ffmpeg -y -i ch05.mp3 -i ch06.mp3 -filter_complex \
 "[0:a]atrim=257.35:1251.16,$FMT[a];[1:a]$FMT[b];[a][b]concat=n=2:v=0:a=1[o]" \
 -map "[o]" $ENC chaika-act4.mp3

echo "== uploading the 4 act files to $BUCKET/$DST/ =="
for n in 1 2 3 4; do
  aws s3 cp "chaika-act$n.mp3" "$BUCKET/$DST/chaika-act$n.mp3" --content-type audio/mpeg
done

echo ""
echo "DONE. Uploaded chaika-act1.mp3 .. chaika-act4.mp3 to $BUCKET/$DST/"
echo "workdir left at $WORK (delete when happy)."
