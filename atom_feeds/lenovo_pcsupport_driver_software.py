#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parses the a Lenovo Support "Drivers & Software" page for version info

Originally used for checking BIOS updates, but can be used with any Support page software download

Takes in one argument: computer_name
- computer_name is a string like L460

It reads the update page contents from standard input. The update page can be obtained from
a URL like: http://pcsupport.lenovo.com/us/en/products/LAPTOPS-AND-NETBOOKS/THINKPAD-L-SERIES-LAPTOPS/THINKPAD-L460/downloads/DS112198
"""

# TODO: Homepage for backup driver download site:
# https://download.lenovo.com/supportdata/index.html
# All machine drivers available at URLs like this:
# https://download.lenovo.com/supportdata/Product/LAPTOPS-AND-NETBOOKS/THINKPAD-L-SERIES-LAPTOPS/THINKPAD-L460.json
# https://download.lenovo.com/supportdata/Product/LAPTOPS-AND-NETBOOKS/THINKPAD-X-SERIES-LAPTOPS/THINKPAD-X1-CARBON-TYPE-20HR-20HQ.json
# Driver page info metadata, but it's out of date compared to the machine info:
# https://download.lenovo.com/supportdata/Driver/DS112198.en.json
# Languages: en for English, ko for Korean, ja for Japanese

import base64
import datetime
import html
import json
import re
import sys

import bs4
import lz4.block # python-lz4 from pypi version 2.1.0
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

_DS_GETCONTENT_REGEX = re.compile(
    r'ds_getcontent[ ]*?=[ ]*?l\.Common\.lz4Decode\((?P<arg_dict>[a-zA-Z0-9+/ =",:{}]+?)\);')


def _parse_ds_getcontent(soup):
    """Returns the processed ds_getcontent body"""
    match = None
    for script_element in soup.find_all('script'):
        if len(script_element.contents) == 1:
            match = _DS_GETCONTENT_REGEX.search(script_element.contents[0].replace('\n', ''))
            if match:
                break
    assert match
    lz4decode_jsonarg = json.loads(match.group('arg_dict'))
    lz4decode_base64 = lz4decode_jsonarg['content']
    lz4decode_originlength = lz4decode_jsonarg['originLength']
    lz4decode_compressed = base64.b64decode(lz4decode_base64)
    ds_getcontent_bytes = lz4.block.decompress(
        lz4decode_compressed, uncompressed_size=lz4decode_originlength)
    return json.loads(ds_getcontent_bytes.decode('UTF-8'))


def _get_update_url(soup):
    """Returns the update URL used for the page"""
    results = soup.find_all('link', attrs={'rel': 'canonical'})
    if not len(results) == 1:
        raise ValueError(
            'Got {} results instead of 1 result for <link rel="canonical" ...>'.format(
                len(results)))
    link_element = results[0]
    assert 'href' in link_element.attrs
    return link_element['href']


def parse_support_page(feed, soup, update_url):
    """
    Returns a list of dictionaries containing:
    - The current version
    - The release date
    - The changes since the last version
    - Files for download which include names, URLs, and checksums
    """
    ds_getcontent = _parse_ds_getcontent(soup)
    assert ds_getcontent
    file_html_items = list()
    for file_dict in ds_getcontent["Files"]:
        file_html_items.append(
            _FILE_ITEM_HTML.format(
                name=file_dict["Name"],
                typestring=file_dict["TypeString"],
                size=file_dict["Size"],
                download_url=file_dict["URL"],
                md5=file_dict["MD5"],
                sha256=file_dict["SHA256"]))
    main_html = _MAIN_DESCRIPTION_HTML.format(
        file_html="\n".join(file_html_items), body_html=html.unescape(ds_getcontent["Body"]))
    feed_entry_id = str(ds_getcontent['Date']['Unix']) + ds_getcontent['Files'][0]['Version']
    feed.add(
        title=ds_getcontent["Files"][0]["Version"],
        content=main_html,
        content_type="html",
        updated=datetime.datetime.utcfromtimestamp(ds_getcontent["Updated"]["Unix"] // 1000),
        url=update_url,
        id=feed_entry_id)


def main():
    """Entrypoint"""
    # Specify a string, like L460
    computer_name = sys.argv[1]
    # Specify a URL, like http://pcsupport.lenovo.com/us/en/products/LAPTOPS-AND-NETBOOKS/THINKPAD-L-SERIES-LAPTOPS/THINKPAD-L460/downloads/DS112198

    atom_title = "{} Updates".format(computer_name)
    atom_subtitle = "View software update changes for {}".format(computer_name)

    soup = bs4.BeautifulSoup(sys.stdin.read(), "lxml")
    update_url = _get_update_url(soup)

    def init_feed():
        """Initialize the atom feed"""
        return pyatom.AtomFeed(
            title=atom_title, subtitle=atom_subtitle, feed_url=update_url, url=update_url)

    def exception_hook(exc_type, exc_value, exc_traceback):
        """Atom feed generator for exceptions"""
        feed = init_feed()
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

    feed = init_feed()

    parse_support_page(feed, soup, update_url)
    print(feed.to_string())


if __name__ == "__main__":
    main()
