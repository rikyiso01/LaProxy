from __future__ import annotations
from asyncio import StreamReader, StreamWriter
from abc import ABC, abstractmethod
from laproxy._laproxy import Handler
from laproxy._tcp import get_remote_host
from dataclasses import dataclass
from collections import UserDict
from re import compile
from typing import TYPE_CHECKING, final
from typing_extensions import override
from logging import getLogger

if TYPE_CHECKING:
    UserDict = UserDict[str, str]

HEADER_RE = compile(r"([^:]+):\s+(.+)")
REQUEST_LINE_RE = compile(r"(\w+)\s+(.+)\s+HTTP\/(\d\.\d)")
RESPONSE_LINE_RE = compile(r"HTTP\/(\d\.\d)\s+(\d+)\s+(.+)")


class MalformedHeaderException(Exception):
    """Exception raised when an http header is malformed"""

    ...


class MalformedRequestLineException(Exception):
    """Exception raised when an http request line is malformed"""

    ...


class MalformedResponseLineException(Exception):
    """Exception raised when an http response line is malformed"""

    ...


class HTTPHeaders(UserDict):
    """Case insensitive dictionary to use to store http headers"""

    __logger = getLogger("laproxy.HTTPHeaders")

    @staticmethod
    async def parse_headers(reader: StreamReader, /) -> HTTPHeaders:
        """Read the http headers from a stream reader

        - reader: The stream reader to read the data from

        - returns: A case insensitive dict containing all the headers"""
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
            HTTPHeaders.__logger.debug(f"Found header {key}={value} from {line}")
            result[key] = value
        return result

    def __getitem__(self, item: str) -> str:
        return self.data[item.lower()]

    def __setitem__(self, item: str, value: str) -> None:
        self.data[item.lower()] = value

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key.lower() in self.data


@dataclass
class HTTPPayload:
    """Common fields of an http request and response"""

    __logger = getLogger("laproxy.HTTPPayload")

    @staticmethod
    async def parse_body(reader: StreamReader, n: int, /) -> bytes:
        """Read an http body from a stream reader

        - reader: The stream reader to read the data from
        - n: The length of the body

        - returns: The content of the body"""
        return await reader.readexactly(n)

    @staticmethod
    async def parse_payload(reader: StreamReader, /) -> HTTPPayload:
        """Read the common part of an http request and response from a stream reader

        - reader: The stream reader to read the data from

        - returns: The resulting data"""
        headers = await HTTPHeaders.parse_headers(reader)
        if "Content-Length" not in headers:
            HTTPPayload.__logger.warning("Missing Content-Length header")
        body = await HTTPPayload.parse_body(
            reader, int(headers.get("Content-Length", 0))
        )
        return HTTPPayload(headers, body)

    headers: HTTPHeaders
    """The headers of the http message"""
    body: bytes
    """The content of the body"""

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
    """Fields of an http request"""

    __logger = getLogger("laproxy.HTTPRequest")

    @staticmethod
    async def parse_request(reader: StreamReader, /) -> HTTPRequest | None:
        """Read an http request from a stream reader

        - reader: The stream reader to read the data from

        - returns: The resulting HTTPRequest or None if the end of the stream is reached before starting the reading
        """
        line = (await reader.readline()).decode().strip()
        if not line:
            return None
        match = REQUEST_LINE_RE.match(line)
        if match is None:
            raise MalformedRequestLineException(line)
        method = match.group(1)
        path = match.group(2)
        version = float(match.group(3))
        HTTPRequest.__logger.debug(
            f"Got request line {method} {path} {version} from {line}"
        )
        payload = await HTTPPayload.parse_payload(reader)
        return HTTPRequest(payload.headers, payload.body, method, path, version)

    method: str
    """Method of the request"""
    path: str
    """Path of the resource"""
    version: float
    """HTTP version"""

    def __bytes__(self) -> bytes:
        return (
            f"{self.method} {self.path} HTTP/{self.version}\r\n".encode()
            + super().__bytes__()
        )


@dataclass
class HTTPResponse(HTTPPayload):
    """Fields of an http response"""

    __logger = getLogger("laproxy.HTTPResponse")

    @staticmethod
    async def parse_response(reader: StreamReader, /) -> HTTPResponse | None:
        """Read an http response from a stream reader

        - reader: The stream reader to read the data from

        - returns: The HTTPResponse or None if the end of stream is reached before starting the reading
        """
        line = (await reader.readline()).decode().strip()
        if not line:
            return None
        match = RESPONSE_LINE_RE.match(line)
        if not match:
            raise MalformedResponseLineException(line)
        version = match.group(1)
        code = match.group(2)
        message = match.group(3)
        HTTPResponse.__logger.debug(
            f"Got response line {version} {code} {message} from {line}"
        )
        payload = await HTTPPayload.parse_payload(reader)
        return HTTPResponse(
            payload.headers,
            payload.body,
            float(version),
            int(code),
            message,
        )

    version: float
    """The http version"""
    code: int
    """The status code"""
    message: str
    """The status message"""

    def __bytes__(self) -> bytes:
        return (
            f"HTTP/{self.version} {self.code} {self.message}\r\n".encode()
            + super().__bytes__()
        )


class HTTPHandler(Handler, ABC):
    """Handler of an HTTP connection"""

    __logger = getLogger("laproxy.HTTPHandler")

    @override
    @final
    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        ip, port = get_remote_host(writer)
        while True:
            if inbound:
                HTTPHandler.__logger.debug("Waiting for HTTP request")
                request = await HTTPRequest.parse_request(reader)
                if request is None:
                    HTTPHandler.__logger.debug("End of HTTP requests stream")
                    break
                content = self.request(request)
            else:
                HTTPHandler.__logger.debug("Waiting for HTTP response")
                response = await HTTPResponse.parse_response(reader)
                if response is None:
                    HTTPHandler.__logger.debug("End of HTTP responses stream")
                    break
                content = self.response(response)
            if content is None:
                HTTPHandler.__logger.info(
                    f"Dropping HTTP connection of {ip}:{port}, inbound={inbound}"
                )
                break
            writer.write(bytes(content))
        writer.close()
        await writer.wait_closed()

    @abstractmethod
    def request(self, request: HTTPRequest, /) -> HTTPRequest | None:
        """Process an HTTP request

        - request: The HTTP request to process

        - returns: The modified HTTP request or None if the connection should be closed
        """
        ...

    @abstractmethod
    def response(self, response: HTTPResponse, /) -> HTTPResponse | None:
        """Process an HTTP response

        - request: The HTTP response to process

        - returns: The modified HTTP response or None if the connection should be closed
        """
        ...


class NoHTTPHandler(HTTPHandler):
    """Simple HTTP handler that doesn't modify any message"""

    @override
    @final
    def request(self, request: HTTPRequest, /) -> HTTPRequest | None:
        return request

    @override
    @final
    def response(self, response: HTTPResponse, /) -> HTTPResponse | None:
        return response
