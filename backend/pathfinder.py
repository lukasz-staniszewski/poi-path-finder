from backend.db import DB, DBPoint
from backend.api.schemas import POI, MapPoint
from backend.constants import VELOCITY, ALPHA, BETA
from typing import List


class PathFinder:
    def __init__(
        self,
        start: MapPoint,
        end: MapPoint,
        max_time: float,
        max_distance: float,
        max_num_pois: int,
        pois_order: List[POI],
    ):
        """
        Initializes a PathFinder object.

        Args:
            start (MapPoint): The starting point of the path.
            end (MapPoint): The ending point of the path.
            max_time (float): The maximum time allowed to add to  the path in minutes.
            max_distance (float): The maximum distance allowed to add to the path in kilometers.
            max_num_pois (int): The maximum number of Points of Interest (POIs) to visit.
        """
        self.db = DB()

        # At first find the start and end point in the database
        self.start = self.db.get_nearest_point(start)  # DBPoint
        self.end = self.db.get_nearest_point(end)  # DBPoint
        # Then find the shortest path between them
        self.shortest_path, self.shortest_cost = self.db.find_shortest_path_between(self.start, self.end)

        self.max_time = max_time * 60  # to seconds
        self.max_distance = max_distance * 1000  # to meters
        self.max_pois = max_num_pois

        self.shortest_line_a = (self.start.y - self.end.y) / (self.start.x - self.end.x)
        self.shortest_line_b = self.start.y - self.shortest_line_a * self.start.x

        self.curr_path = [self.start]
        self.curr_cost = 0
        self.curr_additional_distance = 0
        self.curr_additional_time = 0
        self.curr_time = 0
        self.curr_pois = []

        self.last_valid_path_between_next = []

        self.pois_order = pois_order

        self.find_path()

    def find_path(self):
        """
        Finds the optimal path by selecting the next POI to visit until the maximum number of POIs is reached.
        """
        while len(self.curr_pois) < self.max_pois:
            next_poi = self.select_next_poi()
            if next_poi is None:
                break

        if len(self.last_valid_path_between_next):
            self.curr_path.extend(self.last_valid_path_between_next[:-1])
            self.curr_cost += self.last_valid_cost_between_next
            self.curr_time += self.last_valid_cost_between_next / VELOCITY
        else:
            self.curr_path = self.shortest_path[:-1]
            self.curr_cost = self.shortest_cost
            self.curr_time = self.shortest_cost / VELOCITY

        self.curr_path.append(self.end)

    def select_next_poi(self):
        """
        Selects the next Point of Interest (POI) to visit.

        Returns:
            next_poi (POI): The next POI to visit.
        """
        # List of POI candidates
        pois = self.db.get_valid_points(
            self.curr_path[-1],
            self.max_distance,
            self.max_time,
            self.pois_order[len(self.curr_pois)].visit_time * 60,
            self.pois_order[len(self.curr_pois)].type.lower().replace(" ", "_"),
        )

        # Find the POI with the lowest heuristic
        lowest_heuristic = float("inf")
        next_poi = None

        if pois:
            for poi in pois:
                if poi not in self.curr_path:
                    heuristic = self.calculate_heuristic(poi)
                    if heuristic < lowest_heuristic:
                        lowest_heuristic = heuristic
                        next_poi = poi
        if not next_poi or not self.update_path(next_poi):
            return None

        return next_poi

    def update_path(self, new_point: DBPoint):
        """
        Updates the current path with a new point.

        Args:
            new_point (DBPoint): The new point to be added to the path.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        # Find the shortest path between the last point in the current path and POI
        path_between_prev, cost_between_prev = self.db.find_shortest_path_between(
            self.curr_path[-1], new_point
        )
        # Find the shortest path between POI and the end
        path_between_next, cost_between_next = self.db.find_shortest_path_between(new_point, self.end)

        if path_between_prev is None or path_between_next is None:
            return False

        curr_total_cost = self.curr_cost + cost_between_prev + cost_between_next
        curr_additional_distance = curr_total_cost - self.shortest_cost
        curr_additional_time = curr_additional_distance / VELOCITY
        print(f"curr_additional_distance: {curr_additional_distance}m")
        print(f"curr_additional_time: {curr_additional_time}s")
        print(f"{self.max_distance}m")
        print(f"{self.max_time}s")

        if curr_additional_distance > self.max_distance or curr_additional_time > self.max_time:
            print("Restrictions violated")
            # Restrictions violated
            return False
        else:
            # Add POI to the current path and update the current cost and time
            self.curr_path.extend(path_between_prev[:-1] + [new_point])
            self.curr_cost += cost_between_prev
            self.curr_time += cost_between_prev / VELOCITY
            self.last_valid_path_between_next = path_between_next
            self.last_valid_cost_between_next = cost_between_next
            self.max_distance = max(0, self.max_distance - curr_additional_distance)
            self.max_time = max(0, self.max_time - curr_additional_time)
            self.curr_additional_distance = curr_additional_distance
            self.curr_additional_time = curr_additional_time
            self.curr_pois.append(
                (
                    new_point,
                    self.pois_order[len(self.curr_pois)].visit_time,
                    self.pois_order[len(self.curr_pois)].type,
                    self.curr_cost,
                    self.curr_time,
                )
            )
            return True

    def calculate_heuristic(self, new_point: DBPoint):
        """
        Calculates the heuristic value for a given POI.

        Args:
            new_point (DBPoint): The POI for which the heuristic value is calculated.

        Returns:
            float: The heuristic value for the POI.
        """
        a = self.dist_from_shortest_line(new_point)
        b = self.dist_between_points(new_point, self.end)
        H = ALPHA * a + BETA * b
        return H

    def dist_from_shortest_line(self, point: DBPoint):
        """
        Calculates the perpendicular distance from a given point to the shortest line.

        Args:
            point (DBPoint): The point for which the distance is calculated.

        Returns:
            float: The perpendicular distance from the point to the shortest line.
        """
        return (
            abs(self.shortest_line_a * point.x - point.y + self.shortest_line_b)
            / (self.shortest_line_a**2 + 1) ** 0.5
        )

    def dist_between_points(self, proposed_point: DBPoint, relative_point: DBPoint = None):
        """
        Calculates the Euclidean distance between two points.

        Args:
            proposed_point (DBPoint): The point for which the distance is calculated.
            relative_point (DBPoint, optional): The reference point. If not provided, the last point in the current path is used.

        Returns:
            float: The Euclidean distance between the two points.
        """
        if relative_point is None:
            relative_point = self.curr_path[-1]
        return (
            (relative_point.x - proposed_point.x) ** 2 + (relative_point.y - proposed_point.y) ** 2
        ) ** 0.5
