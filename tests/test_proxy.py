from __future__ import annotations
from laproxy import TCPProxy, NoTCPHandler, NoHTTPHandler
from aiohttp import ClientSession
from asyncio import CancelledError, Future, sleep, run, ensure_future


async def check(future: Future[None], port: int) -> None:
    async with ClientSession() as session:
        while True:
            await sleep(0.1)
            try:
                r = await session.get(f"http://127.0.0.1:{port}", allow_redirects=False)
            except:
                continue
            assert "301 Moved" in await r.text()
            assert r.status == 301
            break
    future.cancel()
    try:
        await future
    except CancelledError:
        pass


async def test_tcp():
    future = ensure_future(
        TCPProxy("0.0.0.0", 1234, "www.google.com", 80, NoTCPHandler).run_async()
    )
    await check(future, 1234)


async def test_http():
    future = ensure_future(
        TCPProxy("0.0.0.0", 1235, "www.google.com", 80, NoHTTPHandler).run_async()
    )
    await check(future, 1235)


if __name__ == "__main__":
    run(test_http())
