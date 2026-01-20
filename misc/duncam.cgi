#!/bin/ksh

MEDIA_URL=/cdn/duncam
MEDIA_DIR=$DOCUMENT_ROOT/$MEDIA_URL
PIC1=cam1.jpg WAV1=cam1.wav
PIC2=cam2.jpg WAV2=cam2.wav

cat - <<EOF
Cache-Control: no-cache, no-store, max-age=0
Pragma: no-cache
Content-Type: text/html

<html>
<link rel="apple-touch-icon" type="image/png" href="/images/puppy.png">
<meta http-equiv="cache-control" content="no-cache">
<meta http-equiv="pragma" content="no-cache">
<meta http-equiv="expires" content="-1">
EOF

rm -f $PIC1 $PIC2 $WAV1 $WAV2

curl -s 'http://duncam@duncam1.lan/image/jpeg.cgi' >$MEDIA_DIR/$PIC1
curl -s 'http://duncam@duncam2.lan/image/jpeg.cgi' >$MEDIA_DIR/$PIC2
timeout 5s curl -s 'http://duncam@duncam1.lan/audio.cgi' >$MEDIA_DIR/$WAV1 &
timeout 5s curl -s 'http://duncam@duncam2.lan/audio.cgi' >$MEDIA_DIR/$WAV2 &
wait

cat - <<EOF
<img src="$MEDIA_URL/$PIC1" width=800><br>
<audio controls style="width:800px;"><source src="$MEDIA_URL/$WAV1"></audio>
<img src="$MEDIA_URL/$PIC2" width=800><br>
<audio controls style="width:800px;"><source src="$MEDIA_URL/$WAV2"></audio>
</html>
EOF
