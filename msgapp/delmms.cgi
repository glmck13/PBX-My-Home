#!/bin/ksh

PATH=${PWD}:$PATH
. getenv.sh

print "Content-Type: text/plain\n"

cd cache

Base=$(urlencode -d "$QUERY_STRING") Base=${Base//[,;]/ }
Expand=$(echo $Base | xargs -n1 | xargs -I '{}' cat {}/.did 2>/dev/null) Expand=${Expand//[,;]/ }
Contacts=$(echo $Base $Expand | xargs -n1 | grep -E '^[[:digit:]]{10,10}$' | sort | uniq)
Contacts=$(echo $Contacts)
Group=${Contacts// /,}

for dir in ${Group}
do
	rm -fr $dir
done

find -L . -type l | xargs rm -f
