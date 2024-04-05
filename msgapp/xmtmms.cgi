#!/bin/ksh

PATH=${SCRIPT_FILENAME%/*}:$PATH
. getenv.sh

print "Content-Type: text/plain\n"

LOCAL_DID=${FLOWROUTE_DID#+1}
#FLOWROUTE_URL=$MSGAPP_URL/env.cgi?browser
cd cache

Base=$(urlencode -d "$QUERY_STRING") Base=${Base//[,;]/ }
Expand=$(echo $Base | xargs -n1 | xargs -I '{}' cat {}/.did 2>/dev/null) Expand=${Expand//[,;]/ }
Contacts=$(echo $Base $Expand | xargs -n1 | grep -E '^[[:digit:]]{10,10}$' | sort | uniq)
Contacts=$(echo $Contacts)
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
		identify $v-bin.$ext 2>/dev/null | read x x dim x
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

for dir in ${Contacts} ${Group}
do
	mkdir -p $dir
	cd $dir; echo ${dir} >.did
	[ "$Text" -a ! -h "$Text" ] && ln -s ../$LOCAL_DID/$Text $Text
	[ "$Media" -a ! -h "$Media" ] && ln -s ../$LOCAL_DID/$Media $Media
	cd - >/dev/null
done

[ "$Group" ] && [ "$Handle" ] && ln -s "$Group" "$Handle"

if [ "$Text" -o "$Media" ]; then

cd $LOCAL_DID

if [ "$Media" ]; then
	is_mms="true"
	media_urls="[\"${MSGAPP_URL}/cache/${LOCAL_DID}/${Media}\"]"
else
	is_mms="false"
	media_urls="[]"
fi

if [ "$Text" ]; then
	body=$(<${Text}) body=${body//\"/\\\"}
else
	body="null"
fi

for dst in ${Contacts}
do
	curl -s "${FLOWROUTE_URL}" -X POST -u "${FLOWROUTE_KEY}":"${FLOWROUTE_SECRET}" -H 'Content-Type: application/vnd.api+json' -d @- <<-EOF 2>&1
	{
	"data": {
		"type": "message",
		"attributes": {
			"to": "+1${dst}",
			"from": "${FLOWROUTE_DID}",
			"body": "${body}",
			"is_mms": ${is_mms},
			"media_urls": ${media_urls}
		}
	}
	}
	EOF
done

cd - >/dev/null
fi