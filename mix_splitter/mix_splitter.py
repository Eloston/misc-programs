#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Splitter for YouTube song mixes via timestamps in the description
# Currently tested exclusively on The Soul of Wind YouTube channel
# Requires youtube-dl
# Requires SONG_OUTPUT environment variable to be set to the output directory for songs
# Optional variables: ALL_PROXY, YOUTUBE_DL_CACHE, YOUTUBE_DL_DOWNLOADS

import sys
import os.path
import subprocess
import os
import pathlib
import importlib
import logging

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

from . import ffmpy

def _import_single_module(module_path, module_name):
    '''Imports and returns a single module by path relative to the script directory'''
    current_dir = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    module_dir = os.path.join(current_dir, module_path)
    sys.path.insert(0, module_dir)
    module = importlib.import_module(module_name)
    sys.path.pop(0)
    return module

youtube_dl = _import_single_module('youtube-dl', 'youtube_dl')

# Constants
OUTPUT_DIR = os.environ['SONG_OUTPUT']
PROXY = os.environ.get('ALL_PROXY', None)
YOUTUBE_DL_CACHE = os.environ.get('YOUTUBE_DL_CACHE', '/tmp/youtube_dl_cache')
YOUTUBE_DL_DOWNLOADS = os.environ.get('YOUTUBE_DL_DOWNLOADS', '/tmp/youtube_dl_downloads')

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

def _format_name(raw_name):
    '''Returns a file-friendly name from raw_name'''
    # NOTE: Please don't do one-liners like this in the future.
    return '_'.join([
        x for x in [
            ''.join([
                z for z in y if z.isalnum()
            ]) for y in raw_name.split()
        ] if len(x) > 0
    ]).lower()

# List of current songs
_OUTPUT_FILES = [_format_name(x.stem) for x in pathlib.Path(OUTPUT_DIR).iterdir()]

class Action:
    '''Enum of command-line actions'''
    SPLIT = 'split'
    CHECK_NEW = 'check_new'
    FILE_CHECK_NEW = 'file_check_new'

def _is_name_existing(new_name, name_collection=_OUTPUT_FILES):
    '''Somewhat intelligently checks if a song already exists'''
    # TODO: Perhaps compare song tuples. If names are prefixes of one another, then check if duration differs by more than 3 seconds to determine if different song
    new_name = _format_name(new_name).replace('_', '')
    for existing_name in name_collection:
        existing_name = existing_name.replace('_', '')
        if existing_name.startswith(new_name) or new_name.startswith(existing_name):
            return True
    return False

def _get_output_path(name, suffix='ogg'):
    '''Return the output filepath from the given name'''
    return os.path.join(OUTPUT_DIR, _format_name(name) + '.' + suffix)

def _parse_songlist(raw_data):
    '''
    Parses the songlist from the string raw_data of the format:
    {start_timestamp} {name_of_song}
    where each line is one song, and the list is ordered in ascending time.

    Returns a list of tuples with the start time, end time, and raw name
    '''
    data = raw_data.splitlines()
    data[:] = [x for x in data if len(x) > 0]
    songs = list()
    pending_entry = None
    for raw_entry in data:
        entry = raw_entry.split(maxsplit=1)
        if not len(entry) == 2:
            raise Exception('Invalid entry: {}'.format(raw_entry))
        start_time, raw_name = entry
        if not start_time.replace(':', '').encode('UTF-8').isdigit():
            raise Exception('Invalid start time for entry "{}"'.format(raw_entry))
        if not pending_entry is None:
            songs.append((
                pending_entry[0],
                start_time,
                pending_entry[1]
            ))
        pending_entry = (start_time, raw_name)
    songs.append((
        pending_entry[0],
        None,
        pending_entry[1]
    ))
    return songs

