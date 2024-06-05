#!/bin/bash

cd $HOME/opt/sxmo
PATH=$PWD:$PATH

rm -fr $HOME/.sxmo; mkdir -p $HOME/.sxmo/cgi-bin; ln -s $PWD/sxmo_sendapi.py $_/sxmo_sendapi.py
cd $HOME/.sxmo

export SXMO_MYNUM=$(mmcli -m any -K | grep modem.generic.own-numbers.value | head -n1)
SXMO_MYNUM=${SXMO_MYNUM#*:} SXMO_MYNUM=${SXMO_MYNUM// /} SXMO_MYNUM=${SXMO_MYNUM#+} SXMO_MYNUM=${SXMO_MYNUM#1}
export SXMO_MYHTTP="${SXMO_MYHTTP:-http://ubuasus.local:8000}"
export SXMO_WEBHOOK="${SXMO_WEBHOOK:-https://pbxmyhome.lan/$SXMO_MYNUM/rcvmms.cgi}"
export SXMO_LOGDIR="${SXMO_LOGDIR:-$PWD}"
export SXMO_TMPDIR="${SXMO_TMPDIR:-$PWD/tmp}"

for dir in "$SXMO_LOGDIR" "$SXMO_TMPDIR"
do
	mkdir -p "$dir"
	chmod 755 "$dir"
done

. sxmo_common.sh

dbus-monitor --system "interface='org.freedesktop.ModemManager1.Modem.Messaging',type='signal',member='Added'" | while read -r line; do
	[[ "$line" == signal* ]] && sxmo_modem.sh checkfornewtexts
done &

sxmo_poll.sh 300 sxmo_modem.sh checkfornewtexts &

MESSAGE=""
dbus-monitor "interface='org.ofono.mms.Service',type='signal',member='MessageAdded'" "interface='org.ofono.mms.Message',type='signal',member='PropertyChanged'" | while read -r line; do
	if [[ "$line" == *object\ path* ]]; then
		MESSAGE=${line} MESSAGE=${MESSAGE#*\"} MESSAGE=${MESSAGE%\"*}
	fi
	if [[ "$line" == *string\ \"received\"* || "$line" == *string\ \"sent\"* ]]; then
		sxmo_mms.sh processmms "$MESSAGE"
		MESSAGE=""
	fi
done &

python3 -m http.server --cgi &

wait
