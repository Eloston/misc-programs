#!/bin/bash -eu

printf "Using resolution: %s" "$1"

_RESOLUTION="$1"

# https://stackoverflow.com/a/2173421
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# Dependencies: apt install gnome-shell gnome-session firefox-esr libgl1-mesa-dri dbus-user-session gnome-remote-desktop pipewire-audio winpr-utils gnome-keyring fonts-noto fonts-noto-color-emoji fonts-noto-ui-core fonts-noto-mono fonts-noto-cjk fonts-droid-fallback

# Need to configure gnome-remote-desktop first using these steps:
# winpr-makecert -rdp -n rdp-security -path .
# grdctl rdp enable
# grdctl rdp set-tls-cert path/to/rdp-security.crt
# grdctl rdp set-tls-key path/to/rdp-security.key
# grdctl rdp disable-view-only
# grdctl --headless rdp set-credentials admin 1234
# grdctl --headless rdp status --show-credentials
#
# Start gnome-remote-desktop-daemon headless in background
/usr/libexec/gnome-remote-desktop-daemon --headless &

# gnome-session doesn't seem necessary right now
# Re-enable it if there's some error that would be fixed by enabling it
#gnome-session --builtin

# Start headless gnome-shell
gnome-shell --wayland --headless --virtual-monitor "$_RESOLUTION" --no-x11
