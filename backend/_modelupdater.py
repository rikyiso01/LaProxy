from __future__ import annotations
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.utils._testing import ignore_warnings
from sklearn.exceptions import ConvergenceWarning

from ._basemodel import Point, ClusterModel

class ModelUpdater(ClusterModel):
    """updates the K-means model with the newly recieved data"""

    def __init__(self, dataset : list, centroids : list, blocked : list):
        super(ModelUpdater, self).__init__(dataset, centroids, blocked)

    
    @ignore_warnings(category=ConvergenceWarning)
    def __getNewCentroids(self) -> list[list]:

        k_scores = []
        maxK = min(10, len(self.dataset))
        
        for k in range(1, maxK):    # i really hope there are not gonna be more than 5/6 different kind of attacks per service
            kmeans = KMeans(n_clusters=k, init="k-means++", n_init=3)
            kmeans.fit(self.dataset)

            if len(kmeans.cluster_centers_) == 1:
                k_scores.append((0.0, -k, [list(x) for x in kmeans.cluster_centers_]))     # if n_clusters = 1 -> silhouette = 0
                continue

            silhouette = silhouette_score(self.dataset, kmeans.labels_, metric = 'euclidean')

            k_scores.append((silhouette, -k, [list(x) for x in kmeans.cluster_centers_]))
        
        if len(k_scores) == 0:
            return []

        k_scores.sort()
        return k_scores[-1][2]      # we pick the list with the highest silhouette score
    
    
    def update(self) -> tuple[list, list]:
        """Uses the silhouette coefficient to determine the number of clusters and K-means++ to obtain the best possible centroids.
        It also updates the blocked list using the following logic: for each new cluster, if its centroid was assigned to a blocked 
        cluster then the new cluster is also blocked"""

        new_centroids = self.__getNewCentroids()
        self.centroids = [Point(x) for x in self.centroids]

        new_blocked = []

        i = 0
        for point in new_centroids:
            assigned = self.assign(point)
            if assigned in self.blocked:    # we let blocked be transitive: if a cluster was blocked, the clusters derived from it are as well by default
                new_blocked.append(i)

            i += 1

        return new_centroids, new_blocked

