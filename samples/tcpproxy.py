from __future__ import annotations
from asyncio import open_connection
from laproxy import TCPProxy, TCPHandler


class Handler(TCPHandler):
    def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
        if b"ciao" in packet and not inbound:
            return None
        return packet


if __name__ == "__main__":
    TCPProxy("0.0.0.0", 5000, "www.google.com", 80, Handler).run()
