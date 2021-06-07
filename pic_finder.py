#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import argparse
import multiprocessing
import numpy as np
import os

import cv2

"""
Find similar image by comparing image keypoints

The processing pipeline and choice of algorithms are not my own.
"""

# Globals for user interface

# Number of top results to print to the user
NTOP = 50
# ANSI escape code to clear line
ANSI_CL = '\033[K'
# Descriptors are np.ndarray objects serialized via np.save
_DESCRIPTOR_FILE_SUFFIX = '.npy'

# Globals for image scanning algorithms

LOWE_RATIO = 0.7
# Requires OPENCV_ENABLE_NONFREE=ON when compiling OpenCV
_SIFT = cv2.SIFT_create()
# ORB detector does not perform well, but it is under a free license
#_ORB = cv2.ORB_create()
# Brute Force matcher has limited number of descriptors:
# cv2.error: OpenCV(4.5.0) ../modules/features2d/src/matchers.cpp:860: error: (-215:Assertion failed) trainDescCollection[iIdx].rows < IMGIDX_ONE in function 'knnMatchImpl'
# So we hardcode limit here:
#BF_IMGIDX_SHIFT = 18
#BF_IMGIDX_ONE = 1 << BF_IMGIDX_SHIFT
#_BF = cv2.BFMatcher()
FLANN_KNN_MATCHES = 2  # For _FLANN.knnMatch
FLANN_INDEX_KDTREE = 0
flann_index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
flann_search_params = dict(checks=50)  # or pass empty dictionary
_FLANN = cv2.FlannBasedMatcher(flann_index_params, flann_search_params)

# Globals for a worker in the build command process pool

# Source image root directory
_IMG_ROOT = None
# Descriptor database root directory
_DB_ROOT = None

# Globals for a worker in the query command process pool

# Loaded reference descriptor
_REFERENCE_DES: np.ndarray = None

# Base code for image searching


class _InvalidComputation(Exception):
    # Thrown on invalid computation for an image
    pass


def compute_descriptor(img_path):
    img = cv2.imread(str(img_path), 0)
    if img is None:
        raise _InvalidComputation('Not a valid image')

    #kp, des = _ORB.detectAndCompute(img, None)
    kp, des = _SIFT.detectAndCompute(img, None)
    #kp, des = _SURF.detectAndCompute(img, None)
    #print(img_path, des.dtype, des.shape)

    if not kp:
        raise _InvalidComputation('Could not find any keypoints')
    if des is None:
        raise _InvalidComputation('descriptor is None')

    return des


def load_descriptor(des_path):
    return np.load(des_path, allow_pickle=False)


def save_descriptor(img_des, des_path):
    np.save(des_path, img_des, allow_pickle=False)


def get_good_matches(des1, des2):
    # Because of https://github.com/opencv/opencv/issues/10548
    if des2.shape[0] < FLANN_KNN_MATCHES:
        raise _InvalidComputation('train descriptor has too few entries')

    matches = _FLANN.knnMatch(des1, des2, k=FLANN_KNN_MATCHES)
    if not matches:
        raise _InvalidComputation('No matches found')
    if len(matches[0]) != 2:
        raise _InvalidComputation(
            f'Matches columns must have 2 entries, got {len(matches[0])}')

    # ratio test as per Lowe's paper
    #good = list()
    ngood = 0
    for m, n in matches:
        if m.distance < LOWE_RATIO * n.distance:
            #good.append(m)
            ngood += 1

    return ngood


# Process pool worker functions


def init_build_worker(source_imgs, db_path):
    global _IMG_ROOT, _DB_ROOT
    _IMG_ROOT = source_imgs
    _DB_ROOT = db_path


def db_add(img_path):
    assert _IMG_ROOT is not None
    assert _DB_ROOT is not None
    if not img_path.is_file():
        print('\nSkipping non-file', img_path)
        return
    if img_path.is_symlink():
        print('\nSkipping symlink', img_path)
        return

    try:
        print(f'{ANSI_CL}Processing', img_path, end='\r')
        try:
            img_des = compute_descriptor(img_path)
        except _InvalidComputation as exc:
            print(
                f'{ANSI_CL}Skipping img with compute_descriptor error "{str(exc)}":',
                img_path)
            return
        # des_path does not contain .npy suffix because that will be added by np.save
        des_path = _DB_ROOT / img_path.relative_to(_IMG_ROOT)
        des_path.parent.mkdir(parents=True, exist_ok=True)
        save_descriptor(img_des, des_path)
    except BaseException as exc:
        print(f'{ANSI_CL}Threw exception on {img_path}: {exc}')


