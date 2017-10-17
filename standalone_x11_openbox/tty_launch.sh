#!/bin/bash

set -e -u

# Runs the given command in a new session of openbox
# Usage: run_in_x11_openbox.sh command [argument [...]]
# This should be invoked from a virtual terminal console

SESSION=$(cat /proc/self/sessionid)

if [[ "$(loginctl show-session $SESSION -p Type --value)" != "tty" ]]; then
    printf 'You must run this from a login shell\n'
    exit
fi

CONSOLE=$(fgconsole)
DISPLAY=$("$(dirname $(readlink -f $0))/get_unused_x11_display.py")
CMD_LINE="$*"

tmp_bash_script=$(mktemp /tmp/standalone_x11_openbox_tty_launch.XXXXXXXXXX.sh)
#printf "#!/bin/bash\nxscreensaver -no-splash -display :$DISPLAY &\nxterm &\n$CMD_LINE" > "$tmp_bash_script"
printf "#!/bin/bash\nxscreensaver -no-splash -display :$DISPLAY &\n$CMD_LINE\nopenbox --exit" > "$tmp_bash_script"
chmod +x "$tmp_bash_script"

openbox_startup="/usr/bin/xterm -e '$tmp_bash_script'"

env DISPLAY=$DISPLAY xinit /usr/bin/openbox --config-file "$(dirname $(readlink -f $0))/rc.xml" --sm-disable --startup "$openbox_startup" -- ":$DISPLAY" "vt$CONSOLE"

rm "$tmp_bash_script"

loginctl terminate-session $SESSION
