from __future__ import annotations
from asyncio import (
    StreamReader,
    StreamWriter,
    start_server,
    open_connection,
)
from ._laproxy import Handler, Proxy
from abc import ABC, abstractmethod
from collections.abc import Callable
from aiotools import TaskGroup  # type: ignore
from typing import TYPE_CHECKING
from traceback import print_exc

if TYPE_CHECKING:
    from asyncio import TaskGroup as TG

DEFAULT_TCP_BUFFSIZE = 1024


class TCPHandler(Handler, ABC):
    def buffsize(self) -> int:
        return DEFAULT_TCP_BUFFSIZE

    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        while True:
            packet = await reader.read(self.buffsize())
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
        try:
            target_reader, target_writer = await open_connection(
                self._target_address, self._target_port
            )
            handler = self._handler()
            group: TG
            async with TaskGroup() as group:  # type: ignore
                group.create_task(
                    self._handle(handler, reader, target_writer, True),
                    name="tcp inbound",
                )
                group.create_task(
                    self._handle(handler, target_reader, writer, False),
                    name="tcp outbound",
                )
        except GeneratorExit:
            pass
        except:
            print_exc()

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
        finally:
            writer.close()
            await writer.wait_closed()


class NoTCPHandler(TCPHandler):
    def process(self, packet: bytes, _: bool, /) -> bytes | None:
        return packet
