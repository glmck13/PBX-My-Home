#!/bin/ksh

print "Content-Type: text/plain\n"

[ "$QUERY_STRING" ] && exec >./debug/env$$.txt 2>&1

export
cat -
