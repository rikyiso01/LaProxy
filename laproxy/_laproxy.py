from __future__ import annotations
from asyncio import run, StreamWriter, StreamReader
from abc import ABC, abstractmethod
from logging import INFO, basicConfig, getLogger


class Proxy(ABC):
    """Abstract base class for a proxy"""

    __logger = getLogger("laproxy.Proxy")

    def run(self, *, log_level: int | None = INFO) -> None:
        """Start this proxy.
        This method is blocking.
        Creates an asyncio event loop.
        If an event loop is already running, use run_async()"""
        if log_level is not None:
            basicConfig(level=log_level)
        try:
            Proxy.__logger.debug("Starting event loop")
            run(self.run_async())
        except KeyboardInterrupt:
            Proxy.__logger.debug("Keyboard Interrupt received, stopping server")

    @abstractmethod
    async def run_async(self) -> None:
        """Children should implement this method to provide proxy functionality"""
        ...


class Handler(ABC):
    """Abstract base class for a connection handler.
    A new object will be created for every connection"""

    @abstractmethod
    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        """Manages a connection using asyncio.
        This method will be called 2 times, one with inbound=false and one with inbound=true, per instance

        - reader: input stream
        - writer: output stream
        - inbound: if the connection is coming from the outside to the inside"""
        ...
