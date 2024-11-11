#!/usr/bin/python3

# Asynchronous IO File Transfer Web Service
# Created as an experiment from a conversation with Bing Copilot

import argparse
import asyncio
import urllib.parse
from aiohttp import web
import ipaddress
from pathlib import Path
import netifaces
from typing import List
from datetime import datetime

async def on_prepare(request: web.Request, response: web.StreamResponse) -> None:
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

def get_ip_port(request: web.Request) -> (str, int):
    info = request.transport.get_extra_info('peername')
    return info[:2]

class TreeHTTPRequestHandler(web.View):
    async def get(self) -> web.Response:
        path: Path = Path(self.request.match_info.get('path', ''))
        if path.is_absolute():
            return web.Response(status=400, text='Absolute paths not allowed')
        if not self.request.transport:
            return web.Response(status=500, text='Missing request.transport')
        client_ip, client_port = get_ip_port(self.request)
        print(f'Client {client_ip}:{client_port} opened {path}')

        full_path: Path = (Path.cwd() / path).resolve()

        # Disallow browsing files outside of the current working directory
        if not full_path.is_relative_to(Path.cwd().resolve()):
            return web.Response(status=403, text='Access denied')

        if not full_path.exists():
            return web.Response(status=404, text='File not found')

        if full_path.resolve().is_dir():
            dirs: List[str] = []
            files: List[str] = []
            # Note: Since "path" is always relative and Path('.').parent == Path('.'), this will never escape the current directory
            # Therefore we just remove the parent directory when we're at the root directory
            if path != Path():
                parent_dir: str = urllib.parse.quote(f'/{path.parent.as_posix()}') if path else ''
                dirs += [f'<li><a href="{parent_dir}">&lt;Parent Directory&gt;</a></li>']
            for entry in sorted(full_path.iterdir()):
                entry_href: str = urllib.parse.quote(f'/{(path / entry.name).as_posix()}')
                if entry.resolve().is_dir():
                    dirs += [f'<li><a href="{entry_href}/">{entry.name}/</a></li>']
                elif entry.resolve().is_file():
                    files += [f'<li><a href="{entry_href}">{entry.name}</a></li>']
            body: bytes = f'<html><head><title>Index of: {path}</title></head><body><h1>Index of: {path}</h1><ul>{" ".join(dirs + files)}</ul></body></html>'.encode('utf-8')
            return web.Response(body=body, content_type='text/html')
        elif full_path.resolve().is_file():
            return web.FileResponse(full_path)
        else:
            return web.Response(status=404, text='File not found')

async def handle_upload_page(request: web.Request) -> web.Response:
    client_ip, client_port = get_ip_port(request)
    print(f'Client {client_ip}:{client_port} opened upload page')
    body: bytes = b'''
    <html>
        <head>
            <title>Upload File</title>
            <script>
                function updateFileList() {
                    var input = document.getElementById('fileInput');
                    var list = document.getElementById('fileList');
                    list.innerHTML = '';
                    for (var i = 0; i < input.files.length; i++) {
                        var li = document.createElement('li');
                        li.textContent = input.files[i].name;
                        list.appendChild(li);
                    }
                }
            </script>
        </head>
        <body>
            <h1>Upload File</h1>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file[]" id="fileInput" multiple onchange="updateFileList()">
                <ul id="fileList"></ul>
                <input type="submit" value="Upload">
            </form>
        </body>
    </html>
    '''
    response = web.Response(body=body, content_type='text/html')
    return response

async def handle_upload(request: web.Request) -> web.Response:
    reader = await request.multipart()
    if not request.transport:
        return web.Response(status=500, text='Missing request.transport')
    client_ip, client_port = get_ip_port(request)
    print(f'Client {client_ip}:{client_port} is uploading files...')
    upload_time: str = datetime.now().isoformat()
    upload_dir: Path = Path(f"/tmp/upload_{upload_time}_{client_ip}:{client_port}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    uploaded_files: List[str] = []
    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name == 'file[]':
            filename: str = field.filename
            size: int = 0
            file_path: Path = upload_dir / filename
            with open(file_path, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()  # 8192 bytes by default.
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)
            uploaded_files.append(f'<li>{filename}, size: {size} bytes</li>')
    body = f'''
    <html>
        <head><title>Upload Result</title></head>
        <body>
            <h1>Upload Result</h1>
            <ul>{" ".join(uploaded_files) if uploaded_files else '<li>No files uploaded</li>'}</ul>
            <a href="/">Upload more files</a>
        </body>
    </html>
    '''
    print(f'Client {client_ip}:{client_port} has finished uploading {len(uploaded_files)} {"file" if len(uploaded_files) == 1 else "files"}')
    return web.Response(body=body.encode('utf-8'), content_type='text/html')

async def init_app(mode: str) -> web.Application:
    app = web.Application()
    app.on_response_prepare.append(on_prepare)

    if mode == 'tree':
        app.router.add_get('/{path:.*}', TreeHTTPRequestHandler)
    elif mode == 'upload':
        app.router.add_get('/', handle_upload_page)
        app.router.add_post('/upload', handle_upload)
    
    return app

async def run_server(app: web.Application, ip: str, port: int) -> None:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, ip, port)
    await site.start()
    print(f'Serving on {ip}:{port}')

def get_private_and_link_local_ips() -> List[str]:
    ip_addresses: List[str] = []
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        for family in (netifaces.AF_INET, netifaces.AF_INET6):
            if family in addrs:
                for addr in addrs[family]:
                    ip = ipaddress.ip_address(addr['addr'])
                    if ip.is_private or ip.is_link_local:
                        ip_addresses.append(str(ip))
    return ip_addresses

def main() -> None:
    parser = argparse.ArgumentParser(description='Start an async web server in either tree or upload mode.')
    parser.add_argument('mode', choices=['tree', 'upload'], help='Mode to run the server in')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('-a', '--address', help='Specific IP address to listen to')
    args = parser.parse_args()

    port: int = args.port

    if args.address:
        ip_addresses: List[str] = [args.address]
    else:
        # Find all private or link-local IP addresses
        ip_addresses = get_private_and_link_local_ips()
        if not ip_addresses:
            raise RuntimeError("No private or link-local IP addresses found.")

    loop = asyncio.get_event_loop()
    app: web.Application = loop.run_until_complete(init_app(args.mode))

    tasks = [run_server(app, ip, port) for ip in ip_addresses]
    loop.run_until_complete(asyncio.gather(*tasks))

    # Keep the loop running
    loop.run_forever()

if __name__ == '__main__':
    main()
