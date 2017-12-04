#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Splitter for YouTube song mixes (simple compilations) via timestamps in the description
Currently tested exclusively on The Soul of Wind YouTube channel
Requires youtube-dl
Requires SONG_OUTPUT environment variable to be set to the output directory for songs
Optional variables: ALL_PROXY, YOUTUBE_DL_CACHE, YOUTUBE_DL_DOWNLOADS
'''

import sys
import os
import os.path
import subprocess
import pathlib
import importlib
import logging

# Program executation setup

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    def _fix_relative_import():
        """Allow relative imports to work from anywhere"""
        parent_path = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.dirname(parent_path))
        global __package__ #pylint: disable=global-variable-undefined
        __package__ = os.path.basename(parent_path) #pylint: disable=redefined-builtin
        __import__(__package__)
        sys.path.pop(0)
    _fix_relative_import()

from . import ffmpy # pylint: disable=wrong-import-position

def _import_single_module(module_path, module_name):
    '''Imports and returns a single module by path relative to the script directory'''
    current_dir = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    module_dir = os.path.join(current_dir, module_path)
    sys.path.insert(0, module_dir)
    module = importlib.import_module(module_name)
    sys.path.pop(0)
    return module

youtube_dl = _import_single_module('youtube-dl', 'youtube_dl') # pylint: disable=invalid-name
fuzzywuzzy = _import_single_module('fuzzywuzzy', 'fuzzywuzzy') # pylint: disable=invalid-name

def _get_logger(name=None, level=logging.DEBUG):
    '''Gets the named logger'''

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.hasHandlers():
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

def _normalize_name(raw_name):
    '''
    Returns a normalized version of the name
    '''
    raise NotImplementedError()

def _get_youtube_id(url):
    '''
    Parses the URL and returns the YouTube video ID

    Raises ValueError when the video ID cannot be found or the ID is of the wrong format.
    '''
    raise NotImplementedError()

class Mix:
    '''
    Represents a YouTube song compilation video
    '''
    
    @staticmethod
    def _info_to_song_generator(info):
        '''
        Parses youtube-dl info dictionary for a compilation and yields Song instances
        '''
        raise NotImplementedError()

    def __init__(self, youtubedl_info):
        '''
        Initializes a new Mix
        '''
        raise NotImplementedError()

    def __hash__(self):
        '''
        Returns hash of the YouTube video ID
        '''
        raise NotImplementedError()

    def __eq__(self, other):
        '''
        Returns True if the other Mix's video ID is the same.
        '''
        # Check if Mix is same object. If not, check if video ID attribute exists, and if video ID is the same
        raise NotImplementedError()

    def __iter__(self):
        '''
        Returns an iterator over the Mix's songs
        '''
        raise NotImplementedError()

    def __len__(self):
        '''
        Returns number of songs in Mix
        '''
        raise NotImplementedError()

    def __bool__(self):
        '''
        Returns a boolean indicating if the Mix contains at least one song
        '''
        raise NotImplementedError()

class Song:
    '''
    Represents a song
    '''

    @classmethod
    def from_file(cls, path):
        '''
        Returns a Song from a file located by a pathlib.Path-like object
        '''
        # set constructor argument downloaded = True
        raise NotImplementedError()

    def __init__(self, duration, downloaded=False, start_time=None, end_time=None, normalized_name=None, raw_name=None, file_extension='ogg', compilation=None):
        '''
        Constructor of a Song. To be invoked by Song.from_file() or by Mix
        '''
        raise NotImplementedError()

    def __eq__(self, other):
        '''
        Returns a boolean indicating if the songs are similar enough.
        '''
        # Check with normalized name, duration, and possibly other parameters like the associated Mix.
        raise NotImplementedError()

class SongCollector:
    '''
    Manages a collection of songs
    '''

    def __init__(self):
        self._known_songs = dict() # normalized_name -> Song
        self._new_songs = dict() # Mix -> Song

    def add_mixes(self, mix_iterable):
        '''
        Add new songs from Mix into the collector
        '''
        raise NotImplementedError()

    def add_directory(self, path):
        '''
        Add known songs named by normalized name from directory located by path into the collector
        '''
        raise NotImplementedError()

    def new_mixes_iterator():
        '''
        Returns new iterator of Mix for new mixes
        '''
        raise NotImplementedError()

    def new_songs_iterator(mix):
        '''
        Returns new iterator of Song for new songs in the given mix
        '''
        raise NotImplementedError()

def _main(*args):
    # TODO: Use argparse
    _get_logger()

    mixes = set()
    # TODO: Refactor old code below
    # Constants
    OUTPUT_DIR = os.environ['SONG_OUTPUT'] # TODO: Change to argparse optional argument
    PROXY = os.environ.get('ALL_PROXY', None)
    YOUTUBE_DL_CACHE = os.environ.get('YOUTUBE_DL_CACHE', '/tmp/youtube_dl_cache')
    YOUTUBE_DL_DOWNLOADS = os.environ.get('YOUTUBE_DL_DOWNLOADS', '/tmp/youtube_dl_downloads')
    # List of current songs
    _OUTPUT_FILES = [_format_name(x.stem) for x in pathlib.Path(OUTPUT_DIR).iterdir()]

if __name__ == '__main__':
    _main(*sys.argv[1:])
