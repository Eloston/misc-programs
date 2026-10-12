#!/usr/bin/env python3
"""Bind mount host paths into running Flatpak instances at the same paths."""

import argparse
import configparser
import contextlib
import ctypes
import os
import pwd
import stat
import subprocess
import sys
from collections.abc import Generator
from typing import NamedTuple, NoReturn, cast, final

# These syscall numbers are the same on all architectures except alpha.
SYS_OPEN_TREE = 428
SYS_MOVE_MOUNT = 429
SYS_MOUNT_SETATTR = 442

AT_FDCWD = -100
AT_EMPTY_PATH = 0x1000
AT_RECURSIVE = 0x8000
OPEN_TREE_CLONE = 1
MOVE_MOUNT_F_EMPTY_PATH = 0x4
MOUNT_ATTR_NOSUID = 0x2
MOUNT_ATTR_NODEV = 0x4
MS_SLAVE = 1 << 19

# Do not let a mount hide the runtime, the app or the Flatpak files in the sandbox.
ALLOWED_PREFIXES = ('/home/', '/mnt/', '/media/', '/run/media/', '/opt/', '/srv/')


@final
class MountAttr(ctypes.Structure):
    _fields_ = [
        ('attr_set', ctypes.c_uint64),
        ('attr_clr', ctypes.c_uint64),
        ('propagation', ctypes.c_uint64),
        ('userns_fd', ctypes.c_uint64),
    ]


class Args(argparse.Namespace):
    pid: int | None = None
    app_id: str = ''
    paths: list[str] = []


class Source(NamedTuple):
    target: str
    stat: os.stat_result
    readonly: bool


_libc = ctypes.CDLL(None, use_errno=True)


def _syscall(nr: int, *args: object) -> int:
    ret = cast(int, _libc.syscall(ctypes.c_long(nr), *args))
    if ret < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return ret


def die(msg: str) -> NoReturn:
    print('ERROR:', msg, file=sys.stderr)
    sys.exit(1)


@contextlib.contextmanager
def as_user(user: pwd.struct_passwd) -> Generator[None]:
    groups, egid = os.getgroups(), os.getegid()
    os.setgroups(os.getgrouplist(user.pw_name, user.pw_gid))
    os.setegid(user.pw_gid)
    os.seteuid(user.pw_uid)
    try:
        yield
    finally:
        os.seteuid(0)
        os.setegid(egid)
        os.setgroups(groups)


def open_source(path: str) -> tuple[int, Source]:
    fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
    target = os.readlink(f'/proc/self/fd/{fd}')
    return fd, Source(target, os.fstat(fd), bool(os.fstatvfs(fd).f_flag & os.ST_RDONLY))


def is_visible(path: str, source: Source) -> bool:
    st = os.stat(path, follow_symlinks=False)
    readonly = bool(os.statvfs(path).f_flag & os.ST_RDONLY)
    return (st.st_dev, st.st_ino) == (source.stat.st_dev, source.stat.st_ino) and (source.readonly or not readonly)


def clone_tree(src_fd: int) -> int:
    fd = _syscall(SYS_OPEN_TREE, src_fd, b'', OPEN_TREE_CLONE | os.O_CLOEXEC | AT_EMPTY_PATH | AT_RECURSIVE)
    # The clone joins the peer group of the source. Make it a slave, as bwrap does, so that mounts do not propagate back to the host.
    attr = MountAttr(attr_set=MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV, propagation=MS_SLAVE)
    _ = _syscall(SYS_MOUNT_SETATTR, fd, b'', AT_EMPTY_PATH | AT_RECURSIVE, ctypes.byref(attr), ctypes.c_size_t(ctypes.sizeof(attr)))
    return fd


def make_mountpoint(target: str, is_dir: bool) -> None:
    path = ''
    parts = target.split('/')[1:]
    for i, part in enumerate(parts):
        path += '/' + part
        try:
            if i == len(parts) - 1 and not is_dir:
                os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC, 0o644))
            else:
                os.mkdir(path, 0o755)
        except FileExistsError:
            pass


def attach(tree_fd: int, source: Source, user: pwd.struct_passwd) -> bool:
    target = source.target
    try:
        st = os.stat(target, follow_symlinks=False)
    except FileNotFoundError:
        # Root has no mapping in the user namespace that owns the sandbox tmpfs, so it gets EOVERFLOW there.
        with as_user(user):
            make_mountpoint(target, stat.S_ISDIR(source.stat.st_mode))
    else:
        if stat.S_ISLNK(st.st_mode):
            die(f'{target} is a symlink in the sandbox')
        if stat.S_ISDIR(st.st_mode) != stat.S_ISDIR(source.stat.st_mode):
            die(f'{target} has a different file type in the sandbox')
        if is_visible(target, source):
            return False
    _ = _syscall(SYS_MOVE_MOUNT, tree_fd, b'', AT_FDCWD, os.fsencode(target), MOVE_MOUNT_F_EMPTY_PATH)
    return True


