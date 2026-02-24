#!/usr/bin/env bash

source $HOME/a2genv/bin/activate

cd $HOME/local

. ./geminicreds.sh

./a2g.py >/tmp/a2g.log 2>&1 &
