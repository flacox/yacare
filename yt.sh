#!/usr/bin/bash

rm -f /tmp/fifo.input
mkfifo /tmp/fifo.input

rm -f /tmp/fifo.output
mkfifo /tmp/fifo.output

youtube-dl --no-part -o - https://www.youtube.com/watch?v=$1 1> /tmp/fifo.output &
mplayer -fs -input file=/tmp/fifo.input /tmp/fifo.output

