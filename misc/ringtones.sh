#!/bin/ksh

PATH=$HOME/bin:$PATH

trap "" HUP INT QUIT

CDRFILE=/tmp/cdr.txt
TMPFILE=/tmp/cdr$$.txt
RINGTONE=/tmp/ringtone.mp3
RINGPID=/tmp/ringpid.txt
CONFFILE=~/etc/ringtones.conf
AWSCREDS=~/etc/awscreds.conf
#SOCKFILE=/var/run/asterisk/asterisk.ctl

#while [ \! -e $SOCKFILE ]
#do
#	sleep 10
#done

. $AWSCREDS

#asterisk -x 'core waitfullybooted'
#asterisk -x 'dialplan remove extension 6000@default'
#asterisk -x 'dialplan add extension 6000,1,System(/bin/echo\ \"${STRFTIME(${EPOCH},,%m%d%Y-%H:%M:%S)}\"\ \"${CALLERID(all)}${CALLBACK}\"\ >>/tmp/cdr.txt) into default replace'
#asterisk -x 'dialplan add extension 6000,2,Dial(DAHDI/1,20,r(info)) into default replace'
#asterisk -x 'dialplan add extension 6000,3,System(/bin/echo\ \"${STRFTIME(${EPOCH},,%m%d%Y-%H:%M:%S)}\"\ \"${DIALSTATUS}\"\ >>/tmp/cdr.txt) into default replace'
#asterisk -x 'dialplan add extension 6000,4,Set(GLOBAL(CALLBACK)=\"\") into default replace'

>$CDRFILE; chmod 777 $CDRFILE

#tail -f $CDRFILE | while read cdr
while true
do
	ncat -l 4573 </dev/null >$TMPFILE
	now=$(date)
	sed -e "s/^/$now|/" <$TMPFILE >>$CDRFILE
	cdr=$(grep agi_callerid: $TMPFILE)
	cdr=${cdr##* } cdr=${cdr##*<} cdr=${cdr%>*} cdr=${cdr//+1/}

	[ -f $RINGPID ] && kill $(<$RINGPID) >/dev/null 2>&1
	rm -f $RINGTONE $RINGPID

	[ ! "$cdr" ] && continue

	[[ $cdr == 0* ]] && continue

	[[ $cdr == *NOANSWER ]] && continue

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
