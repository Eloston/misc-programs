#!/bin/bash -e

if [ -z "$1" ];
then
	pushd $(dirname $(readlink -f $0)) >/dev/null
	printf 'ERROR: Please specify skeleton: %s\n' $(ls -d */)
	popd >/dev/null
	exit 1
fi
printf 'Initializing git skeleton for: %s\n' "$1"

# Copy skeleton to current directory
cp -ri $(dirname $(readlink -f $0))/$1/. .
