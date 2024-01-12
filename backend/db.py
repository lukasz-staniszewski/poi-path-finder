from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import geopandas as gpd
from sqlalchemy import text
import pandas as pd
from typing import Optional, List, Tuple
from backend.constants import VELOCITY, INIT_BUFFER_RADIUS, MAX_BUFFER_RADIUS

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
        source = self._find_nearest_source(A, B)
        target = self._find_nearest_target(B)
        tuple_string = "("
        for r in ROAD_TYPES:
            tuple_string += f"''{str(r)}'',"
        tuple_string = tuple_string[:-1]
        tuple_string += ")"
        query = f"""
        SELECT *
        FROM pgr_dijkstra(
            'select osm_id as id, source, target, ST_Length(way) as cost FROM planet_osm_line where highway IN {tuple_string}',
            {source},
            {target},
            FALSE
        ) as p
            LEFT JOIN planet_osm_line as r on p.edge = r.osm_id
            LEFT JOIN planet_osm_line_vertices_pgr as pnt on p.node = pnt.id
        ORDER BY p.seq;
        """
        try:
            gdf = gpd.GeoDataFrame.from_postgis(
                query,
                self._engine,
                geom_col="the_geom",
                index_col="osm_id",
            )
            gdf = gdf.reset_index()
            return (
                [
                    DBPoint(row.osm_id, row.the_geom.x, row.the_geom.y)
                    for idx, row in gdf.to_crs("EPSG:4326").iterrows()
                ],
                gdf.iloc[-1].agg_cost,
            )
        except ValueError:
            return None, None

    def _find_nearest_source(self, start: DBPoint, end: DBPoint) -> int:
        curr_radius = INIT_BUFFER_RADIUS
        result = None
        with self._engine.connect() as connection:
            while curr_radius < MAX_BUFFER_RADIUS and (result is None or len(result) == 0):
                query = f"""
                WITH start_point AS (
                    SELECT ST_Transform(way, 4326) AS geom
                    FROM planet_osm_point
                    WHERE osm_id = {start.id}
                ),
                end_point AS (
                    SELECT ST_Transform(way, 4326) AS geom
                    FROM planet_osm_point
                    WHERE osm_id = {end.id}
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
        curr_radius = INIT_BUFFER_RADIUS
        result = None
        with self._engine.connect() as connection:
            while curr_radius < MAX_BUFFER_RADIUS and (result is None or len(result) == 0):
                query = f"""
                WITH end_point AS (
                SELECT ST_Transform(way, 4326) as geom
                FROM planet_osm_point
                WHERE osm_id = {end.id}
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
