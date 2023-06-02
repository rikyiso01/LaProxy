from __future__ import annotations
from asyncio import StreamReader, StreamWriter
from abc import ABC, abstractmethod
from ._laproxy import Handler
from dataclasses import dataclass
from collections import UserDict
from re import compile

HEADER_RE = compile(r"([^:]+):\s+(.+)")
REQUEST_LINE_RE = compile(r"(\w+)\s+(.+)\s+HTTP\/(\d\.\d)")
RESPONSE_LINE_RE = compile(r"HTTP\/(\d\.\d)\s+(\d+)\s+(.+)")


class MalformedHeaderException(Exception):
    ...


class MalformedRequestLineException(Exception):
    ...


class MalformedResponseLineException(Exception):
    ...


class HTTPHeaders(UserDict[str, str]):
    @staticmethod
    async def parse_headers(reader: StreamReader, /) -> HTTPHeaders:
        result = HTTPHeaders()
        while True:
            line = (await reader.readline()).strip().decode()
            if not line:
                break
            match = HEADER_RE.match(line)
            if match is None:
                raise MalformedHeaderException(line)
            key = match.group(1)
            value = match.group(2)
            result[key] = value
        return result

    def __getitem__(self, item: str) -> str:
        return self.data[item.lower()]

    def __setitem__(self, item: str, value: str) -> None:
        self.data[item.lower()] = value


@dataclass
class HTTPPayload:
    @staticmethod
    async def parse_body(reader: StreamReader, n: int, /) -> bytes:
        return await reader.readexactly(n)

    @staticmethod
    async def parse_payload(reader: StreamReader, /) -> HTTPPayload:
        headers = await HTTPHeaders.parse_headers(reader)
        body = b""
        if "content-length" in headers:
            body = await HTTPPayload.parse_body(reader, int(headers["Content-Length"]))
        return HTTPPayload(headers, body)

    headers: HTTPHeaders
    body: bytes

    def __bytes__(self) -> bytes:
        result = bytearray()
        for key, value in self.headers.items():
            result.extend(f"{key}: {value}\r\n".encode())
        result.extend(b"\r\n")
        if self.body:
            result.extend(self.body)
        return bytes(result)


@dataclass
class HTTPRequest(HTTPPayload):
    @staticmethod
    async def parse_request(reader: StreamReader, /) -> HTTPRequest | None:
        line = (await reader.readline()).decode().strip()
        if not line:
            return None
        match = REQUEST_LINE_RE.match(line)
        if match is None:
            raise MalformedRequestLineException(line)
        method = match.group(1)
        path = match.group(2)
        version = float(match.group(3))
        payload = await HTTPPayload.parse_payload(reader)
        return HTTPRequest(payload.headers, payload.body, method, path, version)

    method: str
    path: str
    version: float

    def __bytes__(self) -> bytes:
        return (
            f"{self.method} {self.path} HTTP/{self.version}\r\n".encode()
            + super().__bytes__()
        )


@dataclass
class HTTPResponse(HTTPPayload):
    @staticmethod
    async def parse_response(reader: StreamReader, /) -> HTTPResponse | None:
        line = (await reader.readline()).decode().strip()
        if not line:
            return None
        match = RESPONSE_LINE_RE.match(line)
        if not match:
            raise MalformedResponseLineException(line)
        version = match.group(1)
        code = match.group(2)
        message = match.group(3)
        payload = await HTTPPayload.parse_payload(reader)
        return HTTPResponse(
            payload.headers,
            payload.body,
            float(version),
            int(code),
            message,
        )

    version: float
    code: int
    message: str

    def __bytes__(self) -> bytes:
        return (
            f"HTTP/{self.version} {self.code} {self.message}\r\n".encode()
            + super().__bytes__()
        )


class HTTPHandler(Handler, ABC):
    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        while True:
            if inbound:
                request = await HTTPRequest.parse_request(reader)
                if request is None:
                    break
                content = self.request(request)
            else:
                response = await HTTPResponse.parse_response(reader)
                if response is None:
                    break
                content = self.response(response)
            if content is None:
                break
            writer.write(bytes(content))
        writer.close()
        await writer.wait_closed()

    @abstractmethod
    def request(self, request: HTTPRequest, /) -> HTTPRequest | None:
        ...

    @abstractmethod
    def response(self, response: HTTPResponse, /) -> HTTPResponse | None:
        ...


class NoHTTPHandler(HTTPHandler):
    def request(self, request: HTTPRequest, /) -> HTTPRequest | None:
        return request

    def response(self, response: HTTPResponse, /) -> HTTPResponse | None:
        return response
