#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import re
import shlex

_STR_TRANS_DICT = {x: None for x in "&[].,()'-#!"}
_STR_TRANS_DICT.update({
    ' ': '_',
    'ü': 'u',
})
STR_TRANS = str.maketrans(_STR_TRANS_DICT)

def norm_prefix(orig_path):
    new_stem = orig_path.stem.lower().replace(' - ', '_')
    new_stem = new_stem.translate(STR_TRANS)
    new_stem = new_stem.strip('_')
    if not re.fullmatch(r'[a-zA-Z0-9_]+', new_stem):
        print('ERROR: Failed to normalize:', new_stem)
        exit(1)
    return orig_path.with_name(new_stem)

if __name__ == '__main__':
    TMPL = "ffmpeg -i {orig_path} -vn -c:a libvorbis -q:a 5 {new_prefix}.ogg"
    normed_prefix_set = set()
    for path in Path().rglob('*.flac'):
        normed_prefix = norm_prefix(path)
        if normed_prefix in normed_prefix_set:
            print('ERROR: Prefix already exists:', normed_prefix)
            exit(1)
        else:
            normed_prefix_set.add(normed_prefix)
        print(TMPL.format(orig_path=shlex.quote(str(path)), new_prefix=shlex.quote(str(normed_prefix))))
