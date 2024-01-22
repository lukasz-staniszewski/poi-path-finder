# Map Path Finder with Points of Interest

## Description

This project is a spatial data-related application determining the route on the map along with indicating the places to visit (points of interest) while satisfying the following route constraints: The starting point and destination of the journey, extension of travel time (route length and time period) and the time period during which a given point of interest is to be visited.

## Authors

* [Lukasz Staniszewski](https://github.com/lukasz-staniszewski)
* [Bartosz Cywinski](https://github.com/cywinski)

## Prerequisites

* [PostgreSQL](https://www.postgresql.org/download/)
* [OSM2PGSQL](https://osm2pgsql.org/doc/install.html)
* [PostGIS](https://postgis.net/documentation/getting_started/)
* [pgRouting](https://pgrouting.org/download.html)
* [Python 3.10](https://www.python.org/downloads/)
* [PIP Packages](requirements.txt)

## Getting started

### Populate database

```
osm2pgsql -c map.osm --database=spdb --username=admin -W --host=localhost --port=5432
```

## Run application

### FastAPI Backend

From the root directory run:

```bash
uvicorn backend.api:application --reload
```

### Frontend

Access `frontend/index.html` file in your browser.

## Tests

### Backend unit tests

From the root directory run:

```bash
pytest -m health
```
