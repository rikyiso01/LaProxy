from __future__ import annotations
from laproxy import TCPProxy, HTTPHandler, HTTPRequest, HTTPResponse


class Handler(HTTPHandler):
    def request(self, request: HTTPRequest, /) -> HTTPRequest | None:
        return request

    def response(self, response: HTTPResponse, /) -> HTTPResponse | None:
        if b"flag" in response.body:
            return None
        return response


if __name__ == "__main__":
    TCPProxy("0.0.0.0", 8080, "www.google.com", 80, Handler).run()
