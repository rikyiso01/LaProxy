from __future__ import annotations

from asyncio import (
    StreamReader,
    StreamWriter,
    open_connection,
    sleep,
    wait_for,
)
from base64 import b64encode
from logging import getLogger
from ._basemodel import ClusterModel, Point

DEFAULT_TCP_BUFFSIZE = 1024

    
class Judge(ClusterModel):
    """Class that uses a K-Means model to assign points (=connections) to cluster. 
    Its verdict is to kill the connection if the corresponding point is in a 'blocked' cluster and simulation_mode is set to False"""

    __logging = getLogger("laproxy.Judge")

    def __init__(self, updater_ip, updater_port):
        super(Judge, self).__init__([], [], [])

        self.__updater_ip = updater_ip
        self.__updater_port = updater_port
        self.__simulation_mode = True


    def verdict(self, packets: list) -> bool:
        """Uses centroids got from backend to check wether the connection belonged to a 'blocked' cluster"""
        self.dataset.append(packets)

        if self.__simulation_mode:
            return True

        newPoint = ClusterModel.packetsToPoint(packets)
        assigned = self.assign(newPoint)

        if assigned in self.blocked:
            Judge.__logging.info(f"blocking an attack")
            return False
        
        return True
    
    
    def __export_dataset(self):
        return [[b64encode(packet).decode("ascii") for packet in interaction] for interaction in self.dataset]
    
    
    def __update(self, newdata: list[str]) -> None:

        centroids_data = newdata[0].strip()[2:-2].split("], [") # first section --- collecting centroids 

        new_centroids = []
        for string in centroids_data:
            pdata = [float(x) for x in string.split(", ") if len(x) > 0]
            new_centroids.append(Point(pdata))

        sim_mode = newdata[1].strip() # second section --- getting operating mode

        new_blocked = []    # third section --- checking blocked clusters 
        if len(newdata) >= 3:
            blocked_data = newdata[2].strip()[1:-1].split(", ")
            new_blocked = [int(x) for x in blocked_data if len(x) > 0]

        self.centroids = new_centroids
        self.blocked = new_blocked
        self.__simulation_mode = sim_mode != "ACTIVE_MODE"
        
    
    async def start_updating(self, proxy_ext_port: int) -> None:
        """Every 40 seconds, a, update request for new centroids is sent to the backend. 
        The request also contains the recently collected data so that the backend can update itself as well
        the parameter: proxy_ext_port is used as an identifier for the service"""
        while True:
            await sleep(40)
            try:
                updater_reader, updater_writer = await open_connection(
                    self.__updater_ip, self.__updater_port
                )
                
                Judge.__logging.info(f"Sending update request to {self.__updater_ip}:{self.__updater_port}")
                command = f"UPDATE # {proxy_ext_port} # {self.__export_dataset()}"
                self.dataset = []

                updater_writer.write(command.encode())
                await updater_writer.drain()

                just_read: bytes
                just_read_len = DEFAULT_TCP_BUFFSIZE
                new_data: str = ""
                try:
                    while just_read_len == DEFAULT_TCP_BUFFSIZE:
                        just_read = await wait_for(updater_reader.read(DEFAULT_TCP_BUFFSIZE), timeout=60)
                        new_data += just_read.decode("ascii")
                        just_read_len = len(just_read)

                except (UnicodeDecodeError, TimeoutError) as e:
                    Judge.__logging.info(f"Closing connection for {type(e).__name__}")
                    raise e

                data = new_data.strip().split(" # ")
                if not data[0] or data[0] == "[]" or len(data) < 2:
                    Judge.__logging.info(f"Recieved empty data")
                    continue    # no update

                self.__update(data)

            finally:
                updater_writer.close()
                await updater_writer.wait_closed()




