# systemd Utilities

* `nspawn_{add,remove}_dev.sh` and `nspawn_prune_deviceallow.py`: Scripts for adding and removing special files to systemd-nspawn priviledged containers (i.e. `--private-users=false`)
* `{start,stop}_gnome.sh` and `eloston-gnome@.service`: systemd service to launch a GNOME Wayland session on any tty with login, without needing gdm3 to be running (but it needs to be installed for some config)
	- Recommended: Remove the GNOME Login Keyring password via seahorse to have the keyring be accessible on auto-login.
