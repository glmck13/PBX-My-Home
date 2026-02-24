#!/usr/bin/env bash

source $HOME/awsenv/bin/activate

cd $HOME/local

. ./awscreds.sh

./aws.py >/tmp/aws.log 2>&1 &
