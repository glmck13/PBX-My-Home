#!/bin/ksh

function exec_a2pcmds
{
	body=""

	if [[ "$Mime" != *text* ]]; then
		return 1

	elif [[ "$Content" == *#!on* ]]; then
		body="Welcome! You just elected to turn on messages from [$FLOWROUTE_A2P]. You can turn off messages at any time by texting back the string: #!off.  For help, text: #!help."
		mkdir -p $Did
		echo "$Did" >$Did/.did
		echo "$Content" >$Did/.auth

	elif [[ "$Content" == *#!off* ]]; then
		body="You just elected to turn off messages from [$FLOWROUTE_A2P]. Goodbye!"
		rm -fr $Did
		find -L . -type l | xargs rm -f

	elif [[ "$Content" == *#!help* ]]; then
		if [ -f $Did/.auth ]; then
			body="Messages from [$FLOWROUTE_A2P] are currently turned on. You can turn off messages at any time by texting back the string: #!off.  For help, text: #!help."
		else
			body="Messages from [$FLOWROUTE_A2P] are currently turned off. You can turn on messages at any time by texting back the string: #!on.  For help, text: #!help."
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
