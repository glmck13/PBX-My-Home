#!/bin/bash

command -v shopt > /dev/null && shopt -s expand_aliases

sxmo_log() {
	printf "%s %s: %s\n" "$(date +%H:%M:%S)" "${0##*/}" "$*" >> $SXMO_LOGDIR/sxmo.log
}
