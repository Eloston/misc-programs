#!/usr/bin/env python3

import pathlib

"""Prints the smallest unused X11 display number"""

def get_session_list():
    sessions = list()
    for socket_path in pathlib.Path("/tmp/.X11-unix").rglob("*"):
        display = int(socket_path.name[1:])
        sessions.append(display)
    sessions.sort()
    return sessions

def find_unused_display_number(int_list):
    if not int_list:
        return 0
    current_value = 0
    for i in int_list:
        assert type(i) is int
        assert i >= 0
        if i != current_value:
            return current_value
        current_value += 1
    return current_value

if __name__ == "__main__":
    print(find_unused_display_number(get_session_list()))
