#!/bin/bash

command -v shopt > /dev/null && shopt -s expand_aliases

sxmo_log() {
	printf "%s %s: %s\n" "$(date +%H:%M:%S)" "${0##*/}" "$*" | tee -a $SXMO_LOGDIR/sxmo.log 1>&2
}

sxmo_debug() {
	if [ -n "$SXMO_DEBUG" ]; then
		printf "%s %s DEBUG: %s\n" "$(date +%H:%M:%S)" "${0##*/}" "$*" | tee -a $SXMO_LOGDIR/sxmo.log 1>&2
	fi
}
