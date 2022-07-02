from __future__ import annotations
from asyncio import run, StreamWriter, StreamReader
from abc import ABC, abstractmethod


class Proxy:
    def run(self) -> None:
        try:
            run(self.run_async())
        except KeyboardInterrupt:
            pass

    @abstractmethod
    async def run_async(self) -> None:
        ...


class Handler(ABC):
    @abstractmethod
    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        ...
