#!/bin/ksh

PATH=$HOME/bin:$PATH

trap "" HUP INT QUIT

CDRFILE=/tmp/cdr.txt
TMPFILE=/tmp/cdr$$.txt
RINGTONE=/tmp/ringtone.mp3
RINGPID=/tmp/ringpid.txt
CONFFILE=~/etc/ringtones.conf
AWSCREDS=~/etc/awscreds.conf

. $AWSCREDS

>$CDRFILE; chmod 777 $CDRFILE

#tail -f $CDRFILE | while read cdr
while true
do
	ncat -l 4573 </dev/null >$TMPFILE
	now=$(date)
	sed -e "s/^/$now|/" <$TMPFILE >>$CDRFILE
	cdr=$(grep agi_callerid: $TMPFILE)
	cdr=${cdr#* }

	[ -f $RINGPID ] && kill $(<$RINGPID) >/dev/null 2>&1
	rm -f $RINGTONE $RINGPID

	[ ! "$cdr" ] && continue

	grep "^$cdr" $CONFFILE | IFS=, read number voice ringtone

	if [ "$ringtone" ]; then
		print "$ringtone" | AWS_VOICE=$voice aws-polly.sh >$RINGTONE
	else
		print "Call from $(print "$cdr" | sed -e "s/./& /g")" | aws-polly.sh >$RINGTONE
	fi

	(
		loop=1; while (( loop-- > 0 ))
		do
			play $RINGTONE vol 2.0 >/dev/null 2>&1; sleep 3
		done
		rm -f $RINGTONE $RINGPID
	) &

	print "$!" >$RINGPID
done
