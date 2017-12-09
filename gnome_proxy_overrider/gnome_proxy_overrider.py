#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
TODO: Rewrite description
Intercepts the GNOME Proxy advertised via D-Bus with the one specified to this program
'''

# TODO: Add mechanism to safely shut-down via KeyboardInterrupt and other means

import argparse
import logging
import os
import sys

from gi.repository import Gio, GLib, GObject

def _get_unique_name_property(self):
    current_name = self.get_unique_name()
    if current_name:
        return current_name
    else:
        try:
            return self._detected_unique_name
        except AttributeError:
            return None

def _set_unique_name_property(self, value):
    if not Gio.dbus_is_name(value):
        _get_logger().error('Not a valid D-Bus unique name: {}'.format(value))
    self._detected_unique_name = value

Gio.DBusConnection.detected_name = property(
    _get_unique_name_property, _set_unique_name_property)

class _ConnectionType:
    '''Enum for coordinator or worker D-Bus connection types'''
    COORDINATOR = 'coordinator'
    WORKER = 'worker'

class _PyGObject(GObject.Object):
    '''For use in passing data in signal handlers'''
    __gtype_name__ = "PyGObject"

    def __init__(self, payload):
        super().__init__()
        self.payload = payload

def _get_logger(name=None, level=logging.DEBUG):
    '''Gets the named logger'''

    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        if name is None:
            logger.info("Initialized root logger")
        else:
            logger.info("Initialized logger '{}'".format(name))
    return logger

def _callback_close(source_object, res, user_data):
    '''Callback for a D-Bus connection close'''
    if not source_object.close_finish(res):
        _get_logger().error('A close command failed')

def _callback_coordinator_filter(connection, message, incoming, user_data):
    '''Callback for a D-Bus connection filter'''
    other_connection, other_type = user_data
    _get_logger().debug(
        'Message: incoming: {}, other pair: {}, type: {}, path: {}, arg0: {}, member: {}, sender: {}, destination: {}'.format(
            incoming, other_type, message.get_message_type(), message.get_path(), message.get_arg0(), message.get_member(), message.get_sender(), message.get_destination()
        )
    )
    if incoming:
        if other_connection.is_closed():
            _get_logger().debug('Other connection already closed during filter')
            connection.close(
                cancellable=None,
                callback=_callback_close,
                user_data=None,
            )
        else:
            if other_type == _ConnectionType.WORKER:
                name = message.get_destination()
                message_setter = Gio.DBusMessage.set_destination
            elif other_type == _ConnectionType.COORDINATOR:
                name = message.get_sender()
                message_setter = Gio.DBusMessage.set_sender
            else:
                raise ValueError('Unknown other_type: {}'.format(other_type))
            if name and not other_connection.detected_name == name:
                other_connection.detected_name = name
            if not name and other_connection.detected_name:
                if message.get_locked():
                    new_message = message.copy()
                    message._unref()
                    message = new_message
                message_setter(message, other_connection.detected_name)
                message.lock()
            success, _ = other_connection.send_message(message, Gio.DBusSendMessageFlags.PRESERVE_SERIAL)
            if not success:
                _get_logger().error('Failed to send message in other connection')
        # For some reason, all incoming messages need to be dropped to make communication work
        return None
    if connection.is_closed():
        _get_logger().debug('Connection closed during filter')
        other_connection.close(
            cancellable=None,
            callback=_callback_close,
            user_data=None,
        )
    return message

def _hook_dbus_connections(worker_dbus_connection, coordinator_dbus_connection):
    coordinator_dbus_connection.add_filter(
        filter_function=_callback_coordinator_filter,
        user_data=(worker_dbus_connection, _ConnectionType.WORKER),
    )
    worker_dbus_connection.add_filter(
        filter_function=_callback_coordinator_filter,
        user_data=(coordinator_dbus_connection, _ConnectionType.COORDINATOR),
    )

def _callback_new_worker_dbus_connection(source_object, res, coordinator_dbus_connection): #pylint: disable=invalid-name
    worker_dbus_connection = Gio.DBusConnection.new_finish(res)
    _get_logger().debug('Worker GUID: {}'.format(
        worker_dbus_connection.get_guid()
    ))

    _hook_dbus_connections(worker_dbus_connection, coordinator_dbus_connection)

def _callback_new_coordinator_dbus_connection(source_object, res, worker_socket_connection): #pylint: disable=invalid-name
    '''Callback for `Gio.DBusConnection.new_for_address` in context of server setup'''
    coordinator_dbus_connection = Gio.DBusConnection.new_for_address_finish(res)
    _get_logger().debug('Coordinator GUID: {}'.format(
        coordinator_dbus_connection.get_guid()
    ))

    # Create worker D-Bus connection
    Gio.DBusConnection.new(
        stream=worker_socket_connection,
        guid=coordinator_dbus_connection.get_guid(),
        flags=Gio.DBusConnectionFlags.AUTHENTICATION_SERVER
        | Gio.DBusConnectionFlags.AUTHENTICATION_ALLOW_ANONYMOUS,
        observer=None,
        cancellable=None,
        callback=_callback_new_worker_dbus_connection,
        user_data=coordinator_dbus_connection
    )

def _handle_new_worker_socket_connection(socket_service, worker_socket_connection, source_object): #pylint: disable=invalid-name
    '''Handles the `Gio.SocketService`'s `incoming` signal'''
    server_address = source_object.payload
    if not server_address:
        raise ValueError('Invalid value for server_address')

    # Create coordinator D-Bus connection
    Gio.DBusConnection.new_for_address(
        address=server_address,
        flags=Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT,
        #| Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
        observer=None,
        cancellable=None,
        callback=_callback_new_coordinator_dbus_connection,
        user_data=worker_socket_connection
    )

    return False # To allow other handlers get called

def _setup_unix_socket_server(path, server_address):
    '''
    Initializes the D-Bus server listening on UNIX socket at `path` in filesystem.

    `path` is a path in the filesystem for the domain socket
    '''
    # NOTE: There does exist Gio.DBusServer (gio/gdbusserver.c in GLib), but it is synchronous only.
    # This implementation is async
    socket_service = Gio.SocketService.new()
    socket_service.connect('incoming', _handle_new_worker_socket_connection)
    success, _ = socket_service.add_address(
        address=Gio.UnixSocketAddress.new(path),
        type=Gio.SocketType.STREAM,
        protocol=Gio.SocketProtocol.DEFAULT,
        source_object=_PyGObject(server_address),
    )
    if not success:
        raise RuntimeError('Could not add address to Gio.SocketService')

def _setup_management_connection(server_address):
    '''Setup the D-Bus client connection for managing this application'''
    pass # TODO

def main(args_list):
    '''Entrypoint'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'listen_socket_path',
        help='The UNIX socket path to listen on'
    )
    parser.add_argument(
        '--server-address',
        required=False,
        default=os.environ['DBUS_SESSION_BUS_ADDRESS'],
        help='The D-Bus address to connect to. Defaults to $DBUS_SESSION_BUS_ADDRESS'
    )
    args = parser.parse_args(args_list)

    logger = _get_logger()

    if not Gio.dbus_is_supported_address(args.server_address):
        logger.error('Invalid server address: {}'.format(args.server_address))
        exit(1)

    _setup_unix_socket_server(args.listen_socket_path, args.server_address)

    _setup_management_connection(args.server_address)

    GLib.MainLoop().run()

if __name__ == '__main__':
    main(sys.argv[1:])
