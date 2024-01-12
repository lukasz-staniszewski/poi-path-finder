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
        self.db = DB()

        self.start = self.db.get_nearest_point(start)  # DBPoint
        self.end = self.db.get_nearest_point(end)  # DBPoint
        self.shortest_path, self.shortest_cost = self.db.find_shortest_path_between(self.start, self.end)

        self.max_time = max_time * 60  # to seconds
        self.max_distance = max_distance * 1000  # to meters
        self.max_pois = max_num_pois

        self.shortest_line_a = (self.start.y - self.end.y) / (self.start.x - self.end.x)
        self.shortest_line_b = self.start.y - self.shortest_line_a * self.start.x

        self.curr_path = [self.start]
        self.curr_cost = 0
        self.curr_time = 0
        self.curr_pois = []

        self.last_valid_path_between_next = []

        self.pois_order = pois_order

        self.find_path()

    def find_path(self):
        while len(self.curr_pois) < self.max_pois:
            next_poi = self.select_next_poi()
            if next_poi is None:
                break

        if len(self.last_valid_path_between_next):
            self.curr_path.extend(self.last_valid_path_between_next[:-1])
        else:
            self.curr_path.extend(self.db.find_shortest_path_between(self.curr_path[-1], self.end)[0][:-1])

        self.curr_path.append(self.end)

    def select_next_poi(self):
        pois = self.db.get_valid_points(
            self.curr_path[-1],
            self.max_distance,
            self.max_time,
            self.pois_order[len(self.curr_pois)].visit_time * 60,
            self.pois_order[len(self.curr_pois)].type.lower().replace(" ", "_"),
        )

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
        path_between_prev, cost_between_prev = self.db.find_shortest_path_between(
            self.curr_path[-1], new_point
        )
        path_between_next, cost_between_next = self.db.find_shortest_path_between(new_point, self.end)

        if path_between_prev is None or path_between_next is None:
            return False

        curr_total_cost = self.curr_cost + cost_between_prev + cost_between_next
        curr_additional_distance = curr_total_cost - self.shortest_cost
        curr_additional_time = curr_additional_distance / VELOCITY
        print(f"curr_additional_distance: {curr_additional_distance}m")
        print(f"curr_additional_time: {curr_additional_time}s")

        if curr_additional_distance > self.max_distance or curr_additional_time > self.max_time:
            return False
        else:
            self.curr_path.extend(path_between_prev[:-1] + [new_point])
            self.curr_cost += cost_between_prev
            self.curr_time += cost_between_prev / VELOCITY
            self.last_valid_path_between_next = path_between_next
            self.max_distance -= curr_additional_distance
            self.max_time -= curr_additional_time
            self.curr_pois.append((new_point, self.pois_order[len(self.curr_pois)].visit_time, self.pois_order[len(self.curr_pois)].type))
            return True

    def calculate_heuristic(self, new_point: DBPoint):
        a = self.dist_from_shortest_line(new_point)
        b = self.dist_between_points(new_point, self.end)
        H = ALPHA * a + BETA * b
        return H

    def dist_from_shortest_line(self, point: DBPoint):
        return (
            abs(self.shortest_line_a * point.x - point.y + self.shortest_line_b)
            / (self.shortest_line_a**2 + 1) ** 0.5
        )

    def dist_between_points(self, proposed_point: DBPoint, relative_point: DBPoint = None):
        if relative_point is None:
            relative_point = self.curr_path[-1]
        return ((relative_point.x - proposed_point.x) ** 2 + (relative_point.y - proposed_point.y) ** 2) ** 0.5
