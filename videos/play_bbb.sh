#!/bin/bash

play -q bbb_audio.ogg &
for i in bbb-ascii+braille-32h-24bit-15fps/*; do cat $i; sleep 0.0666; clear;  done;
