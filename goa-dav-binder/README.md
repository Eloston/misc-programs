# CalDAV/CardDAV Binder for GNOME Online Accounts

Add support for CalDAV/CardDAV in GNOME Online Accounts via a pseudo Nextcloud server.

## Setup and run

Written for Python 3.7 and newer. Requires uvicorn and starlette: `apt install uvicorn python3-starlette`

1. Set environment variables `CALDAV_URL` (Calendaring and Tasks), `CARDDAV_URL` (Contacts), and `WEBDAV_URL` (File access) to the endpoints to forward to. You may omit one or more URLs for services you do not want to enable.
	* e.g. for FastMail, set the following:

	```
	export CALDAV_URL=https://caldav.fastmail.com/dav/calendars
	export CARDDAV_URL=https://carddav.fastmail.com/dav/addressbooks
	```

2. Run the server:
	* Run directly: `python3 goa_dav_binder.py`
	* Run with automatic reloading on code changes: `uvicorn --reload --port=9264 goa_dav_binder:app`
	* Run as systemd service: TODO
3. Go to GNOME Online Accounts, and add a new Nextcloud account. Set the server to `http://localhost:9264`, and use your service's username and password.

## Troubleshooting

### My Calendar and Tasks do not show up!

You probably set the wrong CalDAV URL. The CalDAV URL must return the [`CALDAV:calendar-home-set` property](https://www.ietf.org/rfc/rfc4791.html#section-6.2.1) in order for Online Accounts to autodiscover your Calendar and Tasks.

One way to verify this is to visit your CalDAV URL with a web browser, and see if `calendar-home-set` is shown on the page.

## Credits

Based off of [this GitHub Gist](https://gist.github.com/apollo13/f4fc8f33a2700dffb9e11c1b056c53ba)
