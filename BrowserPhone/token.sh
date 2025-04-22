#!/bin/bash

Seed=""
token="${QUERY_STRING:-$1,}"
token=$(echo -n "${token%,*}${Seed}" | md5sum)
echo -n "${token%% *}"
