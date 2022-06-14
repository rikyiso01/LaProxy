from asyncio import run, StreamWriter, StreamReader
from abc import ABC, abstractmethod


class Proxy:
    def run(self) -> None:
        try:
            run(self._run())
        except KeyboardInterrupt:
            pass

    @abstractmethod
    async def _run(self) -> None:
        ...


class Handler(ABC):
    @abstractmethod
    async def handle(
        self, reader: StreamReader, writer: StreamWriter, inbound: bool, /
    ) -> None:
        ...
