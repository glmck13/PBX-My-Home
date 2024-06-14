#!/bin/bash

. sxmo_common.sh

NUMBER=${1:?}
TXTFILE=${2:?}
TXTSIZE=$(stat -c%s "$TXTFILE")

sxmo_log "Send SMS to $NUMBER: $TXTFILE [$TXTSIZE]"

SMSNO=$(mmcli -m any --messaging-create-sms-with-text="$TXTFILE" --messaging-create-sms="number=$NUMBER")
SMSNO=${SMSNO##*/}
mmcli -m any -s "$SMSNO" --send --timeout=10
mmcli -m any --messaging-delete-sms="$SMSNO"

TIME="$(date +%FT%H:%M:%S%z)"
mkdir -p "$SXMO_LOGDIR/$NUMBER"
printf "%s\tsent_txt\t%s\t%s chars\n" "$TIME" "$NUMBER" "$TXTSIZE" >> "$SXMO_LOGDIR/modemlog.tsv"
