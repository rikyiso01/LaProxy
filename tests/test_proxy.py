from __future__ import annotations
from laproxy import TCPProxy, NoTCPHandler, NoHTTPHandler
from httpx import AsyncClient
from asyncio import sleep, run, Task
from aiotools import TaskGroup  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import TaskGroup as TG


async def check(task: Task[None], port: int) -> None:
    async with AsyncClient() as session:
        await sleep(0.1)
        r = await session.get(f"http://127.0.0.1:{port}", follow_redirects=False)
        assert "301 Moved" in r.text
        assert r.status_code == 301
    task.cancel()


async def test_tcp():
    group: TG
    async with TaskGroup() as group:  # type: ignore
        task = group.create_task(
            TCPProxy(
                "0.0.0.0",
                1234,
                "www.google.com",
                80,
                NoTCPHandler,
            ).run_async(),
            name="proxy",
        )
        group.create_task(check(task, 1234), name="client")


async def test_http():
    group: TG
    async with TaskGroup() as group:  # type: ignore
        task = group.create_task(
            TCPProxy(
                "0.0.0.0",
                1235,
                "www.google.com",
                80,
                NoHTTPHandler,
            ).run_async(),
            name="proxy",
        )
        group.create_task(check(task, 1235), name="client")


if __name__ == "__main__":
    run(test_http())
