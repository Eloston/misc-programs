#!/bin/bash

# Removes a device created with nspawn_add_dev.sh

set -eu

# Get help
if [ $# -lt 2 ] || [ "$1" = '-h' ] || [ "$1" = '--help' ]; then
	printf 'Usage: container_name device_path\n'
	exit 0
fi

_machine=$1
_device=$(readlink -f $2)

printf 'Removing device %s from container %s...\n' $_device $_machine

# check if machine is running
if ! systemctl is-active --quiet systemd-nspawn@$_machine.service; then
	printf 'ERROR: nspawn container %s is not running\n' $_machine >&2
	exit 1
fi

# Remove unneeded DeviceAllow for our device
$(dirname $(readlink -f $0))/nspawn_get_deviceallow.py $_machine $_device

if systemd-run --wait --machine=$_machine /usr/bin/test -e $_device; then
	systemd-mount --machine=$_machine --unmount $_device
	# Unmount in this manner leaves behind an extra file for some reason
	systemd-run --wait --machine=$_machine /bin/rm $_device
fi
