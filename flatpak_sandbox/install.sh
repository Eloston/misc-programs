#!/bin/bash

set -eu -o pipefail

_flatpak_id=$1
_ROOT_DIR=$(dirname $(readlink -f $0))
_mount_unit=$(systemd-escape --path "/home/eloston/.local/share/flatpak/overrides/$_flatpak_id").mount

$_ROOT_DIR/create-mount.sh $_flatpak_id
sudo mv -i $_mount_unit /etc/systemd/system
sudo cp -i $_ROOT_DIR/tmp-flatpak-overrides@.service /etc/systemd/system
sudo systemctl disable $_mount_unit
sudo systemctl daemon-reload
sudo systemctl enable $_mount_unit
sudo systemctl start $_mount_unit