def _split_file(compilation_path, compilation_title, compilation_author, songs):
    '''Split a song compilation file by the processed songs list'''
    for start_time, end_time, raw_name in songs:
        output_path = _get_output_path(raw_name)
        if not _is_name_existing(raw_name):
            output_args = [
                '-metadata:s:a', 'comment=From the compilation "{}"'.format(compilation_title),
                '-metadata:s:a', 'album={}'.format(compilation_author),
                '-metadata:s:a', 'album_artist={}'.format(compilation_author),
                '-metadata:s:a', 'artist={}'.format(compilation_author),
                '-metadata:s:a', 'title={}'.format(raw_name),
                '-acodec', 'copy',
                '-ss', start_time
            ]
            if end_time:
                output_args.extend(('-to', end_time))
            ff = ffmpy.FFmpeg(
                #inputs={compilation_path: ['-ss', start_time]},
                inputs={compilation_path: None},
                outputs={
                    output_path: output_args
                }
            )
            logging.info('Parsing: "{}"'.format(raw_name))
            ff.run(stderr=subprocess.DEVNULL)

def _process_file(action, compilation_title, compilation_author, compilation_path):
    '''Processes a file in the filesystem'''
    if action == Action.FILE_CHECK_NEW:
        with open(compilation_path) as input_file:
            songs = _parse_songlist(input_file.read())
    else:
        '''
        ffprobe = ffmpy.FFprobe(inputs={
                compilation_path: ['-show_entries', 'stream_tags=comment', '-print_format', 'default=nokey=1:noprint_wrappers=1']
            }
        )
        probe_stdout, probe_stderr = ffprobe.run(stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)
        songs = _parse_songlist(probe_stdout.decode('UTF-8'))
        '''
        songs = _parse_songlist(sys.stdin.read())
    if action == Action.CHECK_NEW or action == Action.FILE_CHECK_NEW:
        for start_time, end_time, raw_name in songs:
            if not _is_name_existing(raw_name):
                logging.info('New song: "{}"'.format(raw_name))
    elif action == Action.SPLIT:
        '''
        ffprobe = ffmpy.FFprobe(inputs={
                compilation_path: ['-show_entries', 'stream_tags=title', '-print_format', 'default=nokey=1:noprint_wrappers=1']
            }
        )
        probe_stdout, probe_stderr = ffprobe.run(stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)
        compilation_title = probe_stdout.decode('UTF-8').rstrip()
        '''
        _split_file(compilation_path, compilation_title, compilation_author, songs)
    else:
        logging.critical('Invalid action "{}"'.format(action))
        exit(1)

def _youtubedl_hook(data):
    '''youtube-dl download hook'''
    # TODO: Parse description for artist names and add to song names
    status = data['status']
    if status == 'downloading':
        downloaded_bytes = data.get('downloaded_bytes', 0)
        total_bytes = data.get('total_bytes', None)
        total_bytes_estimate = data.get('total_bytes_estimate', None)
        if total_bytes:
            progress = "{}%".format(round(downloaded_bytes / total_bytes * 100, 1))
        elif total_bytes_estimate:
            progress = "{}%".format(round(downloaded_bytes / total_bytes_estimate * 100, 1))
        else:
            progress = 'Unknown progress'
        elapsed = data.get('elapsed', None)
        if elapsed is None:
            elapsed = 'Unknown'
        speed = data.get('speed', None)
        if speed is None:
            speed = 'Unknown'
        eta = data.get('eta', None)
        if eta is None:
            eta = 'Unknown'
        print("{percentage} speed: {speed}, eta: {eta}, elapsed: {elapsed}".format(
            percentage=progress,
            speed=speed,
            eta=eta,
            elapsed=elapsed
        ), end='\r')
    elif status == 'finished':
        print('{filename} finished downloading'.format(
            filename=data.get('filename', '(Unknown Path)')
        ))
    elif status == 'error':
        logging.critical('youtube-dl: {}'.format(str(data)))
        exit(1)

def _get_songs_from_chapters(chapters):
    '''Parses youtube-dl's chapters format into a list of tuples of (start_time, end_time, raw_name)'''
    songs = list()
    for chapter in chapters:
        songs.append((
            str(chapter['start_time']),
            str(chapter['end_time']),
            chapter['title']
        ))
    return songs

