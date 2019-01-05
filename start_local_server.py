#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Simple localhost HTTP server with webbrowser launching. It will serve the path of the file or symlink used to invoke this script as the root path; otherwise, it will use current working directory. Only one server will launch per path.

Useful for viewing HTML-based documentation stored on the filesystem.
'''

import argparse
import errno
import hashlib
import http.server
import os
import socket
import sys
import tempfile
import webbrowser
from pathlib import Path

_DEFAULT_PORT = 8080
_DEFAULT_BIND = 'localhost'

# Singleton code adapted from: https://raw.githubusercontent.com/pycontribs/tendo/master/tendo/singleton.py
# License: https://raw.githubusercontent.com/pycontribs/tendo/master/LICENSE
# ---BEGIN MODIFIED SINGLETON CODE---

class SingleInstanceException(BaseException):
    pass


class SingleContext:
    """Context Manager that can be entered only once per machine.

    If you want to prevent your script from running in parallel just enter SingleContext() context. If is there another instance already running it will throw a `SingleInstanceException`.

    >>> with SingleContext():
    ...     # Can only run once

    This option is very useful if you have scripts executed by crontab at small amounts of time.

    Remember that this works by creating a lock file with a filename based on the full path to the script file.

    Providing a flavor_id will augment the filename with the provided flavor_id, allowing you to create multiple singleton instances from the same file. This is particularly useful if you want specific functions to have their own singleton instances.
    """

    def __init__(self, flavor_id='unnamed-service', lockfile=None):
        self._initialized = False
        if lockfile:
            self.lockfile = lockfile
        else:
            hasher = hashlib.new('md5')
            hasher.update(str(Path().resolve()).encode('UTF-8'))
            basename =  '.lock-{}-{}'.format(flavor_id, hasher.hexdigest())
            self.lockfile = Path(tempfile.gettempdir(), basename)

    def __enter__(self):
        print('DEBUG: SingleInstance lockfile:', self.lockfile)
        if sys.platform == 'win32':
            try:
                # file already exists, we try to remove (in case previous
                # execution was interrupted)
                content = b''
                if self.lockfile.exists():
                    content = self.lockfile.read_bytes()
                    self.lockfile.unlink()
                self.fd = os.open(
                    str(self.lockfile), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                if content:
                    os.write(self.fd, content)
                    os.fsync(self.fd)
            except OSError as exc:
                if exc.errno == 13:
                    print('ERROR: Another instance is already running, quitting.')
                    raise SingleInstanceException()
                raise exc
        else:  # non Windows
            import fcntl
            if self.lockfile.exists():
                self.fp = self.lockfile.open('r+')
            else:
                self.fp = self.lockfile.open('w')
                self.fp.flush()
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                print('WARN: Another instance is already running, quitting.')
                raise SingleInstanceException()
        self._initialized = True
        return self

    def __exit__(self, *args):
        if not self._initialized:
            return
        self._initialized = False
        try:
            if sys.platform == 'win32':
                if hasattr(self, 'fd'):
                    os.close(self.fd)
                    self.lockfile.unlink()
            else:
                import fcntl
                fcntl.lockf(self.fp, fcntl.LOCK_UN)
                # os.close(self.fp)
                if self.lockfile.is_file():
                    self.lockfile.unlink()
        except BaseException as exc:
            print('WARN:', exc)
            sys.exit(-1)

    def write_to_lockfile(self, content):
        if not self._initialized:
            return
        if sys.platform == 'win32':
            os.write(self.fd, content.encode('UTF-8'))
            os.fsync(self.fd)
        else: # non Windows
            self.fp.write(content)
            self.fp.flush()

# ---END MODIFIED SINGLETON CODE---

def launch_server(single_context):
    # Code adapted from http.server.test() and https://stackoverflow.com/a/35387673
    http.server.SimpleHTTPRequestHandler.protocol_version = 'HTTP/1.0'
    current_port = _DEFAULT_PORT
    while True:
        try:
            httpd = http.server.HTTPServer((_DEFAULT_BIND, current_port), http.server.SimpleHTTPRequestHandler)
        except socket.error as exc:
            if exc.errno == errno.EADDRINUSE:
                print('WARN: Port', current_port, 'already in use; trying', current_port+1)
                current_port += 1
            else:
                raise exc
        else:
            socket_addr = httpd.socket.getsockname()
            print('Serving HTTP on', socket_addr[0], 'port', socket_addr[1], '...')
            web_address = 'http://{}:{}/'.format(*socket_addr)
            single_context.write_to_lockfile(web_address)
            # NOTE: There can be a timing issue where the browser fails to connect before the server is up
            webbrowser.open(web_address)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print('\nKeyboard interrupt received, exiting.')
                httpd.server_close()
            break

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-r', '--root', type=Path, help='Path to the root directory. If not specified, it will try to interpret the command used to launch this script as a path, and used the containing directory. Otherwise, the current working directory will be used.')
    args = parser.parse_args()
    if args.root:
        root_path = args.root
        if not args.root.is_dir():
            parser.error('{} is not a directory'.format(args.root))
    else:
        root_path = Path(__file__).parent
        if root_path.exists():
            root_path = root_path.resolve()
        else:
            root_path = Path().resolve()
    # Change directory to location of script (or the symlink to the script used)
    os.chdir(str(root_path))
    single_context = SingleContext(flavor_id='local-python-server')
    try:
        with single_context:
            launch_server(single_context)
    except SingleInstanceException:
        webbrowser.open(single_context.lockfile.read_text().strip())
        exit(1)

if __name__ == '__main__':
    main()
