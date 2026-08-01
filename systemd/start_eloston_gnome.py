#!/usr/bin/env python3

import sys
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = '''
            <html>
                <head>
                    <title>Desktop Control</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        * {
                            box-sizing: border-box;
                            margin: 0;
                            padding: 0;
                        }
                        body {
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                        }
                        .btn-group {
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            gap: 5vmin;
                        }
                        .btn-start {
                            font-size: 6vmin;
                            padding: 6vmin;
                            width: 70vmin;
                        }
                        .btn-stop {
                            font-size: 4vmin;
                            padding: 4vmin;
                            width: calc(70vmin * 2 / 3);
                        }
                    </style>
                </head>
                <body>
                    <div class="btn-group">
                        <button class="btn-start" onclick="sendRequest('/start')">Start Desktop</button>
                        <button class="btn-stop" onclick="sendRequest('/stop')">Stop Desktop</button>
                    </div>
                    <script>
                        function sendRequest(path) {
                            var xhr = new XMLHttpRequest();
                            xhr.open('POST', path, true);
                            xhr.send();
                        }
                    </script>
                </body>
            </html>
        '''
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        try:
            if self.path == '/start':
                print('Running systemctl stop gdm3')
                output = subprocess.run(["systemctl", "stop", "gdm3"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print('stdout:', output.stdout)
                print('stderr:', output.stderr)
                print('Running systemctl start eloston-gnome@tty1')
                output = subprocess.run(["systemctl", "start", "eloston-gnome@tty1"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print('stdout:', output.stdout)
                print('stderr:', output.stderr)
            elif self.path == '/stop':
                print('Running systemctl start eloston-gnome-logout@tty1')
                output = subprocess.run(["systemctl", "start", "eloston-gnome-logout@tty1"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print('stdout:', output.stdout)
                print('stderr:', output.stderr)
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
        except Exception:
            self.send_response(500)
            self.end_headers()


def run():
    server_address = (sys.argv[1], int(sys.argv[2]))
    httpd = HTTPServer(server_address, RequestHandler, bind_and_activate=False)
    httpd.socket = socket.fromfd(3, httpd.address_family, httpd.socket_type)
    httpd.serve_forever()


if __name__ == '__main__':
    run()
