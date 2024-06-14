#!/bin/bash

. sxmo_common.sh

# extract mms payload
extractmmsattachement() {
	jq -r '.attrs.Attachments[] | join(" ")' | while read -r AINDEX ACTYPE AFILE AOFFSET ASIZE; do
		case "$ACTYPE" in
			*text/*)
				DATA_EXT="txt"
				;;
			*image/gif*)
				DATA_EXT="gif"
				;;
			*image/png*)
				DATA_EXT="png"
				;;
			*image/jpeg*)
				DATA_EXT="jpeg"
				;;
			*video/*)
				DATA_EXT="video"
				;;
			*)
				DATA_EXT="bin"
				;;
		esac

		sxmo_log "$AINDEX $ACTYPE $AFILE $AOFFSET $ASIZE"
		dd skip="$AOFFSET" count="$ASIZE" if="$AFILE" of="$SXMO_LOGDIR/$LOGDIRNUM/attachments/${AFILE##*/}-${AINDEX}.$DATA_EXT" bs=1 >/dev/null 2>&1
	done
}

# We process both sent and received mms here.
processmms() {
	MESSAGE_PATH="$1"
	MESSAGE="$(mmsctl -M -o "$MESSAGE_PATH")"
	MMS_FILE="${MESSAGE_PATH##*/}"

	sxmo_log "$MESSAGE"

	STATUS="$(printf %s "$MESSAGE" | jq -r '.attrs.Status')" # sent or received
	sxmo_log "Processing $STATUS mms ($MESSAGE_PATH)."
	[[ "$STATUS" == @(sent|received) ]] || return

	DATE="$(printf %s "$MESSAGE" | jq -r '.attrs.Date')"
	DATE="$(date +%FT%H:%M:%S%z -d "$DATE")"
	# everyone to whom the message was sent (including you). This will be a
	# string e.g. +12345678+123455+39898988
	RECIPIENTS="$(printf %s "$MESSAGE" | jq -r '.attrs.Recipients | join("")')"

	MYNUM="$(printf %s "$MESSAGE" | jq -r '.attrs."Modem Number"')"
	[ -z "$MYNUM" ] && MYNUM="+12345670000"

	SENDER="$(printf %s "$MESSAGE" | jq -r '.attrs.Sender')" # note this will be null if I am the sender
	[ "$SENDER" = "null" ] && SENDER="$MYNUM"

	# Generates a unique LOGDIRNUM: all the recipients, plus the sender, minus you
	LOGDIRNUM="$(printf %s%s "$RECIPIENTS" "$SENDER" | xargs pnc find | grep -v "^$MYNUM$" | sort -u | grep . | xargs printf %s)"

	mkdir -p "$SXMO_LOGDIR/$LOGDIRNUM/attachments"
	printf "%s" "$MESSAGE" | extractmmsattachement

	if [ -f "$SXMO_LOGDIR/$LOGDIRNUM/attachments/$MMS_FILE.txt" ]; then
		TEXT="$(cat "$SXMO_LOGDIR/$LOGDIRNUM/attachments/$MMS_FILE.txt")"
		rm -f "$SXMO_LOGDIR/$LOGDIRNUM/attachments/$MMS_FILE.txt"
	else
		TEXT=""
	fi

	sxmo_log "Finished processing $MMS_FILE. Deleting it."
	mmsctl -D -o "$MESSAGE_PATH"

	printf "%s\t%s_mms\t%s\t%s\n" "$DATE" "$STATUS" "$LOGDIRNUM" "$MMS_FILE" >> "$SXMO_LOGDIR/modemlog.tsv"

	if [ "$STATUS" = "received" ]; then
		ATTACHMENTS=""
		for attachment in $SXMO_LOGDIR/$LOGDIRNUM/attachments/${MMS_FILE}[.-]*; do
			[ -f "$attachment" ] && ATTACHMENTS+="$attachment; "
		done
		sxmo_log "ATTACHMENTS: $ATTACHMENTS"
		sxmo_notify.sh "$SENDER" "$LOGDIRNUM" "$TEXT" "$ATTACHMENTS"
	fi

}

"$@"
