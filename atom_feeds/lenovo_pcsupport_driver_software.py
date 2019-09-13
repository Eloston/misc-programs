#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parses the a Lenovo Support "Drivers & Software" page for latest versions

Designed for use as a conversion filter for Liferea (news aggregator).

Takes no arguments.

Usage:
1. Get an update page URL like: https://pcsupport.lenovo.com/products/laptops-and-netbooks/thinkpad-x-series-laptops/thinkpad-x1-carbon-type-20hr-20hq/downloads/ds120390
2. Take the last path component (e.g. ds120390) and add it to the following URL as follows:
    https://pcsupport.lenovo.com/api/v4/downloads/driver?docId=ds120390
3. Send the document's body at that URL as standard input to this program.
4. This program's standard output is the Atom feed.
"""

import base64
import datetime
import html
import json
import re
import sys

import pyatom

_FILE_ITEM_HTML = """
<div>
<a href="{download_url}"><b>{name}</b></a>
<ul>
<li>Type: {typestring}</li>
<li>Size: {size}</li>
<li>MD5: {md5}</li>
<li>SHA-256: {sha256}</li>
</ul>
</div>
"""

_MAIN_DESCRIPTION_HTML = """
<h2>Change Log</h2>
<p>
<div>
{changelog_html}
</div>
</p>
<h2>Files</h3>
<p>
<div>
{file_html}
</div>
</p>
<h2>Description</h2>
<p>
<div>
{body_html}
</div>
</p>
"""

def _parse_driver_document(driver_document):
    if not driver_document.get('message') == 'succeed':
        raise ValueError(f'Unexpected message value: {driver_document.get("message")}')
    assert 'body' in driver_document
    return driver_document['body']['DriverDetails'], driver_document['body']['ChangeLogText']

def _populate_feed_meta(feed_args, driver_details):
    feed_args['url'] = 'https://pcsupport.lenovo.com/downloads/{}'.format(
        driver_details["DocId"],
    )
    feed_args['title'] = driver_details['Title']

def populate_feed_entries(feed, driver_details, changelog_text):
    """
    Populate AtomFeed with entries
    """
    file_html_items = list()
    for file_dict in driver_details["Files"]:
        file_html_items.append(
            _FILE_ITEM_HTML.format(
                name=file_dict["Name"],
                typestring=file_dict["TypeString"],
                size=file_dict["Size"],
                download_url=file_dict["URL"],
                md5=file_dict["MD5"],
                sha256=file_dict["SHA256"]))
    main_html = _MAIN_DESCRIPTION_HTML.format(
        changelog_html=html.escape(changelog_text if changelog_text else '(Unspecified)'),
        file_html="\n".join(file_html_items),
        body_html=html.unescape(driver_details["Body"]),
    )
    feed_entry_id = str(driver_details['Date']['Unix']) + driver_details['Files'][0]['Version']
    feed.add(
        title=driver_details["Files"][0]["Version"],
        content=main_html,
        content_type="html",
        updated=datetime.datetime.utcfromtimestamp(driver_details["Updated"]["Unix"] // 1000),
        id=feed_entry_id)


def main():
    """Entrypoint"""
    # This should NOT be replaced; it should be updated so that
    # exception_hook can use this instance to create its own special
    # feed with as accurate arguments as possible
    feed_args = dict(
        title='(Unknown Lenovo pcsupport driver)',
        url='about:blank'
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

    # Load driver details
    driver_document = json.load(sys.stdin)
    driver_details, changelog_text = _parse_driver_document(driver_document)
    assert driver_details

    # Setup feed and metadata
    _populate_feed_meta(feed_args, driver_details)
    feed = pyatom.AtomFeed(**feed_args)

    # Populate feed entries
    populate_feed_entries(feed, driver_details, changelog_text)

    # Output feed
    print(feed.to_string())


if __name__ == "__main__":
    main()
