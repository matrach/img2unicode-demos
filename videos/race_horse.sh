#!/bin/bash

BASEDIR=`dirname $0`
while :; do
for f in $BASEDIR/race_horse/horseanim*.txt; do cat $f; sleep 0.1; clear; done;
done;
