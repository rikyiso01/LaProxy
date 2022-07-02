from __future__ import annotations
from asyncio import StreamReader, StreamWriter
from abc import ABC, abstractmethod
from ._laproxy import Handler


class HTTPPayload:
    @staticmethod
    async def parse_headers(reader: StreamReader, /) -> dict[str, str]:
        result: dict[str, str] = {}
        while True:
            line = (await reader.readline()).strip()
            if not line:
                break
            key, value = line.decode().split(": ")
            result[key] = value
        return result

    @staticmethod
    async def parse_body(reader: StreamReader, n: int, /) -> bytes:
        return await reader.readexactly(n)

    @staticmethod
    async def parse_payload(reader: StreamReader, /) -> HTTPPayload:
        headers = await HTTPPayload.parse_headers(reader)
        body = b""
        if "Content-Length" in headers:
            body = await HTTPPayload.parse_body(reader, int(headers["Content-Length"]))
        return HTTPPayload(headers, body)

    def __init__(self, headers: dict[str, str], body: bytes, /):
        self._headers = headers
        self._body = body

    @property
    def body(self) -> bytes:
        return self._body

    def __getitem__(self, item: str, /) -> str:
        return self._headers[item]

    def headers(self) -> dict[str, str]:
        return self._headers.copy()

    def __bytes__(self) -> bytes:
        result = bytearray()
        for key, value in self._headers.items():
            result.extend(f"{key}: {value}\r\n".encode())
        result.extend(b"\r\n")
        if self._body:
            result.extend(self._body)
        return bytes(result)


class HTTPRequest(HTTPPayload):
    @staticmethod
    async def parse_request(reader: StreamReader, /) -> HTTPRequest | None:
        line = await reader.readline()
        if not line:
            return None
        method, path, version = line.strip().decode().split(" ")
        return HTTPRequest(
            method, path, version, await HTTPPayload.parse_payload(reader)
        )

    def __init__(self, method: str, path: str, version: str, payload: HTTPPayload, /):
        super().__init__(payload.headers(), payload.body)
        self._version = version
        self._method = method
        self._path = path

    @property
    def version(self) -> str:
        return self._version

    @property
    def method(self) -> str:
        return self._method

    @property
    def path(self) -> str:
        return self._path

    def __bytes__(self) -> bytes:
        return (
            f"{self._method} {self._path} {self._version}\r\n".encode()
            + super().__bytes__()
        )


class HTTPResponse(HTTPPayload):
    @staticmethod
    async def parse_response(reader: StreamReader, /) -> HTTPResponse | None:
        line = await reader.readline()
        if not line:
            return None
        version, code, *message = line.strip().decode().split(" ")
        return HTTPResponse(
            version,
            int(code),
            " ".join(message),
            await HTTPPayload.parse_payload(reader),
        )

    def __init__(self, version: str, code: int, message: str, payload: HTTPPayload, /):
        super().__init__(payload.headers(), payload.body)
        self._version = version
        self._code = code
        self._message = message

    @property
    def version(self) -> str:
        return self._version

    @property
    def code(self) -> int:
        return self._code

    @property
    def message(self) -> str:
        return self._message

    def __bytes__(self) -> bytes:
        return (
            f"{self._version} {self._code} {self._message}\r\n".encode()
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
