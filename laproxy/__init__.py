"""
# LaProxy

## Introduction

> An easy to use proxy for A/D CTFs  
> You can read the documentation at [rikyiso01.github.io/LaProxy](https://rikyiso01.github.io/LaProxy)

## Code Samples

> ### TCP
>
> ```python
> from laproxy import TCPProxy, TCPHandler
>
>
> class Handler(TCPHandler):
>     def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
>         if b"ciao" in packet and not inbound:
>             return None
>         return packet
>
>
> if __name__ == "__main__":
>     TCPProxy("0.0.0.0", 1234, "127.0.0.1", 5005, Handler).run()
> ```
>
> ### HTTP
>
> ```python
> from laproxy import TCPProxy, HTTPHandler, HTTPRequest, HTTPResponse
>
>
> class Handler(HTTPHandler):
>     def request(self, request: HTTPRequest, /) -> HTTPRequest | None:
>         return request
>
>     def response(self, response: HTTPResponse, /) -> HTTPResponse | None:
>         if b"flag" in response.body:
>             return None
>         return response
>
> if __name__ == "__main__":
>     TCPProxy("0.0.0.0", 1234, "127.0.0.1", 5005, Handler).run()
> ```
>
> You can find more examples in the samples folder

## Installation

> Install locally with:
>
> ```bash
> python3 -m pip install laproxy
> ```
>
> Or use it in a docker compose:
>
> ```yaml
> version: "3.9"
> services:
>     proxy:
>         image: ghcr.io/rikyiso01/laproxy:latest
>         ports:
>             - "1234:1234"
>         volumes:
>             - ./proxy.py:/app/proxy.py
> ```

"""
from __future__ import annotations
from ._laproxy import Proxy, Handler
from ._tcp import TCPProxy, TCPHandler, NoTCPHandler, TCPLineHandler
from ._http import HTTPHandler, HTTPPayload, HTTPResponse, HTTPRequest, NoHTTPHandler

__all__ = [
    "Proxy",
    "Handler",
    "TCPProxy",
    "TCPHandler",
    "NoTCPHandler",
    "TCPLineHandler",
    "HTTPHandler",
    "HTTPPayload",
    "HTTPResponse",
    "HTTPRequest",
    "NoHTTPHandler",
]
