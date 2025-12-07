#!/bin/bash
set -euo pipefail

# from https://github.com/stackcoder/doublepress

if [ "$1" !=  "button/power PBTN 00000080 00000000" ]; then
  exit 0
fi

logger "$0: Power button pressed"
/usr/local/sbin/doublepress.sh &
