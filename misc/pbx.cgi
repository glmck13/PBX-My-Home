#!/bin/ksh

PATH=$PATH:/var/www/.local/bin

for x in ${QUERY_STRING//\&/ }
do
	key=${x%%=*} val=${x#*=}
	val=$(urlencode -d "$val" | sed -e 's/\$/\\\\\\&/g')
	eval $key=\"$val\"
done

cd $DOCUMENT_ROOT/cdn

start=${exten#???} exten=${exten%$start}
POSITION=$PWD/${exten}.secs
if [ "$start" ]; then
	:
elif [ -f "$POSITION" ]; then
	start=$(<$POSITION)
else
	start=0
fi
let end=$start+3600
secs=$(date "+%s")
trap 'let start=${start}+$(date +"%s")-${secs}; [ "$media" != "short" ] && echo ${start} >$POSITION' HUP INT TERM EXIT

grep "^$exten|" pbx.conf | IFS='|' read x media src desc
[ ! "$media" ] && media="short" src="misc/nothing-en.mp3"

print "Content-Type: audio/mpeg\n"

if [ "$media" = "short" ]; then
	cat "$src"
elif [ "$media" = "long" ]; then
	ffmpeg -i "$src" -f mp3 -ss "${start}" - 2>/dev/null
elif [ "$media" = "youtube" ]; then
	yt-dlp -o - -x "$src" --download-sections "*${start}-${end}" 2>/dev/null | ffmpeg -i - -f mp3 -ar 48000 - 2>/dev/null
fi
