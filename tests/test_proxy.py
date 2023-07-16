from __future__ import annotations
from laproxy import TCPProxy, NoTCPHandler, NoHTTPHandler
from httpx import AsyncClient, get
from asyncio import sleep as asleep, run, Task
from aiotools import TaskGroup
from sys import executable
from os import environ
from subprocess import Popen, check_call
from time import sleep


async def check(task: Task[None], port: int) -> None:
    async with AsyncClient() as session:
        await asleep(0.1)
        r = await session.get(f"http://127.0.0.1:{port}", follow_redirects=False)
        assert "301 Moved" in r.text
        assert r.status_code == 301
    task.cancel()


def check_http(port: int) -> None:
    sleep(1)
    r = get(f"http://127.0.0.1:{port}", follow_redirects=False)
    assert "301 Moved" in r.text
    assert r.status_code == 301


def check_sample(path: str, port: int) -> None:
    process = Popen([executable, path], env={**environ, "PYTHONPATH": "."})
    check_http(port)
    process.terminate()
    process.wait()


async def test_tcp():
    async with TaskGroup() as group:
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
    async with TaskGroup() as group:
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


def test_httpsample():
    check_sample("samples/httpproxy.py", 8080)


def test_tcpsample():
    check_sample("samples/tcpproxy.py", 5000)


def test_tcplinesample():
    check_sample("samples/tcplineproxy.py", 5001)


def test_docker():
    check_call(["docker", "compose", "-f", "tests/docker-compose.yml", "down"])
    check_call(
        ["docker", "compose", "-f", "tests/docker-compose.yml", "up", "--build", "-d"]
    )
    check_http(1236)
    check_call(["docker", "compose", "-f", "tests/docker-compose.yml", "down"])


if __name__ == "__main__":
    run(test_http())
