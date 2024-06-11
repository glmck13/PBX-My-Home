#!/bin/ksh

PATH=${SCRIPT_FILENAME%/*}:$PATH
. getenv.sh

print "Content-Type: text/plain\n"

LOCAL_DID=${MSGAPP_DID#+1}
if [ "${REQUEST_METHOD}" = "PATCH" ]; then
	MSGAPP_SENDAPI=$MSGAPP_MYURL/env.cgi
	print "*** TEST MODE ***"
	TEST_MODE="on"
else
	TEST_MODE="off"
fi

cd cache

Base=$(urlencode -d "$QUERY_STRING") Base=${Base//[,;]/ }
Expand=$(echo $Base | xargs -n1 | xargs -I '{}' cat {}/.did 2>/dev/null) Expand=${Expand//[,;]/ }
Contacts=$(echo $Base $Expand | xargs -n1 | grep -E '^[[:digit:]]{5,10}$' | sort | uniq)
Contacts=$(echo $Contacts)

if [ "$MSGAPP_BACKEND" != "SXMO" ]; then
for dir in ${Contacts}
do
	if [ ! -f $dir/.auth ]; then
		Contacts=${Contacts//$dir/}
		print "No A2P authorization on file for $dir!"
	fi
done
Contacts=$(echo $Contacts)
fi

Group=${Contacts// /,}

Handle=""
for f in ${Base}
do
	[[ "$f" == @* ]] || continue
	[ ! -h "$f" ] && Handle="$f"
done
Text="" Media=""

mkdir -p $LOCAL_DID; [ ! -h @DID ] && ln -s $LOCAL_DID @DID
cd $LOCAL_DID; echo $LOCAL_DID >.did

split -l1 -t,
for x in xaa,xab xac,xad
do
	k=${x%,*} v=${x#*,}
	[ -f "$k" -a -f "$v" ] || continue

	k=$(<$k) v=${x#*,} ext=$k ext=${ext#*/} ext=${ext%;*}
	base64 -d <$v >$v-bin 2>/dev/null
	[ -s $v-bin ] || continue

	Base=xmt:$(uuidgen)

	if [[ "$k" == *image* ]]; then
		mv $v-bin $v-bin.$ext
		identify $v-bin.$ext 2>/dev/null | read -r x x dim x
		dim=${dim%%x*}
		Media=$Base.$ext
		if [ ${dim:-0} -gt 1000 ]; then
			convert -resize 1000x $v-bin.$ext $v-bin-small.$ext
			mv $v-bin-small.$ext $Media
		else
			mv $v-bin.$ext $Media
		fi
		ls -l $Media
	elif [[ "$k" == *words* ]]; then
		ext="txt"
		urlencode -d $(<$v-bin) >$v-bin.$ext
		Text=$Base.$ext
		mv $v-bin.$ext $Text
		ls -l $Text
	else
		dim=$(stat -c %s $v-bin)
		if [ ${dim:-0} -lt 750000 ]; then
			Media=$Base.$ext
			mv $v-bin $Media
			ls -l $Media
		else
			print "Media size=${dim} exceeds 750K limit"
		fi
	fi
done
rm -f x?? x??-*
cd - >/dev/null

distro=${Group}
[ "$MSGAPP_BACKEND" = "SXMO" ] || distro+=" ${Contacts//$Group/}"

for dir in ${distro}
do
	mkdir -p $dir
	cd $dir; echo ${dir} >.did
	[ "$Text" -a ! -h "$Text" ] && ln -s ../$LOCAL_DID/$Text $Text
	[ "$Media" -a ! -h "$Media" ] && ln -s ../$LOCAL_DID/$Media $Media
	cd - >/dev/null
done

if [ "$Group" ]; then
	if [ "$Handle" ]; then
		typeset -A Links	
		for f in *
		do
			[ -h "$f" ] && Links[$(readlink "$f")]="$f"
		done
		if [ "$Handle" != "@-" ]; then
			ln -s "$Group" "$Handle"
		else
			rm -f "${Links[$Group]}"
		fi
	fi
fi

if [ "$Text" -o "$Media" ]; then

cd $LOCAL_DID

urls=""
if [ "$Media" ]; then
	is_mms="true"
	urls+="${MSGAPP_MYURL}/cache/${LOCAL_DID}/${Media}"
else
	is_mms="false"
fi

if [ "$Text" ]; then
	if [ "$MSGAPP_BACKEND" = "SXMO" ]; then
		urls+=" ${MSGAPP_MYURL}/cache/${LOCAL_DID}/${Text}"
		body="null"
	else
		body=$(<${Text}) body=\"${body//\"/\\\"}\"
	fi
else
	body="null"
fi
urls="[\"$(echo $urls | sed -e "s/  */\",\"/g")\"]"
[ "$urls" = '[""]' ] && urls="[]"

distro=""
for dst in ${Contacts}
do
	[[ "$dst" == ?????????? ]] && dst="+1$dst"
	distro+=" \"$dst\""
done

if [ "$MSGAPP_BACKEND" = "SXMO" ]; then
	[ "$distro" ] && distro="[$(echo $distro | sed -e "s/  */,/g")]"
fi

for dst in $distro
do
	curl -sk "${MSGAPP_SENDAPI}" -X POST -u "${MSGAPP_KEY}":"${MSGAPP_SECRET}" -H 'Content-Type: application/vnd.api+json' -d @- <<-EOF 2>&1
	{
	"data": {
		"type": "message",
		"attributes": {
			"to": ${dst},
			"from": "${MSGAPP_DID}",
			"body": ${body},
			"is_mms": ${is_mms},
			"media_urls": ${urls}
		}
	}
	}
	EOF
	[ "$TEST_MODE" != "on" ] && sleep 1s
done

cd - >/dev/null
fi
