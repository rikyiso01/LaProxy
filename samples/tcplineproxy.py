from __future__ import annotations
from laproxy import TCPProxy, TCPLineHandler


class Handler(TCPLineHandler):
    def process_line(self, line: bytes, inbound: bool, /) -> bytes | None:
        if b"ciao" in line and not inbound:
            return None
        return line


if __name__ == "__main__":
    TCPProxy("0.0.0.0", 5001, "www.google.com", 80, Handler).run()
