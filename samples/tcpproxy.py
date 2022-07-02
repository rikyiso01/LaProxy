from __future__ import annotations
from laproxy import TCPProxy, TCPHandler


class Handler(TCPHandler):
    def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
        if b"ciao" in packet and not inbound:
            return None
        return packet


if __name__ == "__main__":
    TCPProxy("0.0.0.0", 1234, "127.0.0.1", 5005, Handler).run()
