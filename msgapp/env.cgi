#!/bin/ksh

print "Content-Type: text/plain\n"

[ "$QUERY_STRING" != "browser" ] && exec >./debug/$$.txt 2>&1

export
cat -