def init_query_worker(des_path):
    global _REFERENCE_DES
    assert _REFERENCE_DES is None
    _REFERENCE_DES = load_descriptor(des_path)


def compute_ngood(des_path):
    assert _REFERENCE_DES is not None
    try:
        print(f'{ANSI_CL}Processing', des_path, end='\r')
        scan_des = load_descriptor(des_path)
        try:
            ngood = get_good_matches(_REFERENCE_DES, scan_des)
        except _InvalidComputation as exc:
            print(
                f'{ANSI_CL}Skipping img with get_good_matches error "{str(exc)}":',
                des_path)
            return -1, des_path
    except BaseException as exc:
        print(f'{ANSI_CL}Threw exception on {des_path}: {exc}')
        return -1, des_path
    return ngood, des_path


# Main process functions


def build_cmd(args, parser_error):
    # Sanity check arguments
    if not args.db.is_dir():
        parser.error('Database path is not an existing directory: ' +
                     str(args.db))
    if not args.source_imgs.is_dir():
        parser_error('Source images path is not an existing directory: ' +
                     str(args.source_imgs))

    with multiprocessing.Pool(args.workers, init_build_worker,
                              [args.source_imgs, args.db]) as pool:
        for _ in pool.imap_unordered(db_add,
                                     args.source_imgs.rglob('*'),
                                     chunksize=args.chunksize):
            pass
    # Add newline because our cursor is at the beginning of a line with text
    print()


def prepare_cmd(args, parser_error):
    # Sanity check arguments
    if not args.query_img.is_file():
        parser_error('Input image is not an existing file: ' +
                     str(args.query_img))

    reference_des = compute_descriptor(args.query_img)
    save_descriptor(reference_des, args.query_des)


def query_cmd(args, parser_error):
    # Sanity check arguments
    if not args.db.is_dir():
        parser.error('Database path is not an existing directory: ' +
                     str(args.db))
    if not args.query_des.is_file():
        parser_error('Query descriptor is not an existing file: ' +
                     str(args.query_des))

    with multiprocessing.Pool(args.workers, init_query_worker,
                              [args.query_des]) as pool:
        all_matches = list(
            pool.imap_unordered(compute_ngood,
                                args.db.rglob('*'),
                                chunksize=args.chunksize))
    all_matches.sort()
    print(f'{ANSI_CL}Top {NTOP} matches:')
    for ngood, scan_path in all_matches[-NTOP:]:
        print(scan_path, f'({ngood})')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--workers',
        type=int,
        help=
        f'Number of worker subprocesses to launch. If not specified, defaults to the number of CPU threads (found: {os.cpu_count()}).'
    )
    parser.add_argument(
        '--chunksize',
        type=int,
        default=2,
        help='Chunksize for multiprocessing map operation. Default: %(default)s'
    )
    subparsers = parser.add_subparsers()
    parser_build = subparsers.add_parser(
        'build', help='Build the descriptor database, updating as necessary')
    parser_build.add_argument(
        '--db',
        required=True,
        type=Path,
        help='Path to the root directory of the database')
    parser_build.add_argument('source_imgs',
                              type=Path,
                              help='Root directory for image files to scan')
    parser_build.set_defaults(func=build_cmd)
    parser_prepare = subparsers.add_parser(
        'prepare',
        help='Prepare for querying by generating a query descriptor file')
    parser_prepare.add_argument('query_img',
                                type=Path,
                                help='Path to the query image to read')
    parser_prepare.add_argument(
        'query_des',
        type=Path,
        help=
        f'The query descriptor filepath to write. If it does not end in {_DESCRIPTOR_FILE_SUFFIX}, it will be appended automatically'
    )
    parser_prepare.set_defaults(func=prepare_cmd)
    parser_query = subparsers.add_parser('query',
                                         help='Query the descriptor database')
    parser_query.add_argument(
        '--db',
        required=True,
        type=Path,
        help='Path to the root directory of the database')
    parser_query.add_argument(
        'query_des',
        type=Path,
        help='Path to the query descriptor file to scan the database against')
    parser_query.set_defaults(func=query_cmd)
    args = parser.parse_args()

    args.func(args, parser.error)


if __name__ == '__main__':
    main()
