from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.constants import AMENITIES
from backend.api.schemas import AmenitiesList, Path, RouteDetails, MapPoint
from backend.db import DB

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DB()


@app.get("/")
async def root():
    return {"message": "Hello SPDB!"}


@app.get("/amenities/", response_model=AmenitiesList)
async def amenities():
    return AmenitiesList(
        amenities=[amenity.replace("_", " ").capitalize() for amenity in AMENITIES]
    ).model_dump()


@app.post("/route/", response_model=Path)
async def create_route(route_details: RouteDetails):
    # TODO: modify this function to return a path with points
    A = db.get_nearest_point(route_details.start.longitude, route_details.start.latitude)
    B = db.get_nearest_point(route_details.end.longitude, route_details.end.latitude)
    path = db.find_shortest_path_between(A, B)

    points = []
    for i in range(len(path)):
        points.append(
            {
                "map_point": MapPoint(latitude=path.iloc[i].the_geom.y, longitude=path.iloc[i].the_geom.x),
                "is_poi": False,
            }
        )
    print(points)
    return Path(
        points=points,
        path_time=route_details.additional_time,
        path_distance=route_details.additional_distance,
    ).model_dump()
