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
from typing_extensions import override
from typing import final
from logging import getLogger

from aiotools import TaskGroup

DEFAULT_TCP_BUFFSIZE = 1024


def get_remote_host(writer: StreamWriter) -> tuple[str, int]:
    return writer.transport.get_extra_info("peername")


class TCPHandler(Handler, ABC):
    """Base handler for a tcp connection, useful for TCP packet level processing"""

    __logger = getLogger("laproxy.TCPHandler")

    def buffsize(self) -> int:
        """Size of the buffer to use for the packet data

        - returns: The buffer size"""
        return DEFAULT_TCP_BUFFSIZE

    @override
    @final
    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        ip, port = get_remote_host(writer)
        TCPHandler.__logger.debug(
            f"Starting handling of {ip}:{port}, inbound={inbound}"
        )
        while True:
            TCPHandler.__logger.debug("Waiting for a packet")
            packet = await reader.read(self.buffsize())
            if not packet:
                break
            TCPHandler.__logger.debug(
                f"Starting processing of packet inbound={inbound}"
            )
            packet = self.process(packet, inbound)
            if packet is None:
                TCPHandler.__logger.info(
                    f"Dropping connection of {ip}:{port}, inbound={inbound}"
                )
                break
            TCPHandler.__logger.debug("Sending packet")
            writer.write(packet)

    @abstractmethod
    def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
        """Process a single tcp packet

        - packet: The packet to modify
        - inbound: If the connection is coming from the outside

        - returns: The modified packet or None if the connection should be dropped"""
        ...


class TCPLineHandler(TCPHandler, ABC):
    """TCP line level processing.
    Warning: The connection is flushed only when a \\n is received"""

    __logger = getLogger("laproxy.TCPLineHandler")

    def __init__(self):
        super().__init__()
        self.__inbound_buffer = bytearray()
        self.__outbound_buffer = bytearray()

    @override
    @final
    def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
        buffer = self.__inbound_buffer if inbound else self.__outbound_buffer
        buffer.extend(packet)
        if b"\n" not in buffer:
            TCPLineHandler.__logger.debug("Packet did not contain any new line")
        response = bytearray()
        while (index := buffer.find(b"\n")) != -1:
            content = buffer[: index + 1]
            del buffer[: index + 1]
            new = self.process_line(content, inbound)
            if new is None:
                return None
            response.extend(new)
        return response

    @abstractmethod
    def process_line(self, line: bytes, inbound: bool, /) -> bytes | None:
        """Process a single line

        - line: The line to process
        - inbound: If the connection is coming from the outside

        - returns: The modified line or None if the connection should be dropped"""
        ...


class TCPProxy(Proxy):
    """Proxy that manages tcp connections"""

    __logger = getLogger("laproxy.TCPProxy")

    def __init__(
        self,
        listen_address: str,
        listen_port: int,
        target_address: str,
        target_port: int,
        handler: Callable[[], Handler],
        /,
    ):
        """- listen_address: address to use to accept external connections
        - listen_port: port to use to accept external connections
        - target_address: address to redirect connections to
        - target_port: port to redirect connections to
        - handler: handler's constructor to use to process connections, it will be called each time a new connection is opened
        """
        self.__listen_address = listen_address
        self.__listen_port = listen_port
        self.__target_address = target_address
        self.__target_port = target_port
        self.__handler = handler

    @override
    @final
    async def run_async(self) -> None:
        TCPProxy.__logger.info(
            f"Starting the server on {self.__listen_address}:{self.__listen_port}"
        )
        server = await start_server(
            self.__thread, self.__listen_address, self.__listen_port
        )
        async with server:
            TCPProxy.__logger.info(
                f"Forwarding connections to {self.__target_address}:{self.__target_port}"
            )
            await server.serve_forever()

    async def __thread(self, reader: StreamReader, writer: StreamWriter, /) -> None:
        try:
            target_reader, target_writer = await open_connection(
                self.__target_address, self.__target_port
            )
            ip, port = get_remote_host(writer)
            TCPProxy.__logger.info(f"Received a connection from {ip}:{port}")
            handler = self.__handler()
            async with TaskGroup() as group:
                group.create_task(
                    self.__handle(handler, reader, target_writer, True),
                    name="tcp inbound",
                )
                group.create_task(
                    self.__handle(handler, target_reader, writer, False),
                    name="tcp outbound",
                )
        except GeneratorExit:
            pass
        except:
            TCPProxy.__logger.error(
                "Exception while handling a connection", exc_info=True
            )

    async def __handle(
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
    """Simple tcp handler that doesn't modify any packet"""

    @override
    @final
    def process(self, packet: bytes, _: bool, /) -> bytes | None:
        return packet


class NoTCPLineHandler(TCPLineHandler):
    """Simple tcp line handler that doesn't modify any line"""

    @override
    @final
    def process_line(self, line: bytes, _: bool, /) -> bytes | None:
        return line
