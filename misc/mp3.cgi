#!/bin/ksh

exten=${QUERY_STRING:-none}

cd $DOCUMENT_ROOT/cdn

ls -1 $exten:* 2>/dev/null | read media
[ ! "$media" ] && media="ZZZZ:nothing-to-play.mp3"

print "Content-Type: audio/mpeg\n"

#echo "$media"
cat "$media"
