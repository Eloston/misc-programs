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
                    <title>Start Desktop</title>
                </head>
                <body>
                    <button onclick="sendRequest()">Start Desktop</button>
                    <script>
                        function sendRequest() {
                            var xhr = new XMLHttpRequest();
                            xhr.open('POST', '/', true);
                            xhr.send();
                        }
                    </script>
                </body>
            </html>
        '''
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        try:
            print('Running systemctl stop gdm3')
            output = subprocess.run(["systemctl", "stop", "gdm3"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print('stdout:', output.stdout)
            print('stderr:', output.stderr)
            print('Running systemctl start eloston-gnome@tty1')
            output = subprocess.run(["systemctl", "start", "eloston-gnome@tty1"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print('stdout:', output.stdout)
            print('stderr:', output.stderr)
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
