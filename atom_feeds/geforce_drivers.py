#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get a list of NVIDIA GeForce driver updates using the APIs of https://www.geforce.com/drivers

Designed for use as a conversion filter for Liferea (news aggregator).

Takes in no arguments.

Usage:
1. Go to https://www.geforce.com/drivers
2. Specify search criteria
3. Open browser's DevTools, and capture URL created by clicking "Start Search"
    Example URL with settings: GeForce, GeForce 10 Series (Notebook), GeForce GTX 1060, Windows 10 64-bit, English (US), Standard, All:
    https://gfwsl.geforce.com/services_toolkit/services/com/nvidia/services/AjaxDriverService.php?func=DriverManualLookup&psid=102&pfid=821&osID=57&languageCode=1033&beta=null&isWHQL=0&dltype=-1&dch=0&upCRD=0&sort1=0&numberOfResults=10
4. Pass in the URL's document body as standard input to this program.
5. This program's standard output is the Atom feed contents.
"""

import base64
import contextlib
import datetime
import html
import json
import re
import sys
import urllib.parse

import pyatom

_MAIN_DESCRIPTION_HTML = """
<h2>Download</h2>
<p>
<div>
<a href="{download_url}"><b>Download ({download_size})</b></a>
</div>
</p>
<h2>Metadata</h2>
<p>
<div>
<ul>
<li>OS: {os_name}</li>
<li>Language: {language_name}</li>
<li>ID: {driver_id}</li>
<li><a href="{banner_url}">Banner URL</a></li>
<li><a href="{banner_url_gfe}">Banner URL (GFE)</a></li>
</ul>
</div>
</p>
<h2>Notes</h2>
<h3>Release Highlights</h3>
<p>
<div>
{release_notes_html}
</div>
<h3>Supported Products</h3>
<p>
<div>
{supported_products_html}
</div>
</p>
<h3>Additional Information</h3>
<div>
{other_notes_html}
</div>
<h3>Installation Notes</h3>
<div>
{installation_notes_html}
</div>
<h3>Overview</h3>
<div>
{overview_html}
</div>
</p>
"""

def _parse_search_results(search_results):
    assert 'Success' in search_results
    assert 'Request' in search_results
    if len(search_results['Request']) != 1:
        raise ValueError('Unexpected number of Request entries: {}'.format(
            len(search_results['Request'])))
    assert 'numberOfResults' in search_results['Request'][0]
    if search_results['Success'] != search_results['Request'][0]['numberOfResults']:
        raise ValueError('Successful results does not match requested: {} != {}'.format(
            search_results['Success'],
            search_results['Request'][0]['numberOfResults'],
        ))
    return search_results['IDS']

def _decode_string(value):
    return html.unescape(urllib.parse.unquote(value if value else '(Unspecified)'))

class _HTMLBuilder:
    def __init__(self):
        self.html = ''

    @contextlib.contextmanager
    def enter(self, tag_name, **tag_attrs):
        serialized_attrs = " ".join(map('{}="{}"'.format, tag_attrs.items()))
        self.html += f'<{tag_name} {serialized_attrs}>'
        try:
            yield None
        finally:
            self.html += f'</{tag_name}>'

    def insert(self, serialized_html):
        self.html += serialized_html

    def __str__(self):
        return self.html

def _get_supported_products_html(series_list):
    builder = _HTMLBuilder()
    with builder.enter('ul'):
        for series in series_list:
            with builder.enter('li'):
                builder.insert(_decode_string(series['seriesname']))
                with builder.enter('ul'):
                    for product in series['products']:
                        with builder.enter('li'):
                            builder.insert(_decode_string(product['productName']))
    return str(builder)

def populate_feed_entries(feed, driver_list):
    """
    Populate AtomFeed with entries
    """
    # This is a guess of ReleaseDateTime's format
    # Syntax: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    # TODO: This is locale-dependent; perhaps use LanguageName to set correct locale?
    release_datetime_format = '%a %b %d, %Y'

    for driver_dict in map(lambda x: x['downloadInfo'], driver_list):
        main_html = _MAIN_DESCRIPTION_HTML.format(
            release_notes_html=_decode_string(driver_dict['ReleaseNotes']),
            supported_products_html=_get_supported_products_html(driver_dict['series']),
            other_notes_html=_decode_string(driver_dict['OtherNotes']),
            installation_notes_html=_decode_string(driver_dict['InstallationNotes']),
            overview_html=_decode_string(driver_dict['Overview']),
            download_url=driver_dict['DownloadURL'],
            download_size=driver_dict['DownloadURLFileSize'],
            os_name=_decode_string(driver_dict['OSName']),
            language_name=_decode_string(driver_dict['LanguageName']),
            driver_id=_decode_string(driver_dict['ID']),
            banner_url=driver_dict['BannerURL'],
            banner_url_gfe=driver_dict['BannerURLGfe'],
        )
        feed.add(
            title=driver_dict['Version'],
            content=main_html,
            content_type="html",
            url=driver_dict['DetailsURL'],
            updated=datetime.datetime.strptime(driver_dict["ReleaseDateTime"], release_datetime_format),
            id=driver_dict['ID'])


def main():
    """Entrypoint"""
    # This should NOT be replaced; it should be updated so that
    # exception_hook can use this instance to create its own special
    # feed with as accurate arguments as possible
    feed_args = dict(
        title='NVIDIA GeForce Drivers',
        url='https://www.geforce.com/drivers'
    )

    def exception_hook(exc_type, exc_value, exc_traceback):
        """Atom feed generator for exceptions"""
        feed = pyatom.AtomFeed(**feed_args)
        time_of_exception = datetime.datetime.utcnow()
        import traceback
        feed.add(
            title="Exception has occured!",
            content="<p>" + "<br />".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)) + "</p>",
            content_type="html",
            updated=time_of_exception,
            id=str(time_of_exception))
        print(feed.to_string())
        sys.exit()
    sys.excepthook = exception_hook

    # Load search results
    search_results = json.load(sys.stdin)
    driver_list = _parse_search_results(search_results)
    assert driver_list

    # Setup feed and metadata
    feed = pyatom.AtomFeed(**feed_args)

    # Populate feed entries
    populate_feed_entries(feed, driver_list)

    # Output feed
    print(feed.to_string())


if __name__ == "__main__":
    main()
