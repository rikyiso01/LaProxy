from __future__ import annotations
from math import sqrt

MAX_POINT_DIMENSIONS = 16
MAX_PACKET_SIZE = 250

class Point:
    """Point class used for the model, each Point has dimensionality = 2 * 16 = 32"""

    def __init__(self, values: list[float] = []):
        
        self.lengths: list[float] = [0.0] * MAX_POINT_DIMENSIONS
        self.sussyness: list[float] = [0.0] * MAX_POINT_DIMENSIONS
            
        if len(values) == 0:
            return
        try:
            for x in range(MAX_POINT_DIMENSIONS):
                self.lengths[x] = values[x]
            for y in range(MAX_POINT_DIMENSIONS):
                self.sussyness[y] = values[MAX_POINT_DIMENSIONS + y]
        except:
            print("values list is too short, adding zeroes")
            return
        
    def getDistance(self, otherPoint) -> float:   
        """Returns euclidean distance from two Points (or a Point and a list representing a Point)"""
        lenDist = 0.0
        susDist = 0.0
        if isinstance(otherPoint, Point):

            for x in range(MAX_POINT_DIMENSIONS):
                lenDist += (self.lengths[x] - otherPoint.lengths[x])**2
                susDist += (self.sussyness[x] - otherPoint.sussyness[x])**2

        elif isinstance(otherPoint, list):

            for x in range(MAX_POINT_DIMENSIONS):
                lenDist += (self.lengths[x] - otherPoint[x])**2
                susDist += (self.sussyness[x] - otherPoint[x + MAX_POINT_DIMENSIONS])**2
            
        return sqrt(lenDist + susDist)
        
    def listify(self) -> list:
        """Converts Point to list"""
        return list(self.lengths + self.sussyness)


class ClusterModel:
    """General purpuse K-means model class. 
    It is extended into an assigner inside the proxy and into a model updater inside the backend"""

    def __init__(self, dataset : list, centroids : list, blocked : list):

        self.dataset = dataset
        self.centroids = centroids
        self.blocked = blocked


    def assign(self, newPoint: Point | list[float]) -> int:
        """Assigns the Point to the closest current centroid (and returns the centroid id)"""
        min_dist = 1e10
        min_i = -1
        i = 0
        current_centroids = self.centroids
        for centroid in current_centroids:
            dist = Point.getDistance(centroid, newPoint)
            if dist < min_dist:
                min_dist = dist
                min_i = i
            i += 1

        return min_i
    
    
    @staticmethod
    def packetsToPoint(packets: list[bytes]) -> Point:
        """Converts a packets list into a point: 
        each dimension of the point keeps track either of the (normalized) length of the message 
        or of the percentage of non alphanumeric characters it contains"""
        global MAX_PACKET_SIZE, MAX_POINT_DIMENSIONS
        newPoint = Point()
        i = 0
        packets = packets[-MAX_POINT_DIMENSIONS:]  #we take only the last n packages, in order to not be vulnerable to spam-attacks
        for p in packets:
            if len(p) == 0:
                continue
            lp = len(p)
            not_sus = sum([(c <= 57 and c >= 48) or (c | 32 <= 122 and c | 32 >= 97) or c in [9, 10, 32, 46, 64] for c in p])
            sus = lp - not_sus

            newPoint.lengths[i] = ((lp + 5) / (MAX_PACKET_SIZE + 5))
            newPoint.sussyness[i] = (sus / lp)
            i += 1
            if i >= MAX_POINT_DIMENSIONS:
                break

        return newPoint