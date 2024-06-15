#!/bin/ksh

PATH=${PWD}:$PATH
. getenv.sh

LOCAL_DID=${MSGAPP_DID#+1}

print "Content-Type: text/html\n"

cd cache

Contacts=$(urlencode -d "$QUERY_STRING")

cat - <<EOF
<style>
blockquote {
  margin-left: 50%;
}
.theirChat {
    background: lightgrey;
    font-size: .75em;
    color: black;
    text-align: left;
}
.myChat {
    background: lightgreen;
    font-size: .75em;
    color: black;
    text-align: left;
}
</style>
EOF

typeset -A Links
for f in *
do
	[ -h "$f" ] && Links[$(readlink "$f")]="$f"
done

Contacts=${Contacts%%;*}

if [ -f "${Contacts:-.}/.did" ]; then
	cd "$Contacts"
	rm -f .new

	now=$(date "+%s")
	if [ -f .del ]; then
		before=$(<.del)
	else
		before=0
	fi
	let secs=$now-$before-60
	if [ "$secs" -lt 0 ]; then
		secs="<span style='color: red;'>** ${secs#-} secs **</span>"
	else
		secs=""
	fi

	auth="#"; [ -f .auth -o "$MSGAPP_BACKEND" = "SXMO" ] && auth=""
	print "<h3>${auth}Message folder: $Contacts $secs</h3>"
fi

ls -1tl --time-style="+%a,-%b-%-d-at-%I:%M:%S-%p" | while read -r line
do
	print -- "$line" | read -r x x x x x tstamp f x

	[ ! "$f" ] && continue

	tstamp=${tstamp//-/ }

	if [ -h "$f" ]; then
		from=$(readlink "$f") from=${from#../} from=${from%%/*}
		x=${Links[$from]}; [ "$x" ] && from=$x
		from+=": "
	else
		from=""
	fi

	side=${f%%:*} ext=${f##*.}

	if [ "$ext" = "txt" ]; then
		content=$(fold -s -w40 "$f" | sed -e "s/$/<br>/"); content=${content%<br>}
	fi

	if [ "$side" = "xmt" ]; then
		tiploc="tooltip-left"
	else
		tiploc="tooltip-right"
	fi

	what=$(file -L "$f" 2>/dev/null)

	[ "$side" = "xmt" ] && print "<blockquote>"

	if [ -f "$f/.did" ]; then
		if [ -f "$f/.new" ]; then
			new="warning"
		else
			new=""
		fi
		if [[ "$f" == @* ]]; then
			:
		#elif [ "${LOCAL_DID}" = "$(<$f/.did)" ]; then
		#	:
		else
			display=${Links[$f]}
			if [ "$display" ]; then
				value="$display;$f"
			else
				value="$f" display="${f//,/ }"
			fi

			auth="#"; [ -f "$f/.auth" -o "$MSGAPP_BACKEND" = "SXMO" ] && auth=""
			print "<button data-tooltip=\"${tstamp}\" class=\"${new} ${tiploc}\" onclick=\"contacts.value='$value'; get_conversation()\">${auth}${display}</button>"
		fi

	elif [ "$ext" = "txt" ]; then
		if [ "$side" = "xmt" ]; then
			chat="myChat"
		else
			chat="theirChat"
		fi
		print "<button data-tooltip=\"${from}${tstamp}\" class=\"${chat} ${tiploc}\">${content}</button><br>"

	elif [[ "$what" == *image* ]]; then
		print -- "<img title=\"${from}${tstamp}\" style=\"border-radius: 5%;\" src=\"${PWD#$DOCUMENT_ROOT}/$f\" width=200><br><br>"

	else
		print -- "<a href=\"${PWD#$DOCUMENT_ROOT}/$f\">attachment.${ext}</a><br>"
	fi

	[ "$side" = "xmt" ] && print "</blockquote>"
done
