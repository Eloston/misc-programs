#!/bin/bash -eux

sudo systemctl stop gdm3
sudo systemctl start eloston-gnome@tty1

#~/software/unlock-keyring.py <<<1234
