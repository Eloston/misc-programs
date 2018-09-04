# Atom feeds

This directory contains scripts for outputting Atom feeds to standard output.

Currently, all scripts read data from standard input so they can be used as Liferea conversion filters for URL subscriptions.

Current conversion filters:

* `lenovo_pcsupport_driver_software.py` - Generates an Atom feed of one item for the latest version of a pcsupport.lenovo.com driver download. Tested on firmware update downloads.
* `omahaproxy.py` - Converts omahaproxy.appspot.com data into an Atom feed.
