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

    def get_first_n_points(self, n: int) -> List[DBPoint]:
        query = """
        SELECT way
        FROM planet_osm_point
        LIMIT %s;
        """
        gdf = gpd.GeoDataFrame.from_postgis(
            query,
            self._engine,
            geom_col="way",
            params=(n,),
        ).to_crs("EPSG:4326")
        return [DBPoint(gpd, row.way.x, row.way.y) for idx, row in gdf.iterrows()]

    def get_point_by_id(self, id: int) -> DBPoint:
        query = """
        SELECT *
        FROM planet_osm_point
        WHERE osm_id = %s;
        """
        gdf = gpd.GeoDataFrame.from_postgis(
            query,
            self._engine,
            geom_col="way",
            params=(id,),
        ).to_crs("EPSG:4326")
        return DBPoint(gdf.index[0], gdf.iloc[0].way.x, gdf.iloc[0].way.y)

    def get_nearest_point(self, point: DBPoint) -> DBPoint:
        query = """
        WITH distances AS (
            SELECT
                *,
                ST_Distance(ST_Transform(way, 4326), ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AS distance
            FROM planet_osm_point
        )
        SELECT *
        FROM distances
        ORDER BY distance ASC
        LIMIT 1;
        """
        gdf = gpd.GeoDataFrame.from_postgis(
            query,
            self._engine,
            geom_col="way",
            index_col="osm_id",
            params=(point.x, point.y),
        ).to_crs("EPSG:4326")
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
        select *
        from pgr_dijkstra(
            'select osm_id as id, source, target, ST_Length(way) as cost from planet_osm_line where highway IN {tuple_string}',
            {source},
            {target},
            FALSE
        ) as p
            left join planet_osm_line as r on p.edge = r.osm_id
            left join planet_osm_line_vertices_pgr as pnt on p.node = pnt.id
        order by p.seq;
        """
        try:
            gdf = gpd.GeoDataFrame.from_postgis(
                query,
                self._engine,
                geom_col="the_geom",
                index_col="osm_id",
            ).to_crs("EPSG:4326")
            gdf = gdf.reset_index()
            return (
                [DBPoint(row.osm_id, row.the_geom.x, row.the_geom.y) for idx, row in gdf.iterrows()],
                gdf.iloc[-1].agg_cost,
            )
        except ValueError:
            return None, None

    def _find_nearest_source(self, start: DBPoint, end: DBPoint) -> int:
        query = f"""
        WITH distances1 as (
        SELECT r.osm_id, ST_Distance(
            ST_SetSRID(ST_StartPoint(r.way), 3851),
            ST_SetSRID((
                SELECT way
                FROM planet_osm_point
                WHERE osm_id = {start.id}
                ), 3851)
            ) as distance
        FROM planet_osm_line as r
        WHERE r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
        )

        select source from (
            select *
            from planet_osm_line r join distances1 d on (r.osm_id = d.osm_id)
            where r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
            order by d.distance asc limit 10
            ) as closest_starts
        order by ST_Distance(
            ST_SetSRID(ST_EndPoint(closest_starts.way), 3851),
            ST_SetSRID((
                SELECT way
                FROM planet_osm_point
                WHERE osm_id = {end.id}
                ), 3851)
            ) limit 1;
        """
        with self._engine.connect() as connection:
            result = connection.execute(text(query)).fetchone()
            if result:
                return result[0]
            else:
                return None

    def _find_nearest_target(self, end: DBPoint) -> int:
        query = f"""
        WITH distances as (
            SELECT r.osm_id, ST_Distance(
                ST_SetSRID(ST_EndPoint(r.way), 3851),
                ST_SetSRID((
                    SELECT way
                    FROM planet_osm_point
                    WHERE osm_id = {end.id}
                    ), 3851)
                ) as distance
            FROM planet_osm_line as r
            where r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
        )
        select r.target
        from planet_osm_line r join distances d on (r.osm_id = d.osm_id)
        where r.highway IN {tuple([str(r) for r in ROAD_TYPES])}
        order by d.distance asc limit 1;
        """
        with self._engine.connect() as connection:
            result = connection.execute(text(query)).fetchone()
            if result:
                return result[0]
            else:
                return None

    # def get_vertex_by_id(self, id):
    #     query = """
    #     SELECT *
    #     FROM planet_osm_roads_vertices_pgr
    #     WHERE id = %s;
    #     """
    #     gdf = gpd.GeoDataFrame.from_postgis(
    #         query,
    #         self._engine,
    #         geom_col="the_geom",
    #         params=(id,),
    #     ).to_crs("EPSG:4326")
    #     return gdf

    def get_valid_points(
        self, point: DBPoint, max_distance: float, max_time: float, min_time: float, amenity: str
    ) -> List[DBPoint]:
        # v = s/t -> s = v*t
        max_distance = min(max_distance, VELOCITY * max_time)
        min_distance = VELOCITY * min_time
        curr_radius = INIT_BUFFER_RADIUS
        gdf = None
        while (curr_radius < MAX_BUFFER_RADIUS) and (111320 * curr_radius < max_distance) and (gdf is None or gdf.shape[0] == 0):
            query = f"""
            SELECT *, 111320 * ST_Distance(ST_Transform(bp.way, 4326), ST_SetSRID(ST_MakePoint({point.x}, {point.y}), 4326)) as dist
            FROM (
                SELECT *
                FROM planet_osm_point
                WHERE ST_Within(
                    ST_Transform(way, 4326), (
                    SELECT ST_Buffer(
                        ST_SetSRID(ST_MakePoint({point.x}, {point.y}), 4326),
                        {curr_radius}
                    )))
            ) as bp
            WHERE 111320 * ST_Distance(ST_Transform(bp.way, 4326), ST_SetSRID(ST_MakePoint({point.x}, {point.y}), 4326)) < {max_distance} AND 111320 * ST_Distance(ST_Transform(bp.way, 4326), ST_SetSRID(ST_MakePoint({point.x}, {point.y}), 4326)) > {min_distance} AND bp.amenity = '{amenity}'
            ORDER BY dist ASC;
            """
            try:
                gdf = gpd.GeoDataFrame.from_postgis(
                    query,
                    self._engine,
                    geom_col="way",
                ).to_crs("EPSG:4326")
                gdf = gdf.reset_index()[1:]  # first row is the point itself
            except ValueError:
                pass
            finally:
                curr_radius *= 2

        return (
            [DBPoint(row.osm_id, row.way.x, row.way.y) for idx, row in gdf.iterrows()]
            if gdf is not None
            else None
        )
