#!/bin/bash

source ~asterisk/venv/bin/activate
TMPDIR=$DOCUMENT_ROOT/tmp/youtube-$$
mkdir -p $TMPDIR
cd $TMPDIR

echo -e "Content-Type: text/plain\n"

q=$(urlencode -d "${QUERY_STRING}")
#yt-dlp --extract-audio "$(urlencode -d "${q#*=}")" 2>&1
yt-dlp "$(urlencode -d "${q#*=}")" 2>&1

#f=$(ls -1 *.opus 2>/dev/null)
f=$(ls -1 *.webm 2>/dev/null)
if [ "$f" ]; then
	ffmpeg -i "$f" "$DOCUMENT_ROOT/cdn/000:YouTube:new.mp3" 2>&1
fi

f=$(ls -1 *.m4a 2>/dev/null)
if [ "$f" ]; then
	ffmpeg -i "$f" -vn -acodec copy out.aac
	ffmpeg -i out.aac "$DOCUMENT_ROOT/cdn/000:YouTube:new.mp3" 2>&1
fi

cd $DOCUMENT_ROOT
rm -fr $TMPDIR
