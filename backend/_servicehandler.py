import os
from base64 import b64decode
from ._basemodel import Point, ClusterModel

MAX_CHUNK_SIZE = 2500

def reverse_readline(filename: str, buf_size=8192):      # ty StackOverflow <3
    """A generator that returns the lines of a file in reverse order"""
    with open(filename, 'rb') as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size)).decode(encoding='utf-8')
            remaining_size -= buf_size
            lines = buffer.split('\n')
            if segment is not None:
                if buffer[-1] != '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if lines[index]:
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


class ServiceHandler:
    """A class to manage services info (such as N. of clusters, example of points, blocked clusters...)
    and the files that store such info"""

    def __init__(self, service_id: str):
        self.id = service_id
        self.centroids: list[list[float]] = []
        self.examples: list[list[bytes]] = []
        self.blocked: list[int] = []
        self.mode: str = "SIMULATION_MODE"
        create_file_if_doesnt_exist = open(f"{service_id}-points.txt", "a")
        create_file_if_doesnt_exist.close()
        create_file_if_doesnt_exist = open(f"{service_id}-convs.txt", "a")
        create_file_if_doesnt_exist.close()


    def getPoints(self) -> list[list]:
        """Gets up to MAX_CHUNK_SIZE points from the points file of the service (giving priority to the most recent ones)"""
        read_lines = 0
        points = []
        
        try:
            for line in reverse_readline(f"{self.id}-points.txt"):
                raw_data = line.strip("\n")[1:-1].split(", ")
                points.append([float(x) for x in raw_data if len(x) > 0])

                read_lines += 1
                if read_lines >= MAX_CHUNK_SIZE:
                    break

        finally:
            return points
        
        
    def updateExamples(self, points: list[list]) -> None:
        """Gets the most recent conversation example for each cluster from the convs file of the service"""

        missing_examples: list[int] = [x for x in range(len(self.centroids))]
        examples_n: list[tuple] = []
        examples: list[str] = ["" for _ in self.centroids]
        assigner = ClusterModel([], [Point(x) for x in self.centroids], [])  # we only need the assign method of ClusterModel

        i = 0
        for p in points:
            example_n = assigner.assign(p)
            if example_n in missing_examples:
                missing_examples.remove(example_n)
                examples_n.append((i, example_n))

            if len(missing_examples) == 0:
                break

            i += 1

        read_lines = 0
        try:
            for line in reverse_readline(f"{self.id}-convs.txt"):
                raw_data = line.strip("\n")

                if read_lines == examples_n[0][0]:
                    examples[examples_n[0][1]] = raw_data
                    examples_n.pop(0)
                
                if len(examples_n) == 0:
                    break

                read_lines += 1
                if read_lines >= MAX_CHUNK_SIZE: # this one should never occur
                    break

        finally:
            self.examples = examples
        

    def updateFiles(self, data_conv: str) -> None:
        """Inserts into points and convs files the data recieved from the last update request of the corresponding service proxy"""
        data_conv = data_conv.strip()[3:-3]

        if len(data_conv) <= 0: return
        
        convs = data_conv.split("'], ['")
        points = []

        for i in range(len(convs)):
            convs[i] = [b64decode(x) for x in convs[i].split("', '")]
            points.append(ClusterModel.packetsToPoint(convs[i]))

        with open(f"{self.id}-points.txt", "a") as pointsfile:
            for p in points: pointsfile.write(str(Point.listify(p)) + "\n")
        
        with open(f"{self.id}-convs.txt", "a") as convsfile:
            for c in convs: convsfile.write(str(c) + "\n")