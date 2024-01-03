from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.constants import AMENITIES
from backend.api.schemas import AmenitiesList, Path, RouteDetails

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
    # TODO: modify this function to return a path with points
    return Path(
        points=[
            {"map_point": route_details.start, "is_poi": False},
            {"map_point": route_details.end, "is_poi": False},
        ],
        path_time=route_details.additional_time,
        path_distance=route_details.additional_distance,
    ).model_dump()
