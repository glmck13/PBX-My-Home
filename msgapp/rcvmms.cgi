#!/bin/ksh

function exec_a2pcmds
{
	body=""

	if [[ "$Mime" != *text* ]]; then
		return 1

	elif [[ "$Content" == *#!START* ]]; then
		body="You just elected to turn ON messages from [$FLOWROUTE_A2PID] using this number. You can turn OFF messages at any time by texting back the string #!STOP.  For help, text #!HELP. Welcome to my world!"
		mkdir -p $Did
		echo "$Did" >$Did/.did
		echo "$Content" >$Did/.auth

	elif [[ "$Content" == *#!STOP* ]]; then
		body="You just elected to turn OFF messages from [$FLOWROUTE_A2PID], and will receive no further communications from this number. Goodbye!"
		rm -fr $Did
		find -L . -type l | xargs rm -f

	elif [[ "$Content" == *#!HELP* ]]; then
		if [ -f $Did/.auth ]; then
			body="Messages from [$FLOWROUTE_A2PID] are currently turned ON. You can turn OFF messages at any time by texting back the string #!STOP. For additional questions, contact me at [$FLOWROUTE_A2PHONE]. Thanks!"
		else
			body="Messages from [$FLOWROUTE_A2PID] are currently turned OFF. You can turn ON messages at any time by texting back the string #!START. For additional questions, contact me at [$FLOWROUTE_A2PHONE]. Thanks!"
		fi
	else
		return 1
	fi

	if [ "$body " ]; then
		curl -s "${FLOWROUTE_URL}" -X POST -u "${FLOWROUTE_KEY}":"${FLOWROUTE_SECRET}" -H 'Content-Type: application/vnd.api+json' -d @- <<-EOF 2>&1
			{ "data": { "type": "message", "attributes": { "to": "+1${Did}", "from": "${FLOWROUTE_DID}", "body": "${body}", "is_mms": false, "media_urls": [] } } }
		EOF
	fi

	return 0
}

PATH=${PWD}:$PATH
. getenv.sh

print "Content-Type: text/plain\n"

LOCAL_DID=${FLOWROUTE_DID#+1}
cd cache

mkdir -p $LOCAL_DID; [ ! -h @DID ] && ln -s $LOCAL_DID @DID
cd $LOCAL_DID; echo $LOCAL_DID >.did
cd - >/dev/null

tee ../debug/rcv$$.json | parsemms.py | while read -r Did Mime Content
do
	exec_a2pcmds && continue

	mkdir -p $Did
	cd $Did; echo $Did >.did; >.new

	Base=rcv:$(uuidgen)
	ext=$Mime ext=${ext#*/}

	if [[ "$Mime" == *text* ]]; then
		ext="txt"
		Base=$Base.$ext
		Content=${Content%[\'\"]} Content=${Content#[\'\"]}
		print "$Content" >$Base
	else
		Base=$Base.$ext
		curl -s "$Content" >$Base
	fi

	cd - >/dev/null

	for dir in *$Did* $LOCAL_DID
	do
		[ "$dir" = "$Did" ] && continue

		cd $dir; >.new
		ln -s ../$Did/$Base $Base
		cd - >/dev/null
	done
done
