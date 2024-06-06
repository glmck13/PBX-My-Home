#!/bin/bash

. sxmo_common.sh

SENDER="${1:?}"
TEXT="${2}"
ATTACHMENTS="${3}"

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
	attach=${attach//;/} attach=${attach#*sxmo/}
	NOTIFY+=$(cat - <<-EOF

        {
           "attributes": {
               "mime_type": "application/octet-stream",
               "url": "$SXMO_MYHTTP/$attach"
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

curl -k $SXMO_WEBHOOK -d@- <<<$NOTIFY
