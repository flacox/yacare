#!/bin/sh
#
# Public domain
# Author: roman [] tsisyk.com
#
# Usage: ./me url [youtube-dl parameters]
#

COOKIE_FILE=yt_cookies
mplayer -cookies -cookies-file ${COOKIE_FILE} $(youtube-dl -f mp4 -g --cookies ${COOKIE_FILE} $*)
