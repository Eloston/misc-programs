#!/bin/bash 

set -eu -o pipefail

_flatpak_id=$1
_mount_unit=$(systemd-escape --path "/home/eloston/.local/share/flatpak/overrides/$_flatpak_id").mount

sudo systemctl stop $_mount_unit
echo "Running Flatseal to update deps... Close it when you're done editing."
flatpak --user run com.github.tchx84.Flatseal
sudo systemctl start $_mount_unit
