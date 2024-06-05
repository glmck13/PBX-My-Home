#!/bin/bash

. sxmo_common.sh

stderr() {
	sxmo_log "$*"
}

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

checkforstucksms() {
	stuck_messages="$(mmcli -m any --messaging-list-sms)"
	if ! echo "$stuck_messages" | grep -q "^No sms messages were found"; then
		case "$1" in
			"delete")
				mmcli -m any --messaging-list-sms | while read -r line; do
					sms_number="$(echo "$line" | cut -d'/' -f6 | cut -d' ' -f1)"
					sxmo_log "Deleting sms $sms_number"
					mmcli -m any --messaging-delete-sms="$sms_number"
				done
				;;
			"view")
				mmcli -m any --messaging-list-sms | while read -r line; do
					sms_number="$(echo "$line" | cut -d'/' -f6 | cut -d' ' -f1)"
					mmcli -m any -s "$sms_number" -K
				done
				;;
		esac
	fi
}

checkfornewtexts() {
	exec 3<> "${XDG_RUNTIME_DIR:-HOME}/sxmo_modem.checkfornewtexts.lock"
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
			stderr "Received an empty SMS (TEXTID: $TEXTID).  I will assume this is an MMS."
			printf %b "$(date +%FT%H:%M:%S%z)\tdebug_mms\tNULL\tEMPTY (TEXTID: $TEXTID)\n" >> "$SXMO_LOGDIR/modemlog.tsv"
			continue
		fi
		TEXT="$(printf %s "$TEXTDATA" | jq -r .sms.content.text)"
		NUM="$(printf %s "$TEXTDATA" | jq -r .sms.content.number)"
		NUM="$(cleanupnumber "$NUM")"

		TIME="$(printf %s "$TEXTDATA" | jq -r .sms.properties.timestamp)"
		TIME="$(date +%FT%H:%M:%S%z -d "$TIME")"

		if [ "$TEXT" = "--" ]; then
			stderr "Text from $NUM (TEXTID: $TEXTID) with '--'.  I will assume this is an MMS."
			printf %b "$TIME\tdebug_mms\t$NUM\t$TEXT\n" >> "$SXMO_LOGDIR/modemlog.tsv"
			continue
		fi

		mkdir -p "$SXMO_LOGDIR/$NUM"
		stderr "Text from number: $NUM (TEXTID: $TEXTID)"
		sxmo_smslog.sh "recv" "$NUM" "$NUM" "$TIME" "$TEXT" >> "$SXMO_LOGDIR/$NUM/sms.txt"
		printf %b "$TIME\trecv_txt\t$NUM\t${#TEXT} chars\n" >> "$SXMO_LOGDIR/modemlog.tsv"

		tries=1
		while ! mmcli -m any --messaging-delete-sms="$TEXTID";
		do
			[ $tries -gt 3 ] && break
			tries=$((tries+1))
			echo "Failed to delete text $TEXTID. Will retry"
			sleep 3
		done

		sxmo_notify.sh "$NUM" "$TEXT" ""
	done
}

"$@"
