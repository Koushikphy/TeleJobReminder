# Redirect network requests to the central bot server from a client
# when the client is not present in the same network layer as the bot.

import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# Central bot server url
BOT_SERVER = 'https://telejobreminder.fly.dev/api/'


class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        # Intercept the incoming request from a defered client, 
        post_data = self.rfile.read(content_length)
        # send it to the main bot server and get back the response
        req = requests.post(BOT_SERVER, post_data)
        # send back bot response back to the initial client
        self._set_headers(req.status_code)
        self.wfile.write(req.content)


def runServer(addr='0.0.0.0',port=8123):
    # 0.0.0.0 is default IP route of the system
    # requests targeted to this system's IP (and this port)
    # would be intercepted by this server
    server_address = (addr, port)
    # would fail if port is occupied, change port then
    httpd = HTTPServer(server_address, MyServer)
    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()



if __name__ == "__main__":
    runServer()