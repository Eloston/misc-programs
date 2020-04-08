#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Prunes systemd-nspawn runtime DeviceAllow= statements after a device removal

It updates the runtime properties via:
systemctl set-property --runtime systemd-nspawn@MACHINE.service ...
"""

from pathlib import Path
import argparse
import subprocess

_CONF_BASEPATH = '/run/systemd/system.control/systemd-nspawn@{machine}.service.d/50-DeviceAllow.conf'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('machine', help='systemd-nspawn machine name')
    parser.add_argument('prune_device', nargs='*', help='Device paths to prune')

    args = parser.parse_args()

    conf_text = Path(_CONF_BASEPATH.format(machine=args.machine)).read_text()

    prune_device = set(args.prune_device)

    deviceallow_list = list()
    for line in conf_text.splitlines():
        if not line.startswith('DeviceAllow='):
            continue
        _, rule = line.split('=', 1)
        if rule.split(' ', 1)[0] in prune_device:
            continue
        deviceallow_list.append(rule)

    # The first DeviceAllow entry should be blank, meaning all previous DeviceAllow
    # entires are invalidated
    assert not len(deviceallow_list[0])

    print('New DeviceAllow list:', deviceallow_list)

    deviceallow_list = [f'DeviceAllow={x}' for x in deviceallow_list]
    subprocess.run(['systemctl', 'set-property', '--runtime', f'systemd-nspawn@{args.machine}.service', *deviceallow_list], check=True)

if __name__ == '__main__':
    main()
