#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parses the a Lenovo BIOS update page for version info

Constants can be modified to be used with other BIOS update pages

Takes in two arguments: computer_name update_url
- computer_name is a string like L460
- update_url is the page for a specific driver download, like http://pcsupport.lenovo.com/us/en/products/LAPTOPS-AND-NETBOOKS/THINKPAD-L-SERIES-LAPTOPS/THINKPAD-L460/downloads/DS112198
"""

import urllib.request
import sys
import shlex
import datetime
import html
import json

import bs4
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

def parse_support_page(feed, update_url):
    """
    Returns a list of dictionaries containing:
    - The current version
    - The release date
    - The changes since the last version
    - Files for download which include names, URLs, and checksums
    """
    with urllib.request.urlopen(update_url) as response:
        soup = bs4.BeautifulSoup(response.read().decode("UTF-8"), "lxml")
    ds_getcontent = None
    for script_element in soup.find_all("script"):
        if len(script_element.contents) == 1:
            if script_element.contents[0].startswith("ds_productinfo"):
                # Need to unescape twice. Once due to escaping to store in a
                # JS string, and a second time to unescape escaped characters
                # in the original HTML like nbsp
                ds_getcontent = script_element.contents[0].split(";ds_getcontent=")[1].split(";ds_warranties=")[0]
    assert ds_getcontent
    ds_getcontent = json.loads(ds_getcontent)
    file_html_items = list()
    for file_dict in ds_getcontent["Files"]:
        file_html_items.append(
            _FILE_ITEM_HTML.format(
                name=file_dict["Name"],
                typestring=file_dict["TypeString"],
                size=file_dict["Size"],
                download_url=file_dict["URL"],
                md5=file_dict["MD5"],
                sha256=file_dict["SHA256"]
            )
        )
    main_html = _MAIN_DESCRIPTION_HTML.format(
        file_html="\n".join(file_html_items),
        body_html=html.unescape(ds_getcontent["Body"])
    )
    feed.add(
        title=ds_getcontent["Files"][0]["Version"],
        content=main_html,
        content_type="html",
        updated=datetime.datetime.utcfromtimestamp(ds_getcontent["Date"]["Unix"] // 1000),
        url=update_url,
        id=ds_getcontent["Date"]["UTC"]
    )

if __name__ == "__main__":
    # Specify a string, like L460
    computer_name = sys.argv[1]
    # Specify a URL, like http://pcsupport.lenovo.com/us/en/products/LAPTOPS-AND-NETBOOKS/THINKPAD-L-SERIES-LAPTOPS/THINKPAD-L460/downloads/DS112198
    update_url = sys.argv[2]

    _ATOM_TITLE = "{} BIOS Updates".format(computer_name)
    _ATOM_SUBTITLE = "View BIOS update changes for {}".format(computer_name)

    def init_feed():
        return pyatom.AtomFeed(
            title=_ATOM_TITLE,
            subtitle=_ATOM_SUBTITLE,
            feed_url=update_url,
            url=update_url
        )

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

    parse_support_page(feed, update_url)
    print(feed.to_string())
