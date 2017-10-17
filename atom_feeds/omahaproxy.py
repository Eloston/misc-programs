# -*- coding: utf-8 -*-

# Spits out Omahaproxy stable channel info to stdout in Atom format
# Atom code is from https://github.com/rpcope1/pyatom

import sys
import datetime
import urllib.request
import json

import pyatom

if __name__ == "__main__":
    SOURCE_URL = "https://omahaproxy.appspot.com/history.json?channel=stable"
    OS_ID_CONVERSION = {
        "ios": "iOS",
        "cros": "Chrome OS",
        "win": "Windows",
        "win64": "Windows 64-bit",
        "linux": "Linux",
        "mac": "Mac OSX",
        "cf": "Chrome Frame",
        "android": "Android",
        "webview": "Android WebView"
    }

    def init_feed():
        return pyatom.AtomFeed(title="Chrome Stable Releases",
                    subtitle="Stable release versions from Omahaproxy",
                    feed_url=SOURCE_URL,
                    url="https://omahaproxy.appspot.com/")

    def exception_hook(*args):
        feed = init_feed()
        time_of_exception = datetime.datetime.utcnow()
        import traceback
        feed.add(title="Exception has occured!",
                content="<p>" + "<br />".join(traceback.format_exception(*args)) + "</p>",
                content_type="html",
                updated=time_of_exception,
                id=str(time_of_exception))
        print(feed.to_string())
        sys.exit()

    sys.excepthook = exception_hook

    feed = init_feed()

    with urllib.request.urlopen(SOURCE_URL) as response:
        json_encoder = json.JSONEncoder(indent=4)
        for version in json.loads(response.read().decode("UTF-8")):
            if len(feed.entries) > 50:
                break
            version_date, version_time = version["timestamp"].split(" ")
            version_year, version_month, version_day = (int(x, 10) for x in version_date.split("-"))
            if "." in version_time:
                version_hour, version_minute, version_second, version_microsecond = (int(x, 10) for x in version_time.replace(".", ":").split(":"))
            else:
                version_hour, version_minute, version_second = (int(x, 10) for x in version_time.split(":"))
                version_microsecond = 0
            item_updated = datetime.datetime(version_year, version_month, version_day, version_hour, version_minute, version_second, version_microsecond)
            feed.add(title=OS_ID_CONVERSION[version["os"]] + ": " + version["version"],
                    content="<p>" + json_encoder.encode(version) + "</p>",
                    content_type="html",
                    updated=datetime.datetime(version_year, version_month, version_day, version_hour, version_minute, version_second, version_microsecond),
                    url="https://omahaproxy.appspot.com/deps.json?version=" + version["version"],
                    id=version["os"] + "_" + version["version"])

    print(feed.to_string())
