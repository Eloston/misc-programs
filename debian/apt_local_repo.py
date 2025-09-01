#!/usr/bin/env python3

import argparse
import errno
import shutil
import subprocess
from collections.abc import Iterable, Set
from pathlib import Path
from typing import NamedTuple

# Package python3-apt
import apt_pkg

def _ensure_apt_pkg_initialized() -> None:
    if hasattr(apt_pkg, '_initialized') and apt_pkg._initialized:
        return
    apt_pkg.init()
    apt_pkg._initialized = True


_REPO_ROOT = Path('/var/local/cache/apt/repo')
_PACKAGE_INDEX_NAME = 'Packages'
_RELEASE_INDEX_NAME = 'Release'
_TO_KEEP = (_PACKAGE_INDEX_NAME, _RELEASE_INDEX_NAME)

class _Package(NamedTuple):
    name: str
    version: str
    filename: Path

def _parse_package_index(root: Path) -> Iterable[_Package]:
    pkg = ver = fn = None
    with (root / _PACKAGE_INDEX_NAME).open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                # end of stanza
                if pkg and ver and fn:
                    yield _Package(pkg, ver, fn)
                # reset for next stanza
                pkg = ver = fn = None
                continue

            if line.startswith("Package:"):
                pkg = line.split(":", 1)[1].strip()
            elif line.startswith("Version:"):
                ver = line.split(":", 1)[1].strip()
            elif line.startswith("Filename:"):
                fn = Path(line.split(":", 1)[1].strip())

        # handle last stanza if file doesn't end with a blank line
        if pkg and ver and fn:
            yield _Package(pkg, ver, fn)



def _parse_package_index_paths(root: Path) -> Iterable[Path]:
    return map(
        lambda x: root / x.filename,
        _parse_package_index(root)
    )


def _add_packages(paths: Iterable[Path], root: Path, replace: bool = False) -> Set[Path]:
    added: set[Path] = set()
    for path in paths:
        resolved_path = path.resolve()
        assert resolved_path.exists()
        if resolved_path.is_dir():
            added.update(_add_packages(path.rglob('*.deb'), root, replace))
            continue
        if path.suffix != '.deb':
            continue
        if (root / path).exists():
            if not replace:
                raise FileExistsError(str(root / path))
            (root / path).unlink()
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        try:
            (root / path).hardlink_to(resolved_path)
        except OSError as exc:
            # Cross-link device error
            if exc.errno == errno.EXDEV:
                shutil.copy2(resolved_path, root / path)
            else:
                raise exc
        added.add(path)
    return added


def _generate_package_index(root: Path, multiversion=False) -> None:
    # args = ['apt-ftparchive', 'packages', '.']
    args = ['dpkg-scanpackages', '-h', 'sha256']
    if multiversion:
        args.append('-m')
    args.append('.')
    result = subprocess.run(args, capture_output=True,
                            text=True, check=True, cwd=str(root))
    (root / _PACKAGE_INDEX_NAME).write_text(result.stdout)


def _generate_release_index(root: Path) -> None:
    args = [
        'apt-ftparchive',
        '-o', 'APT::FTPArchive::Release::Origin=apt-local-repo',
        '-o', 'APT::FTPArchive::Release::Description=Local repository created by apt-local-repo',
        'release',
        '.'
    ]
    result = subprocess.run(args, capture_output=True,
                            text=True, check=True, cwd=str(root))
    (root / _RELEASE_INDEX_NAME).write_text(result.stdout)

def _remove_obsolete_packages(root: Path) -> Set[Path]:
    _ensure_apt_pkg_initialized()
    cache = apt_pkg.Cache()

    def cmp(a, b):
        vc = apt_pkg.version_compare(a, b)
        return (vc > 0) - (vc < 0)

    obsolete_filenames: Set[Path] = set()

    packages_index = _parse_package_index(root)
    for stanza in packages_index:
        pkg = stanza.name
        ver = stanza.version
        fn = stanza.filename
        cache_latest = None
        if pkg in cache and cache[pkg].version_list:
            cache_latest = cache[pkg].version_list[0].ver_str
            if cmp(ver, cache_latest) < 0:
                try:
                    (root / fn).unlink()
                    obsolete_filenames.add(fn)
                except FileNotFoundError:
                    print(f'Warning: {fn} listed in {_PACKAGE_INDEX_NAME} but not found')

    return obsolete_filenames

def _remove_unreferenced_filenames(root: Path) -> Set[Path]:
    to_keep: set[Path] = set(_parse_package_index_paths(root))
    to_keep.update(root / x for x in _TO_KEEP)
    pruned: Set[Path] = set()
    path_stack = [root]
    while path_stack:
        path_parent = path_stack.pop()
        for path in tuple(path_parent.iterdir()):
            if path.is_dir():
                path_stack.append(path)
                continue
            if path in to_keep:
                continue
            pruned.add(path.relative_to(root))
            path.unlink()
        if not sum(1 for _ in path_parent.iterdir()):
            path_parent.rmdir()
    return pruned


def check_common_args(args: argparse.Namespace) -> None:
    assert args.root.resolve().is_dir()


def add_handler(args: argparse.Namespace) -> None:
    added = _add_packages(args.paths, args.root, args.replace)
    _generate_package_index(args.root)
    _generate_release_index(args.root)
    unreferenced = _remove_unreferenced_filenames(args.root)
    added_count = len(added - unreferenced)
    unreferenced_count = len(unreferenced - added)
    print(f'Added {added_count} and removed {unreferenced_count} file(s)')


def prune_handler(args: argparse.Namespace) -> None:
    unreferenced =_remove_unreferenced_filenames(args.root)
    obsolete = _remove_obsolete_packages(args.root)
    if obsolete:
        _generate_package_index(args.root)
        _generate_release_index(args.root)
    print(f'Removed {len(unreferenced)} unreferenced and {len(obsolete)} obsolete file(s)')


def scan_handler(args: argparse.Namespace) -> None:
    _generate_package_index(args.root)
    _generate_release_index(args.root)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=_REPO_ROOT)
    subparser = parser.add_subparsers()

    add_parser = subparser.add_parser('add')
    add_parser.add_argument('--replace', action='store_true')
    add_parser.add_argument('paths', type=Path, nargs='+')
    add_parser.set_defaults(handler=add_handler)

    prune_parser = subparser.add_parser('prune')
    prune_parser.set_defaults(handler=prune_handler)

    scan_parser = subparser.add_parser('scan')
    scan_parser.set_defaults(handler=scan_handler)

    args = parser.parse_args()
    if 'handler' not in args:
        parser.print_usage()
        return
    check_common_args(args)
    args.handler(args)


if __name__ == '__main__':
    main()
