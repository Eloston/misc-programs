#!/usr/bin/env python3

# Installer for deoplete.nvim and deoplete-jedi.
# Needs to be invoked in the same location as the respective git repos (either by copy or soft link)
# NOTE: deoplete-jedi should be reinstalled every time deoplete.nvim is installed due to the current configuration.

import argparse
import shutil
from pathlib import Path

NVIM_PLUGIN_FILES = [
    'autoload/deoplete',
    'autoload/health/deoplete.vim',
    'autoload/deoplete.vim',
    'doc/deoplete.txt',
    'plugin/deoplete.vim',
    'rplugin/python3/deoplete', # TODO: This breaks deoplete plugins like deoplete-jedi
]
JEDI_PLUGIN_FILES = [
    'rplugin/python3/deoplete/sources/deoplete_jedi',
    'rplugin/python3/deoplete/sources/deoplete_jedi.py',
]
NVIM_CONFIG = '~/.config/nvim/'

def _remove_empty_dirs(dir_path):
    while True:
        try:
            next(dir_path.iterdir())
            return
        except StopIteration:
            dir_path.rmdir()
        except FileNotFoundError:
            pass
        dir_path = dir_path.parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--delete', action='store_true', help='Deletes the plugin without copying')
    parser.add_argument('type', choices=['nvim', 'jedi'])
    args = parser.parse_args()
    cwd = Path(__file__).parent.resolve()
    nvim_config = Path(NVIM_CONFIG).expanduser().resolve()
    if args.type == 'nvim':
        plugin_files = NVIM_PLUGIN_FILES
    elif args.type == 'jedi':
        plugin_files = JEDI_PLUGIN_FILES
    else:
        raise NotImplementedError()
    for plugin_file in map(lambda x: Path(x), plugin_files):
        if not (cwd / plugin_file).exists():
            print('ERROR: Git repo does not have file: %s' % plugin_file)
            exit(1)
    for plugin_path in plugin_files:
        if (nvim_config / plugin_path).is_dir():
            shutil.rmtree(str(nvim_config / plugin_path))
            _remove_empty_dirs(nvim_config / plugin_path)
        elif (nvim_config / plugin_path).is_file():
            (nvim_config / plugin_path).unlink()
            _remove_empty_dirs((nvim_config / plugin_path).parent)
        if not args.delete:
            if (cwd / plugin_path).is_dir():
                copyfunc = shutil.copytree
            else:
                copyfunc = shutil.copy2
            (nvim_config / plugin_path).parent.mkdir(parents=True, exist_ok=True)
            copyfunc(str(cwd / plugin_path), str(nvim_config / plugin_path))

if __name__ == '__main__':
    main()
