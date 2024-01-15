import os
from typing import List, Optional, Tuple

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from backend.constants import (
    INIT_BUFFER_DIJKSTRA,
    INIT_BUFFER_RADIUS,
    MAX_BUFFER_RADIUS,
    VELOCITY,
)

load_dotenv()

ROAD_TYPES = [
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "motorway_link",
    "trunk_link",
    "primary_link",
    "secondary_link",
    "tertiary_link",
]


class DBPoint:
    """
    Represents a point in the database.

    Attributes:
        id (int): The ID of the point.
        x (float): The x-coordinate of the point.
        y (float): The y-coordinate of the point.
    """

    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y

    def __eq__(self, other):
        if isinstance(other, DBPoint):
            return self.id == other.id
        return False

    def __repr__(self):
        return f"DBPoint(id={self.id}, x={self.x}, y={self.y})"


class DB:
    """
    Represents a database connection and provides methods for querying and manipulating data.

    Attributes:
        _engine (sqlalchemy.engine.Engine): The database engine used for the connection.

    Methods:
        get_point_by_id(id: int) -> DBPoint:
            Retrieves a point from the database based on its ID.

        get_nearest_point(point: DBPoint) -> Optional[DBPoint]:
            Retrieves the nearest point to the given point from the database.

        find_shortest_path_between(A: DBPoint, B: DBPoint) -> Optional[Tuple[List[DBPoint], float]]:
            Finds the shortest path between two points using the Dijkstra algorithm.

        _find_nearest_source(start: DBPoint, end: DBPoint) -> int:
            Finds the nearest source of the road to the given start and end points.

        _find_nearest_target(end: DBPoint) -> int:
            Finds the nearest target of the road to the given end point.

        get_valid_points(point: DBPoint, max_distance: float, max_time: float, min_time: float, amenity: str) -> List[DBPoint]:
            Retrieves a list of valid points based on the given criteria.
    """

    def __init__(self) -> None:
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self._engine = create_engine(url)

    def get_point_by_id(self, id: int) -> DBPoint:
        query = f"""
        SELECT *
        FROM planet_osm_point
        WHERE osm_id = {id};
        """
        gdf = gpd.GeoDataFrame.from_postgis(
            query,
            self._engine,
            geom_col="way",
        ).to_crs("EPSG:4326")
        return DBPoint(gdf.index[0], gdf.iloc[0].way.x, gdf.iloc[0].way.y)

    def get_nearest_point(self, point: DBPoint) -> Optional[DBPoint]:
        """
        Retrieves the nearest point to the given point from the database.

        Args:
            point (DBPoint): The point to find the nearest point to.

        Returns:
            Optional[DBPoint]: The nearest point as a DBPoint object, or None if no point is found.
        """
        curr_radius = INIT_BUFFER_RADIUS
        gdf = None
        while (curr_radius < MAX_BUFFER_RADIUS) and (gdf is None or gdf.shape[0] == 0):
            query = f"""
            WITH nearest_point AS (
                SELECT *, ST_Distance(ST_Transform(way, 4326), ST_SetSRID(ST_MakePoint({point.x}, {point.y}), 4326)) AS distance
                FROM planet_osm_point
                WHERE ST_DWithin(ST_Transform(way, 4326), ST_SetSRID(ST_MakePoint({point.x}, {point.y}), 4326), {curr_radius})
                ORDER BY distance ASC
                LIMIT 1
            )
            SELECT * FROM nearest_point;
            """
            gdf = gpd.GeoDataFrame.from_postgis(
                query,
                self._engine,
                geom_col="way",
                index_col="osm_id",
            )
            curr_radius *= 2
        if not len(gdf):
            return None
        gdf = gdf.to_crs("EPSG:4326")
        return DBPoint(gdf.index[0], gdf.iloc[0].way.x, gdf.iloc[0].way.y)

    def find_shortest_path_between(self, A: DBPoint, B: DBPoint) -> Optional[Tuple[List[DBPoint], float]]:
        """
        Finds the shortest path between two DBPoints using Dijsktra algorithm.

        Args:
            A (DBPoint): The starting point.
            B (DBPoint): The ending point.

        Returns:
            Optional[Tuple[List[DBPoint], float]]: A tuple containing a list of DBPoints representing the shortest path and the total cost of the path. Returns None if no path is found.
        """
        print("Dijkstra | Finding source and target...")
        source = self._find_nearest_source(A, B)
        print("Dijkstra | Source found")
        target = self._find_nearest_target(B)
        print("Dijkstra | Target found")

        path = []
        expand = 10000
        while len(path) == 0 and expand < 1000000:
            query = f"""
            SELECT *
            FROM pgr_dijkstra(
                'SELECT osm_id as id, source, target, ST_Length(way) as cost 
                FROM planet_osm_line as rr,
                    (SELECT ST_Expand(ST_Extent(l1.way),{expand}) as box  FROM planet_osm_line as l1 WHERE l1.source = {source} OR l1.target = {target}) as box
                WHERE rr.way && box.box AND rr.highway IS NOT NULL',
                {source}, {target}, false
            ) as r
            INNER JOIN planet_osm_line as g ON r.edge = g.osm_id
            LEFT JOIN planet_osm_line_vertices_pgr as pnt on r.node = pnt.id;
            """

            print(f"Dijkstra | Finding shortest path for expand={expand}m...")
            try:
                gdf = gpd.GeoDataFrame.from_postgis(
                    query,
                    self._engine,
                    geom_col="the_geom",
                    index_col="osm_id",
                )
                gdf = gdf.reset_index()
                if len(gdf) == 0:
                    expand *= 2
                    continue
                print("Dijkstra | Shortest path found")
                return (
                    [
                        DBPoint(row.osm_id, row.the_geom.x, row.the_geom.y)
                        for idx, row in gdf.to_crs("EPSG:4326").iterrows()
                    ],
                    gdf.iloc[-1].agg_cost,
                )
            except ValueError as e:
                print("Dijkstra | Shortest path not found: " + str(e))
                return None, None
        print("Dijkstra | Shortest path not found")
        return ([], 0)

    def _find_nearest_source(self, start: DBPoint, end: DBPoint) -> int:
        """
        Finds the nearest source of the road to the given start and end points.

        Args:
            start (DBPoint): The starting point.
            end (DBPoint): The ending point.

        Returns:
            int: The ID of the nearest source point.
        """
        curr_radius = INIT_BUFFER_DIJKSTRA
        result = None
        with self._engine.connect() as connection:
            while curr_radius < MAX_BUFFER_RADIUS and (result is None or len(result) == 0):
                query = f"""
                WITH start_point AS (
                    SELECT ST_Transform(way, 4326) AS geom
                    FROM planet_osm_point
                    WHERE osm_id = {start.id}
                    LIMIT 1
                ),
                end_point AS (
                    SELECT ST_Transform(way, 4326) AS geom
                    FROM planet_osm_point
                    WHERE osm_id = {end.id}
                    LIMIT 1
                ),
                distances1 AS (
                    SELECT r.osm_id, ST_Distance(ST_Transform(ST_StartPoint(r.way), 4326), sp.geom) AS distance
                    FROM planet_osm_line AS r, start_point AS sp
                    WHERE r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
                    AND ST_DWithin(ST_Transform(ST_StartPoint(r.way), 4326), sp.geom, {curr_radius})
                    ORDER BY distance ASC
                )
                SELECT source FROM (
                    SELECT r.*, d.distance
                    FROM planet_osm_line AS r
                    JOIN distances1 d ON r.osm_id = d.osm_id
                    WHERE r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
                ) AS closest_starts
                ORDER BY ST_Distance(ST_Transform(ST_EndPoint(closest_starts.way), 4326), (SELECT geom FROM end_point))
                LIMIT 1;
                """
                result = connection.execute(text(query)).fetchone()
                curr_radius *= 2
            return result[0]

    def _find_nearest_target(self, end: DBPoint) -> int:
        """
        Finds the nearest target of the road based on the given end point.

        Args:
            end (DBPoint): The end point to find the nearest target for.

        Returns:
            int: The ID of the nearest target.
        """
        curr_radius = INIT_BUFFER_DIJKSTRA
        result = None
        with self._engine.connect() as connection:
            while curr_radius < MAX_BUFFER_RADIUS and (result is None or len(result) == 0):
                query = f"""
                WITH end_point AS (
                SELECT ST_Transform(way, 4326) as geom
                FROM planet_osm_point
                WHERE osm_id = {end.id}
                LIMIT 1
                ),
                nearby_lines AS (
                    SELECT r.osm_id, r.way
                    FROM planet_osm_line AS r
                    CROSS JOIN end_point
                    WHERE r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
                    AND ST_DWithin(ST_Transform(ST_EndPoint(r.way), 4326), end_point.geom, {curr_radius})
                )
                SELECT r.target
                FROM planet_osm_line AS r
                JOIN nearby_lines AS d ON r.osm_id = d.osm_id
                WHERE r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
                ORDER BY ST_Distance(ST_Transform(ST_EndPoint(d.way), 4326), (SELECT geom FROM end_point)) ASC
                LIMIT 1;
                """
                result = connection.execute(text(query)).fetchone()
                curr_radius *= 2
            return result[0]

    def get_valid_points(
        self, point: DBPoint, max_distance: float, max_time: float, min_time: float, amenity: str
    ) -> List[DBPoint]:
        """
        Retrieves a list of valid points within a specified distance and time range from a given point.

        Args:
            point (DBPoint): The reference point.
            max_distance (float): The maximum distance from the reference point.
            max_time (float): The maximum time it takes to reach the points from the reference point.
            min_time (float): The minimum time it takes to reach the points from the reference point.
            amenity (str): The type of amenity to filter the points.

        Returns:
            List[DBPoint]: A list of valid points within the specified distance and time range.
        """
        # v = s/t -> s = v*t
        max_distance = min(max_distance, VELOCITY * max_time)
        min_distance = VELOCITY * min_time
        curr_radius = INIT_BUFFER_RADIUS
        gdf = None
        while (
            (curr_radius < MAX_BUFFER_RADIUS)
            and (111320 * curr_radius < max_distance)
            and (gdf is None or gdf.shape[0] == 0)
        ):
            query = f"""
            WITH point_geom AS (
            SELECT ST_SetSRID(ST_MakePoint({point.x}, {point.y}), 4326) AS geom
            ),
            buffered_points AS (
                SELECT p.*, ST_Distance(ST_Transform(p.way, 4326), (SELECT geom FROM point_geom)) * 111320 AS dist
                FROM planet_osm_point AS p
                WHERE ST_DWithin(ST_Transform(p.way, 4326), (SELECT geom FROM point_geom), {curr_radius})
                AND p.amenity = '{amenity}'
            )

            SELECT *
            FROM buffered_points
            WHERE dist BETWEEN {min_distance} AND {max_distance}
            ORDER BY dist ASC;
            """
            gdf = gpd.GeoDataFrame.from_postgis(
                query,
                self._engine,
                geom_col="way",
            )
            gdf = gdf.reset_index()[1:]  # first row is the point itself
            curr_radius *= 2
        return (
            [DBPoint(row.osm_id, row.way.x, row.way.y) for idx, row in gdf.to_crs("EPSG:4326").iterrows()]
            if len(gdf)
            else []
        )
