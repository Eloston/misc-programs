# -*- coding: utf-8 -*-

# ASGI-compatible server written in starlette
# To run the server: python3 goa_dav_binder.py

import os

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse, RedirectResponse
import uvicorn

CALDAV_URL = os.environ.get('CALDAV_URL')
print('Using CalDAV URL:', CALDAV_URL)
CARDDAV_URL = os.environ.get('CARDDAV_URL')
print('Using CardDAV URL:', CARDDAV_URL)
WEBDAV_URL = os.environ.get('WEBDAV_URL')
print('Using WebDAV URL:', WEBDAV_URL)


async def homepage(request: Request):
    return PlainTextResponse('GNOME Online Accounts CalDAV/CardDAV Binder is running!')

async def blank_response(request: Request):
    if not WEBDAV_URL:
        return Response()
    return RedirectResponse(WEBDAV_URL)

async def dav(request: Request):
    mapping = {
        "caldav": CALDAV_URL,
        "carddav": CARDDAV_URL,
    }
    url = mapping[request.path_params["type"]]
    if not url:
        return Response()
    return RedirectResponse(url)

app = Starlette(
    debug=True,
    routes=[
        Route("/", endpoint=homepage),
        Route("/.well-known/{type}", endpoint=dav, methods=["PROPFIND"]),
        Mount(
            "/remote.php",
            routes=[
                Route("/webdav/", endpoint=blank_response),
                Route("/{type}/", endpoint=dav, methods=["PROPFIND"]),
            ],
        ),
    ],
)

if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=9264)
