from typing import List

from pydantic import BaseModel, Field


class MapPoint(BaseModel):
    """Point on the map"""

    x: float = Field(description="Point's latitude")
    y: float = Field(description="Point's longitude")


class POI(BaseModel):
    """Point of interest"""

    type: str | None = Field(description="Type of POI", default=None)
    visit_time: int | None = Field(description="Time to visit POI", default=None)


class RouteDetails(BaseModel):
    """Route details"""

    start: MapPoint
    end: MapPoint
    additional_time: float | None = Field(description="Additional time for POIs", default=None)
    additional_distance: float | None = Field(description="Additional distance for POIs", default=None)
    pois: List[POI] | None = Field(description="List of POIs", default=None)


class PathPoint(BaseModel):
    """Point on the path"""

    map_point: MapPoint
    is_poi: bool = Field(description="Is point of interest", default=False)
    poi_details: POI | None = Field(description="Details of the POI", default=None)
    dist_from_start: float = Field(description="Distance from start")
    time_from_start: float = Field(description="Time from start")

class Path(BaseModel):
    """Response path with points"""

    points: List[PathPoint] = Field(description="List of points on the path")
    path_time: float = Field(description="Time of the path")
    path_distance: float = Field(description="Distance of the path")
    additional_distance: float = Field(description="Additional distance")
    additional_time: float = Field(description="Additional time")

class AmenitiesList(BaseModel):
    """List of amenities"""

    amenities: List[str] = Field(description="List of possible amenities")
