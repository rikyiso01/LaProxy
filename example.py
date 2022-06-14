from pyproxy import TCPProxy, NoTCPHandler, NoHTTPHandler, TCPHandler


class Handler(TCPHandler):
    def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
        if b"ciao" in packet:
            return None
        return packet


TCPProxy("0.0.0.0", 1234, "127.0.0.1", 5005, Handler).run()
