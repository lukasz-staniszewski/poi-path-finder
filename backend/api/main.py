from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.constants import AMENITIES
from backend.api.schemas import AmenitiesList, Path, RouteDetails, MapPoint, POI
from backend.pathfinder import PathFinder

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    finder = PathFinder(
        start=route_details.start,
        end=route_details.end,
        max_time=route_details.additional_time,
        max_distance=route_details.additional_distance,
        max_num_pois=len(route_details.pois),
        pois_order=route_details.pois,
    )

    path = finder.curr_path
    print(path)

    return Path(
        points=[
            {
                "map_point": MapPoint(x=p.x, y=p.y),
                "is_poi": False,
            }
            for p in path
        ],
        path_time=route_details.additional_time,
        path_distance=route_details.additional_distance,
    ).model_dump()