def read_flatpak_info(path: str) -> configparser.ConfigParser:
    info = configparser.ConfigParser(interpolation=None, strict=False)
    _ = info.read(path)
    return info


def is_sub_sandbox(info: configparser.ConfigParser) -> bool:
    # Set by flatpak-spawn --sandbox, e.g. for glycin image loaders. These do not get the app permissions.
    return info.getboolean('Instance', 'sandbox', fallback=False)


def find_instances(app_id: str) -> list[int]:
    out = subprocess.run(['flatpak', 'ps', '--columns=child-pid,application'], check=True, stdout=subprocess.PIPE, text=True).stdout
    pids: list[int] = []
    for line in out.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0].isdigit() and fields[1] == app_id:
            if not is_sub_sandbox(read_flatpak_info(f'/proc/{fields[0]}/root/.flatpak-info')):
                pids.append(int(fields[0]))
    return pids


def visible_in(pid: int, source: Source) -> bool:
    # Only a hint to skip sudo: absolute symlinks under /proc/PID/root resolve on the host. The --pid mode does the real check.
    try:
        return is_visible(f'/proc/{pid}/root{source.target}', source)
    except OSError:
        return False


def inject_all(app_id: str, paths: list[str]) -> None:
    sources: list[Source] = []
    for path in paths:
        try:
            fd, source = open_source(path)
        except OSError as e:
            die(f'Cannot open {path}: {e.strerror}')
        os.close(fd)
        sources.append(source)
    for pid in find_instances(app_id):
        missing = [source.target for source in sources if not visible_in(pid, source)]
        if missing:
            ret = subprocess.run(['sudo', os.path.abspath(__file__), '--pid', str(pid), app_id, *missing]).returncode
            if ret != 0:
                sys.exit(ret)


def inject(pid: int, app_id: str, paths: list[str]) -> None:
    if 'SUDO_UID' not in os.environ:
        die('Run this with sudo')
    user = pwd.getpwuid(int(os.environ['SUDO_UID']))

    if os.stat(f'/proc/{pid}').st_uid != user.pw_uid:
        die(f'Process {pid} does not belong to {user.pw_name}')
    ns_fd = os.open(f'/proc/{pid}/ns/mnt', os.O_RDONLY | os.O_CLOEXEC)
    if os.fstat(ns_fd).st_ino == os.stat('/proc/self/ns/mnt').st_ino:
        die(f'Process {pid} is in the host mount namespace')

    mounts: list[tuple[int, Source]] = []
    for path in paths:
        # Open as the user, so that root cannot expose a path that the user cannot get to.
        with as_user(user):
            src_fd, source = open_source(path)
        if not source.target.startswith(ALLOWED_PREFIXES):
            die(f'{source.target} is not under one of {", ".join(ALLOWED_PREFIXES)}')
        mounts.append((clone_tree(src_fd), source))

    child = os.fork()
    if child == 0:
        try:
            os.setns(ns_fd, os.CLONE_NEWNS)
            info = read_flatpak_info('/.flatpak-info')
            if info.get('Application', 'name', fallback=None) != app_id:
                die(f'Process {pid} is not an instance of {app_id}')
            if is_sub_sandbox(info):
                die(f'Process {pid} is in a sub-sandbox of {app_id}')
            for tree_fd, source in mounts:
                if attach(tree_fd, source, user):
                    print(f'Mounted {source.target} in process {pid}')
        except SystemExit as e:
            os._exit(e.code if isinstance(e.code, int) else 1)
        except Exception as e:
            print('ERROR:', e, file=sys.stderr)
            os._exit(1)
        os._exit(0)
    _, status = os.waitpid(child, 0)
    sys.exit(os.waitstatus_to_exitcode(status))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        '--pid',
        type=int,
        help='mount into the instance of this child PID, as root. Without it, call sudo only for instances that cannot see a path.',
    )
    _ = parser.add_argument('app_id', metavar='APP_ID')
    _ = parser.add_argument('paths', metavar='PATH', nargs='+')
    args = parser.parse_args(namespace=Args())
    if args.pid is None:
        inject_all(args.app_id, args.paths)
    else:
        inject(args.pid, args.app_id, args.paths)


if __name__ == '__main__':
    main()
