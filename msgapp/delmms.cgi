#!/bin/ksh

PATH=${PWD}:$PATH
. getenv.sh

print "Content-Type: text/plain\n"

cd cache

Base=$(urlencode -d "$QUERY_STRING") Base=${Base//[,;]/ }
Expand=$(echo $Base | xargs -n1 | xargs -I '{}' cat {}/.did 2>/dev/null) Expand=${Expand//[,;]/ }
Contacts=$(echo $Base $Expand | xargs -n1 | grep -E '^[[:digit:]]{5,10}$' | sort | uniq)
Contacts=$(echo $Contacts)
Group=${Contacts// /,}

#for dir in ${Contacts//$Group/} ${Group}
for dir in ${Group}
do
	cd $dir || continue

	now=$(date "+%s")
	if [ -f .del ]; then
		before=$(<.del)
	else
		before=0
	fi
	echo $now >.del

	let secs=$now-$before-60

	if [ "$secs" -lt 0 ]; then
		cd - >/dev/null
		rm -fr $dir
	else
		rm -f *
		cd - >/dev/null
	fi
done

find -L . -type l | xargs rm -f
