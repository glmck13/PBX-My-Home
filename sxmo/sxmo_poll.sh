#!/bin/bash

timeout="$1"
shift

finish() {
	kill "$CMDPID"
	kill "$SLEEPPID"
	exit 0
}

trap 'finish' TERM INT EXIT

while : ; do
	sleep $(($timeout - $(date +%s) % $timeout)) &
	SLEEPPID="$!"
	wait "$SLEEPPID"

	"$@" &
	CMDPID="$!"
	wait "$CMDPID"
done
