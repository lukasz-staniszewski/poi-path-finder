# poi-path-finer

## Authors

* [Lukasz Staniszewski](https://github.com/lukasz-staniszewski)
* [Bartosz Cywinski](https://github.com/cywinski)

## Prerequisites

* [PostgreSQL](https://www.postgresql.org/download/)
* [OSM2PGSQL](https://osm2pgsql.org/doc/install.html)
* [PostGIS](https://postgis.net/documentation/getting_started/)
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
