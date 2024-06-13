#!/bin/bash

. sxmo_common.sh

SENDER="${1:?}"
TEXT="${2}"
ATTACHMENTS="${3}"

[ "$TEXT" -o "$ATTACHMENTS" ] || exit

if [ "$ATTACHMENTS" ]; then
	IS_MMS=true
else
	IS_MMS=false
fi

NOTIFY=$(cat - <<-EOF
{
   "data": {
       "attributes": {
           "body": "$TEXT",
           "from": "$SENDER",
           "is_mms": $IS_MMS
       },
       "type": "message"
   },
   "included": [
EOF
)

for attach in $ATTACHMENTS
do
	attach=${attach//;/}
	mime=$(mimetype -bM $attach)
	attach=$SXMO_MYHTTP/${attach#*sxmo/}
	NOTIFY+=$(cat - <<-EOF

        {
           "attributes": {
               "mime_type": "$mime",
               "url": "$attach"
           }
        },
	EOF
	)
done

NOTIFY=${NOTIFY%,}
NOTIFY+=$(cat - <<-EOF

   ]
}
EOF
)

#cat <<<$NOTIFY >&2

curl -sk $SXMO_WEBHOOK -d@- <<<$NOTIFY
