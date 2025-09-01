#!/usr/bin/env python3

import argparse
import errno
import shutil
import subprocess
from collections.abc import Iterable, Set
from pathlib import Path

_REPO_ROOT = Path('/var/local/cache/apt/repo')
_PACKAGE_INDEX_NAME = 'Packages'
_RELEASE_INDEX_NAME = 'Release'
_TO_KEEP = (_PACKAGE_INDEX_NAME, _RELEASE_INDEX_NAME)


def parse_package_index_filenames(path: Path) -> Iterable[str]:
    return map(
        lambda x: x[len('Filename: '):],
        filter(
            lambda x: x.startswith('Filename: '),
            path.read_text().splitlines()
        )
    )


def parse_package_index_paths(root: Path) -> Iterable[Path]:
    return map(
        lambda x: root / x,
        parse_package_index_filenames(root / _PACKAGE_INDEX_NAME)
    )


def add_packages(paths: Iterable[Path], root: Path, replace: bool = False) -> Set[Path]:
    added: set[Path] = set()
    for path in paths:
        resolved_path = path.resolve()
        assert resolved_path.exists()
        if resolved_path.is_dir():
            added.update(add_packages(path.rglob('*.deb'), root, replace))
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


def generate_package_index(root: Path, multiversion=False) -> None:
    # args = ['apt-ftparchive', 'packages', '.']
    args = ['dpkg-scanpackages', '-h', 'sha256']
    if multiversion:
        args.append('-m')
    args.append('.')
    result = subprocess.run(args, capture_output=True,
                            text=True, check=True, cwd=str(root))
    (root / _PACKAGE_INDEX_NAME).write_text(result.stdout)


def generate_release_index(root: Path) -> None:
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


def prune_repo(root: Path) -> Set[Path]:
    to_keep: set[Path] = set(parse_package_index_paths(root))
    to_keep.update(root / x for x in _TO_KEEP)
    pruned = set()
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
    added = add_packages(args.paths, args.root, args.replace)
    generate_package_index(args.root)
    generate_release_index(args.root)
    pruned = prune_repo(args.root)
    added_count = len(added - pruned)
    pruned_count = len(pruned - added)
    print('Added', added_count, 'and pruned', pruned_count, 'file(s)')


def prune_handler(args: argparse.Namespace) -> None:
    pruned = prune_repo(args.root)
    print('Pruned', len(pruned), 'file(s)')


def scan_handler(args: argparse.Namespace) -> None:
    generate_package_index(args.root)
    generate_release_index(args.root)


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
