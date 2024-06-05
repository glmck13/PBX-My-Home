#!/bin/bash

. sxmo_common.sh

info() {
	sxmo_log "$*"
	printf "%s\n" "$*" # some functions run from commandline
}

# We attempt to delete all objects from mmsd-tng after we receive/send them.
# However, sometimes (e.g., a crash) there are stuck or "lost" mms, i.e.,
# mmsd-tng still has objects in its database.  Often mmsd-tng will resolve this
# issue itself, given enough time. If you pass --force to this function, it will
# process/delete them.
checkforlostmms() {
	# generate a list of all messages on the server
	if ! RES="$(dbus-send --dest=org.ofono.mms --print-reply /org/ofono/mms/modemmanager org.ofono.mms.Service.GetMessages)"; then
		info "mmsdtng is busy or something is broken."
		return 1
	fi

	ALL_MMS_TEMP="$(mktemp)"
	printf "%s\n" "$RES" | grep "object path" | cut -d'"' -f2 | rev | cut -d'/' -f1 | rev | sort -u > "$ALL_MMS_TEMP"

	count="$(wc -l < "$ALL_MMS_TEMP")"

	# loop through messages and report (or process if --force) them we
	# delete messages with status draft, and process those with sent and
	# received
	if [ "$count" -gt 0 ]; then
		info "Found the following $count unprocessed mms:"
		while read -r line; do
			MESSAGE_STATUS="$(mmsctl -M -o "/org/ofono/mms/modemmanager/$line" | jq -r '.attrs.Status')"
			case "$MESSAGE_STATUS" in
				sent|received)
					info "* $line (status:$MESSAGE_STATUS)."
					if [ "$1" = "--force" ]; then
						info "Processing."
						processmms "/org/ofono/mms/modemmanager/$line"
					fi
					;;
				draft|expired)
					info "* $line (status:$MESSAGE_STATUS)."
					if [ "$1" = "--force" ]; then
						info "Deleting."
						#dbus-send --dest=org.ofono.mms --print-reply "/org/ofono/mms/modemmanager/$line" org.ofono.mms.Message.Delete
						mmsctl -D -o "/org/ofono/mms/modemmanager/$line"
					fi
					;;
				*)
					info "* $line (status:$MESSAGE_STATUS). WARNING: UNKNOWN STATUS!"
					;;
			esac
		done < "$ALL_MMS_TEMP"
		if [ "$1" = "--force" ]; then
			info "Finished."
		else
			info "Run $0 checkforlostmms --force to process (if sent or received) or delete (if expired or draft)."
		fi
	fi
	rm "$ALL_MMS_TEMP"
}

