# PyProxy

## Introduction

> A fast way to create proxies

## Code Samples

> ### TCP
>
> ```python
> from pyproxy import TCPProxy, TCPHandler
> 
> class Handler(TCPHandler):
>     def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
>         if b"ciao" in packet and not inbound:
>             return None
>         return packet
> 
> TCPProxy("0.0.0.0", 1234, "127.0.0.1", 5005, Handler).run()
> ```
>
> ### HTTP
>
> ```python
> from pyproxy import TCPProxy, HTTPHandler, HTTPRequest, HTTPResponse
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
> TCPProxy("0.0.0.0", 1234, "127.0.0.1", 5005, Handler).run()
> ```
>
> 

## Installation

> Install locally with:
>
> ```bash
> pip install git+ssh://git@github.com/rikyiso01/pyproxy.git
> ```
>
> Or use it in a docker compose:
>
> ```yaml
> version: "3.9"
> services:
>   proxy:
>     image: ghcr.io/rikyiso01/pyproxy:main
>     ports:
>       - "1234:1234"
>     volumes:
>       - ./proxy.py:/app/proxy.py
>     command: python proxy.py
> ```