def _process_youtube(action, proxy, compilation_urls):
    '''Processes a YouTube URL'''
    if action != Action.SPLIT and action != Action.CHECK_NEW:
        logging.critical('Invalid action {}'.format(action))
        exit(1)

    ydl_opts = {
        #'progress_hooks': [_youtubedl_hook],
        'logger': _get_logger(youtube_dl.__name__),
        'cachedir': YOUTUBE_DL_CACHE,
        'call_home': False,
        'format': '171', # webm + vorbis
        'outtmpl': YOUTUBE_DL_DOWNLOADS + '/%(id)s.%(ext)s',
        'nooverwrites': True,
    }
    if proxy:
        ydl_opts['proxy'] = proxy

    logging.info('Checking for new songs')

    known_song_names = set()
    # TODO: Remove hardcoding
    known_song_names.add('listen_again') # Hack to remove songs being repeated in The Soul of Wind compilations
    initial_known_song_names_size = len(known_song_names)
    url_to_new_songs = dict()
    url_to_metadata = dict()
    needs_qualification = set()
    needs_encoding = set()
    no_chapters = set()
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for url in compilation_urls:
            logging.info('URL: {}'.format(url))
            try:
                info = ydl.extract_info(url, download=False)
            except youtube_dl.utils.DownloadError:
                needs_encoding.add(url)
                logging.warning('Songs need re-encoding')
                continue
            title = info['title']
            logging.info('Title: {}, Format: {}'.format(title, info['format']))
            if info['ext'] != 'webm':
                logging.critical('Unexpected extension {}'.format(info['ext']))
                exit(1)
            if info['acodec'] != 'vorbis':
                logging.critical('Unexpected audio codec {}'.format(info['acodec']))
                exit(1)
            url_to_metadata[url] = (info['id'], title, info['uploader'])
            chapters = info['chapters']
            if not chapters:
                # TODO: If no chapters but song is short enough (<20 min?), then assume it is a single song and use video title as song name
                no_chapters.add(url)
                logging.warning('Compilation has no chapters')
                continue
            songs = _get_songs_from_chapters(chapters)
            for song in songs:
                start_time, end_time, raw_name = song
                formatted_name = _format_name(raw_name)
                if '_' not in formatted_name:
                    # Hack to detect songs with one word in them. These songs from this video will need to be qualified with an artist name later on
                    logging.warning('Songs need qualification')
                    needs_qualification.add(url)
                    del url_to_metadata[url]
                    if url in url_to_new_songs:
                        del url_to_new_songs[url]
                    break
                if not _is_name_existing(raw_name, name_collection=known_song_names) and not _is_name_existing(raw_name):
                    if url not in url_to_new_songs:
                        url_to_new_songs[url] = list()
                    url_to_new_songs[url].append(song)
                    known_song_names.add(formatted_name)
                    logging.info('Found new song: {}'.format(raw_name))
        if action == Action.CHECK_NEW:
            if len(known_song_names) > initial_known_song_names_size:
                logging.info("Found new songs!")
            else:
                logging.info("No new songs")
        elif action == Action.SPLIT:
            logging.info('Downloading new songs')
            ydl.download(list(url_to_new_songs.keys()))
            logging.info('Splitting up new songs')
            for url in url_to_new_songs:
                compilation_id, compilation_title, compilation_author = url_to_metadata[url]
                compilation_path = os.path.join(YOUTUBE_DL_DOWNLOADS, compilation_id + '.webm')
                _split_file(compilation_path, compilation_title, compilation_author, url_to_new_songs[url])
            logging.info('Done processing songs')
        if needs_qualification:
            logging.info('Skipped URLs that need artist(s) names: {}'.format(str(needs_qualification)))
        if needs_encoding:
            logging.info('Skipped URLs that need re-encoding: {}'.format(str(needs_encoding)))
        if no_chapters:
            logging.info('Skipped URLs that have no chapters: {}'.format(str(no_chapters)))

def _main(action_type, action, *args):
    _get_logger()
    if action_type == 'file':
        if len(args) != 3:
            logging.critical('There can be only 4 more arguments for action type "file"')
            exit(1)
        compilation_title = args[0]
        compilation_author = args[1]
        compilation_path = args[2]
        if compilation_path is None:
            raise Exception('compilation_path cannot be blank')
        if not os.path.isfile(compilation_path):
            raise Exception('compilation_path must be a file')
        _process_file(action, compilation_title, compilation_author, compilation_path)
    elif action_type == 'youtube':
        # TODO: Fix hardcoded proxy
        _process_youtube(action, PROXY, args)
    else:
        logging.critical('Invalid action type "{}"'.format(action))
        exit(1)

if __name__ == '__main__':
    _main(*sys.argv[1:])
