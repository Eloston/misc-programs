# D-Bus Proxy

This is a Python-based proxy for D-Bus message buses; i.e. it acts as a middleman between D-Bus clients (e.g. GNOME applications) and dbus-daemon. It logs messages sent between them to the console.

## Background

I originally wrote this to override GNOME Proxy settings for a specific application, but I realized much later that proxy settings are read directly from dconf; D-Bus is only used for writing values and listening for changes (via dconf-service). By the time I realized, I had already written what is available here.

## Usage

Tested on Python 3. Requires PyGObject.

1. Run the proxy: `python3 dbus_proxy.py /path/to/bus_proxy` where `/path/to/proxy_bus` is a path for a new UNIX socket to be created.
2. Set the environment variable `DBUS_SESSION_BUS_ADDRESS` to `unix:path=/path/to/proxy_bus` for the application that should use the proxy.
3. To shut down the proxy:
    a. Since the proxy doesn't have any clean-up mechanisms, make sure to **first** close all applications that use the proxy.
    b. Kill the proxy process, e.g. a keyboard interrupt if running in a terminal

The proxy has other command-line arguments. Pass in `--help` for more info.

## Credits

Software used:

* PyGObject

Documentation and references:

* [PyGObject API Reference](//lazka.github.io/pgi-docs/)
    * [Source Code](//github.com/pygobject/pgi-docgen)
* [PyGObject general documentation on Read The Docs](//pygobject.readthedocs.io/en/latest/index.html)
* [GNOME API Reference](//developer.gnome.org/references)
* [alban's dbus-daemon-proxy](//github.com/alban/dbus-daemon-proxy)
* [pydbus](//github.com/LEW21/pydbus)
