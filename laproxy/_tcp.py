from __future__ import annotations
from asyncio import StreamReader, StreamWriter, start_server, open_connection, gather
from ._laproxy import Handler, Proxy
from abc import ABC, abstractmethod
from collections.abc import Callable
from traceback import print_exc


class TCPHandler(Handler, ABC):
    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        while True:
            packet = await reader.read(1024)
            if not packet:
                break
            packet = self.process(packet, inbound)
            if packet is None:
                break
            writer.write(packet)

    @abstractmethod
    def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
        ...


class TCPProxy(Proxy):
    def __init__(
        self,
        listen_address: str,
        listen_port: int,
        target_address: str,
        target_port: int,
        handler: Callable[[], Handler],
        /,
    ):
        self._listen_address = listen_address
        self._listen_port = listen_port
        self._target_address = target_address
        self._target_port = target_port
        self._handler = handler

    async def run_async(self) -> None:
        server = await start_server(
            self._thread, self._listen_address, self._listen_port
        )
        async with server:
            await server.serve_forever()

    async def _thread(self, reader: StreamReader, writer: StreamWriter, /) -> None:
        target_reader, target_writer = await open_connection(
            self._target_address, self._target_port
        )
        handler = self._handler()
        await gather(
            self._handle(handler, reader, target_writer, True),
            self._handle(handler, target_reader, writer, False),
        )

    async def _handle(
        self,
        handler: Handler,
        reader: StreamReader,
        writer: StreamWriter,
        inbound: bool,
        /,
    ) -> None:
        try:
            await handler.handle(reader, writer, inbound)
        except BaseException as e:
            if not isinstance(e, GeneratorExit):
                print_exc()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except BaseException as e:
                if not isinstance(e, RuntimeError):
                    print_exc()


class NoTCPHandler(TCPHandler):
    def process(self, packet: bytes, _: bool, /) -> bytes | None:
        return packet
