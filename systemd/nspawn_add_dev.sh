#!/bin/bash

# Allows a priviledged (--private-users=false) systemd-nspawn container have access to a special file
# To revert an add, use nspawn_remove_dev.sh

set -eu

# Get help
if [ $# -lt 2 ] || [ "$1" = '-h' ] || [ "$1" = '--help' ]; then
	printf 'Usage: container_name device_path\n'
	exit 0
fi

_machine=$1
_device=$(readlink -f $2)

printf 'Adding device %s to container %s...\n' $_device $_machine

# check if machine is running
if ! systemctl is-active --quiet systemd-nspawn@$_machine.service; then
	printf 'ERROR: nspawn container %s is not running\n' $_machine >&2
	exit 1
fi

# check if device path exists
if [ ! -e $_device ]; then
	printf 'ERROR: Device path %s does not exist\n' $_device >&2
	exit 1
fi
if [ -d $_device ]; then
	printf 'ERROR: Device path %s is a directory\n' $_device >&2
	exit 1
fi

# Grant cgroups permission
systemctl set-property --runtime systemd-nspawn@$_machine.service "DeviceAllow=$_device rwm"
# Actually make file available inside container
machinectl bind --mkdir $_machine $_device
