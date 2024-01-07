from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import geopandas as gpd
from sqlalchemy import text
import pandas as pd

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


class DB:
    def __init__(self) -> None:
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self._engine = create_engine(url)

    def get_first_n_points(self, n: int) -> gpd.GeoDataFrame:
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
        return gdf

    def get_point_by_id(self, id: int) -> gpd.GeoDataFrame:
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
        return gdf

    def get_nearest_point(self, x: float, y: float) -> gpd.GeoDataFrame:
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
            params=(x, y),
        ).to_crs("EPSG:4326")
        return gdf

    def find_shortest_path_between(self, A, B) -> gpd.GeoDataFrame:
        with self._engine.connect() as connection:
            print(A.index[0], B.index[0])
            source = self._find_nearest_source(A.index[0], B.index[0])
            target = self._find_nearest_target(B.index[0])
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
            gdf = gpd.GeoDataFrame.from_postgis(
                query,
                self._engine,
                geom_col="the_geom",
                index_col="osm_id",
            ).to_crs("EPSG:4326")

            return gdf

    def _find_nearest_source(self, start_id, end_id) -> int:
        query = f"""
        WITH distances1 as (
        SELECT r.osm_id, ST_Distance(
            ST_SetSRID(ST_StartPoint(r.way), 3851),
            ST_SetSRID((
                SELECT way
                FROM planet_osm_point
                WHERE osm_id = {start_id}
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
                WHERE osm_id = {end_id}
                ), 3851)
            ) limit 1;
        """
        with self._engine.connect() as connection:
            result = connection.execute(text(query)).fetchone()
            if result:
                return result[0]
            else:
                return None

    def _find_nearest_target(self, id) -> int:
        query = f"""
        WITH distances as (
            SELECT r.osm_id, ST_Distance(
                ST_SetSRID(ST_EndPoint(r.way), 3851),
                ST_SetSRID((
                    SELECT way
                    FROM planet_osm_point
                    WHERE osm_id = {id}
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

    def get_vertex_by_id(self, id):
        query = """
        SELECT *
        FROM planet_osm_roads_vertices_pgr
        WHERE id = %s;
        """
        gdf = gpd.GeoDataFrame.from_postgis(
            query,
            self._engine,
            geom_col="the_geom",
            params=(id,),
        ).to_crs("EPSG:4326")
        return gdf
