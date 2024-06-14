#!/bin/bash

. sxmo_common.sh

cleanupnumber() {
	if pnc valid "$1"; then
		echo "$1"
		return
	fi

	REFORMATTED="$(pnc find ${DEFAULT_COUNTRY:+-c "$DEFAULT_COUNTRY"} "$1")"
	if [ -n "$REFORMATTED" ]; then
		echo "$REFORMATTED"
		return
	fi

	echo "$1"
}

checkfornewtexts() {
	exec 3<> "${XDG_RUNTIME_DIR:-$HOME}/sxmo_modem.checkfornewtexts.lock"
	flock -x 3
	TEXTIDS="$(
		mmcli -m any --messaging-list-sms |
		grep -Eo '/SMS/[0-9]+ \(received\)' |
		grep -Eo '[0-9]+'
	)"
	[ "$TEXTIDS" ] || return

	# Loop each textid received and read out the data into appropriate logfile
	for TEXTID in $TEXTIDS; do
		TEXTDATA="$(mmcli -m any -s "$TEXTID" -J)"
		# SMS with no TEXTID is an SMS WAP (I think). So skip.
		if [ -z "$TEXTDATA" ]; then
			sxmo_log "Received an empty SMS (TEXTID: $TEXTID).  I will assume this is an MMS."
			printf %b "$(date +%FT%H:%M:%S%z)\tdebug_mms\tNULL\tEMPTY (TEXTID: $TEXTID)\n" >> "$SXMO_LOGDIR/modemlog.tsv"
			continue
		fi
		TEXT="$(printf %s "$TEXTDATA" | jq -r .sms.content.text)"
		NUM="$(printf %s "$TEXTDATA" | jq -r .sms.content.number)"
		NUM="$(cleanupnumber "$NUM")"

		TIME="$(printf %s "$TEXTDATA" | jq -r .sms.properties.timestamp)"
		TIME="$(date +%FT%H:%M:%S%z -d "$TIME")"

		if [ "$TEXT" = "--" ]; then
			sxmo_log "Text from $NUM (TEXTID: $TEXTID) with '--'.  I will assume this is an MMS."
			printf %b "$TIME\tdebug_mms\t$NUM\t$TEXT\n" >> "$SXMO_LOGDIR/modemlog.tsv"
			#continue
		fi

		mkdir -p "$SXMO_LOGDIR/$NUM"
		sxmo_log "Text from number: $NUM (TEXTID: $TEXTID)"
		printf %b "$TIME\trecv_txt\t$NUM\t${#TEXT} chars\n" >> "$SXMO_LOGDIR/modemlog.tsv"

		mmcli -m any --messaging-delete-sms="$TEXTID"
		sxmo_notify.sh "$NUM" "+1${SXMO_MYNUM}" "$TEXT" ""
	done
}

"$@"
