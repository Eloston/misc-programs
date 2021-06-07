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

# Globals for image scanning algorithms

# Lowe ratio, essentially used to determine if two keypoints match
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
FLANN_KNN_MATCHES = 2 # For _FLANN.knnMatch
FLANN_INDEX_KDTREE = 0
flann_index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
flann_search_params = dict(checks=50) # or pass empty dictionary
_FLANN = cv2.FlannBasedMatcher(flann_index_params, flann_search_params)

# Globals for a worker in the process pool

# Loaded reference descriptor
_REFERENCE_DES: np.ndarray = None
# Maximum length of the larger dimension when downscaling images
_MAX_LENGTH: int = None

# Base code for image searching


class _InvalidComputation(Exception):
    # Thrown on invalid computation for an image
    pass


def downscale_img(img, max_length):
    height, width = img.shape[:2]
    if height < max_length and width < max_length:
        # Image is already smaller than we need
        return img
    if height > width:
        new_dim = (int(width / float(height) * max_length), max_length)
    else:
        new_dim = (max_length, int(height / float(width) * max_length))
    return cv2.resize(img, new_dim, interpolation=cv2.INTER_AREA)


def compute_descriptor(img_path, max_length):
    img = cv2.imread(str(img_path), 0)
    if img is None:
        raise _InvalidComputation('Not a valid image')

    img = downscale_img(img, max_length)

    #kp, des = _ORB.detectAndCompute(img, None)
    kp, des = _SIFT.detectAndCompute(img, None)
    #kp, des = _SURF.detectAndCompute(img, None)
    #print(img_path, des.dtype, des.shape)

    if not kp:
        raise _InvalidComputation('Could not find any keypoints')
    if des is None:
        raise _InvalidComputation('descriptor is None')

    return des


def get_good_matches(des1, des2):
    # Because of https://github.com/opencv/opencv/issues/10548
    if des2.shape[0] < FLANN_KNN_MATCHES:
        raise _InvalidComputation('train descriptor has too few entries')

    matches = _FLANN.knnMatch(des1, des2, k=FLANN_KNN_MATCHES)
    if not matches:
        raise _InvalidComputation('No matches found')
    if len(matches[0]) != 2:
        raise _InvalidComputation(f'Matches columns must have 2 entries, got {len(matches[0])}')

    # ratio test as per Lowe's paper
    #good = list()
    ngood = 0
    for m, n in matches:
        if m.distance < LOWE_RATIO * n.distance:
            #good.append(m)
            ngood += 1

    return ngood


# Process pool worker functions


def init_worker(img_path, max_length):
    global _REFERENCE_DES, _MAX_LENGTH
    assert _REFERENCE_DES is None
    assert _MAX_LENGTH is None
    _REFERENCE_DES = compute_descriptor(img_path, max_length)
    _MAX_LENGTH = max_length


def compute_ngood(img_path):
    assert _REFERENCE_DES is not None
    if not img_path.is_file():
        print('\nSkipping non-file', img_path)
        return
    if img_path.is_symlink():
        print('\nSkipping symlink', img_path)
        return

    try:
        print(f'{ANSI_CL}Processing', img_path, end='\r')
        try:
            scan_des = compute_descriptor(img_path, _MAX_LENGTH)
        except _InvalidComputation as exc:
            print(f'{ANSI_CL}Skipping img with compute_descriptor error "{str(exc)}":', img_path)
            return -1, img_path
        try:
            ngood = get_good_matches(_REFERENCE_DES, scan_des)
        except _InvalidComputation as exc:
            print(f'{ANSI_CL}Skipping img with get_good_matches error "{str(exc)}":', img_path)
            return -1, img_path
    except BaseException as exc:
        print(f'{ANSI_CL}Threw exception on {img_path}: {exc}')
        return -1, img_path
    return ngood, img_path


# Main process functions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--workers',
        type=int,
        help=
        f'Number of worker subprocesses to launch. If not specified, defaults to the number of CPU threads (found: {os.cpu_count()}).'
    )
    parser.add_argument('--chunksize',
                        type=int,
                        default=2,
                        help='Chunksize for multiprocessing map operation. Default: %(default)s')
    parser.add_argument('--resize', type=int, default=640, help='Before computing descriptors, specifies the maximum length of the larger dimension when downscaling images. Default: %(default)s')
    parser.add_argument('query_img',
                              type=Path,
                              help='Path to the query image')
    parser.add_argument('img_root', type=Path, help='Path to the directory containing images to search through')
    args = parser.parse_args()

    print(f'{ANSI_CL}Initializing workers...', end='\r')
    with multiprocessing.Pool(args.workers, init_worker, [args.query_img, args.resize]) as pool:
        all_matches = list(
            pool.imap_unordered(compute_ngood, args.img_root.rglob('*'), chunksize=args.chunksize))
    all_matches.sort()
    print(f'{ANSI_CL}Top {NTOP} matches:')
    for ngood, scan_path in all_matches[-NTOP:]:
        print(scan_path, f'({ngood})')


if __name__ == '__main__':
    main()
