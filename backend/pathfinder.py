class Pathfinder:
    def __init__(self, database):
        self.database = database

    def find_path(self, start_point, end_point, pois):
        path = [start_point]
        current_point = start_point

        while current_point != end_point:
            next_poi = self.select_next_poi(current_point, pois)
            path.append(next_poi)
            current_point = next_poi

        return path

    def select_next_poi(self, current_point, pois):
        lowest_heuristic = float('inf')
        next_poi = None

        for poi in pois:
            heuristic = self.calculate_heuristic(current_point, poi)
            if heuristic < lowest_heuristic:
                lowest_heuristic = heuristic
                next_poi = poi

        return next_poi

    def calculate_heuristic(self, point1, point2):
        # Implement your heuristic calculation logic here
        pass
