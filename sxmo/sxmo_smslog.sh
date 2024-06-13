#!/bin/bash

. sxmo_common.sh

ACTION="$1" # recv or sent
LOGDIRNUM="$2" # The directory name in SXMO_LOG
NUM="$3" # The sender's phone number
TIME="$4"
TEXT="$5"
MMSID="$6" # optional

if [ "$ACTION" = "recv" ]; then
	VERB="Received"
else
	VERB="Sent"
fi

# if group chain also print the sender
if [ "$NUM" != "$LOGDIRNUM" ] && [ "$ACTION" = "recv" ]; then
	printf "%s from %s at %s:\n%b\n" \
		"$VERB" "$NUM" "$TIME" "$TEXT"
else
	printf "%s at %s:\n%b\n" \
		"$VERB" "$TIME" "$TEXT"
fi

# print any attachments
for attachment in $SXMO_LOGDIR/$LOGDIRNUM/attachments/${MMSID}[.-]*; do
	[ -f "$attachment" ] && printf "%s\n" "$(basename "$attachment")"
done

printf "\n"
