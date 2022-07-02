from laproxy import TCPProxy, HTTPHandler, HTTPRequest, HTTPResponse


class Handler(HTTPHandler):
    def request(self, request: HTTPRequest, /) -> HTTPRequest | None:
        return request

    def response(self, response: HTTPResponse, /) -> HTTPResponse | None:
        if b"flag" in response.body:
            return None
        return response

if __name__=='__main__':
    TCPProxy("0.0.0.0", 1234, "127.0.0.1", 5005, Handler).run()
