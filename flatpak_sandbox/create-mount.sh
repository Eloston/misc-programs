#!/bin/bash

set -eu -o pipefail

_flatpak_id=$1
_flatpak_override_src="/tmp/.flatpak-overrides/$_flatpak_id"
_flatpak_override_dst="/home/eloston/.local/share/flatpak/overrides/$_flatpak_id"

if [ ! -f "$_flatpak_override_dst" ]; then
	echo "ERROR: Missing original Flatpak overrides file at $_flatpak_override_dst" >&2
	exit 1
fi

cat <<EOF > $(systemd-escape --path "$_flatpak_override_dst").mount
[Unit]
Description=Mounts Flatpak overrides for $_flatpak_id to /tmp so that they are discarded after shutdown
DefaultDependencies=no
Conflicts=umount.target
Before=umount.target
# Ensure after tmpfs is ready on /tmp
After=tmp.mount tmp-flatpak-overrides@$_flatpak_id.service
BindsTo=tmp-flatpak-overrides@$_flatpak_id.service

[Mount]
What=$_flatpak_override_src
Where=$_flatpak_override_dst
Type=none
Options=bind

[Install]
WantedBy=tmp.mount
EOF
