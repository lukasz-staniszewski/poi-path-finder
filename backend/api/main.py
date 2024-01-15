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

    shortest_path = finder.shortest_path
    path = finder.curr_path
    pois = finder.curr_pois
    pois_ids = set([poi[0].id for poi in pois])

    shortest_points = []
    for i in range(len(shortest_path)):
        point = shortest_path[i]
        shortest_points.append(
            {
                "map_point": MapPoint(x=point.x, y=point.y),
                "is_poi": False,
                "poi_details": None,
                "dist_from_start": None,
                "time_from_start": None,
            }
        )

    points = []
    for i in range(len(path)):
        point = path[i]
        is_poi = point.id in pois_ids
        points.append(
            {
                "map_point": MapPoint(x=point.x, y=point.y),
                "is_poi": is_poi,
                "poi_details": POI(
                    type=pois[0][2] if is_poi else None,
                    visit_time=pois[0][1] if is_poi else None,
                ).model_dump(),
                "dist_from_start": f"{pois[0][3] / 1000:.1f}" if is_poi else None,
                "time_from_start": f"{pois[0][4] / 60:.1f}" if is_poi else None,
            }
        )
        if is_poi:
            pois.pop(0)

    return Path(
        shortest_points=shortest_points,
        points=points,
        path_time= f"{finder.curr_time / 60:.1f}",
        path_distance=f"{finder.curr_cost / 1000:.1f}",
        additional_distance=f"{finder.curr_additional_distance / 1000:.1f}",
        additional_time=f"{finder.curr_additional_time / 60:.1f}",
    ).model_dump()
