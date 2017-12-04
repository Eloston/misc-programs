#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Intercepts the GNOME Proxy advertised via D-Bus with the one specified to this program'''

import sys

from gi.repository import Gio, GLib

def _signal_received(connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
    '''
    Forward a received signal to the other connection. The other connection is specified in
    user_data.

    This implements the Gio.DBusSignalCallback interface.
    '''
    user_data.emit_signal(
        destination_bus_name=user_data.get_unique_name(),
        object_path=object_path,
        interface_name=interface_name,
        signal_name=signal_name,
        parameters=parameters
    )

def _get_regular_client_connection():
    '''Connects to the real D-Bus session bus as a client'''
    client_connection = Gio.DBusConnection.new_for_address_sync(
            address='unix:path=/run/user/1000/bus', # TODO: Find this in a more intelligent manner
            flags=Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
                | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
            observer=None,
            cancellable=None,
    )
    return client_connection

def _get_stdin_server_connection(client_connection):
    '''
    Initializes the D-Bus server running on standard input
    '''
    stdin_stream = Gio.UnixInputStream.new(
        fd=sys.stdin.fileno(),
        close_fd=False,
    )
    stdout_stream = Gio.UnixOutputStream.new(
        fd=sys.stdout.fileno(),
        close_fd=False,
    )
    io_stream = Gio.SimpleIOStream.new(
        input_stream=stdin_stream,
        output_stream=stdout_stream,
    )
    server_connection = Gio.DBusConnection.new_sync(
        stream=io_stream,
        guid=client_connection.get_guid(),
        flags=Gio.DBusConnectionFlags.AUTHENTICATION_SERVER
            | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
        observer=None,
        cancellable=None,
    )
    return server_connection

def main():
    client_connection = _get_regular_client_connection()
    server_connection = _get_stdin_server_connection(client_connection)

    print('client bus name: {}'.format(client_connection.get_unique_name()), file=sys.stderr)
    print('server bus name: {}'.format(server_connection.get_unique_name()), file=sys.stderr)

    # Hook into signals
    server_connection.signal_subscribe(
        sender=None,
        interface_name=None,
        member=None,
        object_path=None,
        arg0=None,
        flags=Gio.DBusSignalFlags.NONE,
        callback=_signal_received,
        user_data=client_connection,
    )
    client_connection.signal_subscribe(
        sender=None,
        interface_name=None,
        member=None,
        object_path=None,
        arg0=None,
        flags=Gio.DBusSignalFlags.NONE,
        callback=_signal_received,
        user_data=server_connection,
    )

    # TODO: Hook into messages

if __name__ == '__main__':
    main()
