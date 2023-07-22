from __future__ import annotations
from asyncio import (
    StreamReader,
    StreamWriter,
    run,
    sleep,
    start_server,
    wait_for,
)

from aiotools import TaskGroup
from aioconsole import get_standard_streams             #remember to pip install aioconsole

from ._modelupdater import ModelUpdater
from ._servicehandler import ServiceHandler

DEFAULT_TCP_BUFFSIZE = 1024

MENU_STRING = '''\nCurrent Service: %s \t N. Clusters: %d \t Mode: %s \t Blocked: %s\nAvailable Options:\n
 - CHECK_EXAMPLES\n - SET_MODE [ACTIVE_MODE/SIMULATION_MODE]\n - SET_BLOCKED <list>\n - SET_SERVICE <port>\n - SHUT_DOWN\n\n> '''

async def display_menu(backend: Backend):
    """Function that displays a minimalistic menu to interact with the user"""
    current_service = ""
    stdin: StreamReader 
    stdin, _ = await get_standard_streams()

    while True:
        serv = backend.services.get(current_service, None)
        if serv is None:
            print(MENU_STRING % ("", 0, "", ""), end="")
        else:
            print(MENU_STRING % (current_service, len(serv.centroids), serv.mode, str(serv.blocked)), end="")

        cmd = await stdin.read(44)
        cmd = cmd.decode("ascii").strip("\n")

        cmd_args = cmd.split(" ")

        if cmd_args[0] == "SET_SERVICE":
            service = cmd_args[1]
            if not service in backend.services.keys():
                backend.services[service] = ServiceHandler(service)
            current_service = service

        elif not current_service:
            print("Please set a service first")

        elif cmd_args[0] == "SET_MODE":
            backend.services[current_service].mode = cmd_args[1]

        elif cmd_args[0] == "SET_BLOCKED":
            blocked_raw = cmd[12:].replace(" ", "")[1:-1].split(",")
            blocked = [int(x) for x in blocked_raw if len(x) > 0]
            backend.services[current_service].blocked = blocked

        elif cmd_args[0] == "CHECK_EXAMPLES":
            print("")
            for i, example in enumerate(backend.services[current_service].examples):
                if i in backend.services[current_service].blocked: print(f"[BLOCKED] {example}")
                else: print(f"[ALLOWED] {example}")
        else:
            print("Unknown command")
    
class Backend:
    """Class that handles the connections from the proxies which request updates"""

    def __init__(self, port: int):
        self.__port = port
        self.services: dict[str, ServiceHandler] = {}


    async def run_async(self) -> None:
        """Inserts in the asyncio loop the tasks to display the menu, handle the incoming connections and update the models"""
        server = await start_server(self.__thread, "0.0.0.0", self.__port)

        async with TaskGroup() as group:

            group.create_task(
                display_menu(self),
                name="menu",
            )
            group.create_task(
                server.serve_forever(),
                name="update requests",
            )
            group.create_task(
                self.__update_models(),
                name="models updater"
            )

    
    async def __update_models(self) -> None:

        while True:
            print("\n\nupdating ended\n\n>", end="")
            await sleep(45)
            print("\n\nWarning: updating started\n\n>", end="")
            for s in self.services.keys():
                service = self.services[s]

                points = service.getPoints()
                if len(points) == 0:
                    continue

                #print(points)
                model_updater = ModelUpdater(points, service.centroids, service.blocked)

                service.centroids, service.blocked = model_updater.update()
                service.updateExamples(points)
                

    async def __thread(self, reader: StreamReader, writer: StreamWriter, /) -> None:
        
        just_read: bytes
        just_read_len = DEFAULT_TCP_BUFFSIZE
        new_data: str = ""
        data_args: list[str]
        try:
            while just_read_len == DEFAULT_TCP_BUFFSIZE:
                just_read = await wait_for(reader.read(DEFAULT_TCP_BUFFSIZE), timeout=60)
                new_data += just_read.decode("ascii")
                just_read_len = len(just_read)

            data_args = new_data.strip().split(" # ")
            if data_args[0] != "UPDATE" or len(data_args) < 3:
                raise ConnectionError
        
        except (UnicodeDecodeError, ConnectionError, TimeoutError):
            writer.close()
            await writer.wait_closed()
            return
    
        service = data_args[1]
        if not service in self.services.keys():
            self.services[service] = ServiceHandler(service)

        response = f"{self.services[service].centroids} # {self.services[service].mode} # {self.services[service].blocked}"
        writer.write(response.encode())
        await writer.drain()

        self.services[service].updateFiles(data_args[2])

        writer.close()
        await writer.wait_closed()


        
def main(port: int):
    backend = Backend(port)
    try:
        print("Starting event loop...\n")
        run(backend.run_async())

    except KeyboardInterrupt:
        print("Keyboard Interrupt received, exiting...")



    