# extract mms payload
extractmmsattachement() {
	jq -r '.attrs.Attachments[] | join(",")' | while read -r aline; do
		ACTYPE="$(printf %s "$aline" | cut -d',' -f2 | cut -d';' -f1 | sed 's|^Content-Type: "\(.*\)"$|\1|')"
		AOFFSET="$(printf %s "$aline" | cut -d',' -f4)"
		ASIZE="$(printf %s "$aline" | cut -d',' -f5)"
		case "$ACTYPE" in
			text/plain)
				DATA_EXT="txt"
				;;
			image/gif)
				DATA_EXT="gif"
				;;
			image/png)
				DATA_EXT="png"
				;;
			image/jpeg)
				DATA_EXT="jpeg"
				;;
			video/*)
				DATA_EXT="video"
				;;
			*)
				DATA_EXT="bin"
				;;
		esac

		MMS_BASE_DIR="${SXMO_MMS_BASE_DIR:-"$HOME"/.mms/modemmanager}"
		if [ -f "$MMS_BASE_DIR/$MMS_FILE" ]; then
			OUTFILE="$MMS_FILE.$DATA_EXT"
			count=0
			while [ -f "$SXMO_LOGDIR/$LOGDIRNUM/attachments/$OUTFILE" ]; do
				OUTFILE="$MMS_FILE-$count.$DATA_EXT"
				count="$((count+1))"
			done
			dd skip="$AOFFSET" count="$ASIZE" \
				if="$MMS_BASE_DIR/$MMS_FILE" \
				of="$SXMO_LOGDIR/$LOGDIRNUM/attachments/$OUTFILE" \
				bs=1 >/dev/null 2>&1
		fi

	done
}

# We process both sent and received mms here.
processmms() {
	MESSAGE_PATH="$1"

	MESSAGE="$(mmsctl -M -o "$MESSAGE_PATH")"
	MMS_FILE="$(printf %s "$MESSAGE_PATH" | rev | cut -d'/' -f1 | rev)"

	STATUS="$(printf %s "$MESSAGE" | jq -r '.attrs.Status')" # sent or received
	if [ "$STATUS" = "received" ]; then
		STATUS="recv"
	elif [ "$STATUS" = "sent" ]; then
		STATUS="sent"
	else
		sxmo_log "Warning: unknown status: $STATUS on $MESSAGE_PATH."
		return
	fi
	sxmo_log "Processing $STATUS mms ($MESSAGE_PATH)."

	DATE="$(printf %s "$MESSAGE" | jq -r '.attrs.Date')"
	DATE="$(date +%FT%H:%M:%S%z -d "$DATE")"
	# everyone to whom the message was sent (including you). This will be a
	# string e.g. +12345678+123455+39898988
	RECIPIENTS="$(printf %s "$MESSAGE" | jq -r '.attrs.Recipients | join("")')"

	MYNUM="$(printf %s "$MESSAGE" | jq -r '.attrs."Modem Number"')"
	[ -z "$MYNUM" ] && MYNUM="+12345670000"

	SENDER="$(printf %s "$MESSAGE" | jq -r '.attrs.Sender')" # note this will be null if I am the sender
	sxmo_debug "SENDER: $SENDER MYNUM: $MYNUM RECIPIENTS: $RECIPIENTS"
	sxmo_debug "MESSAGE: $MESSAGE"
	[ "$SENDER" = "null" ] && SENDER="$MYNUM"

	# Generates a unique LOGDIRNUM: all the recipients, plus the sender, minus you
	LOGDIRNUM="$(printf %s%s "$RECIPIENTS" "$SENDER" | xargs pnc find | grep -v "^$MYNUM$" | sort -u | grep . | xargs printf %s)"

	mkdir -p "$SXMO_LOGDIR/$LOGDIRNUM/attachments"
	printf "%s" "$MESSAGE" | extractmmsattachement

	if [ -f "$SXMO_LOGDIR/$LOGDIRNUM/attachments/$MMS_FILE.txt" ]; then
		TEXT="$(cat "$SXMO_LOGDIR/$LOGDIRNUM/attachments/$MMS_FILE.txt")"
		rm -f "$SXMO_LOGDIR/$LOGDIRNUM/attachments/$MMS_FILE.txt"
	else
		TEXT="<Empty>"
	fi

	#dbus-send --dest=org.ofono.mms --print-reply "$MESSAGE_PATH" org.ofono.mms.Message.Delete
	mmsctl -D -o "$MESSAGE_PATH"
	sxmo_log "Finished processing $MMS_FILE. Deleting it."

	printf "%s\t%s_mms\t%s\t%s\n" "$DATE" "$STATUS" "$LOGDIRNUM" "$MMS_FILE" >> "$SXMO_LOGDIR/modemlog.tsv"
	sxmo_smslog.sh "$STATUS" "$LOGDIRNUM" "$SENDER" "$DATE" "$TEXT" "$MMS_FILE" >> "$SXMO_LOGDIR/$LOGDIRNUM/sms.txt"

	if [ "$STATUS" = "recv" ]; then
		ATTACHMENTS=""
		for attachment in "$SXMO_LOGDIR/$LOGDIRNUM/attachments/${MMS_FILE}"[.-]*; do
			[ -f "$attachment" ] && ATTACHMENTS+="$attachment; "
		done
		sxmo_log "ATTACHMENTS: $ATTACHMENTS"
		sxmo_notify.sh "$SENDER" "$TEXT" "$ATTACHMENTS"
	fi

}

"$@"
