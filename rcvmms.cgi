#!/bin/ksh

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
