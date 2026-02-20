# Threat Classification & Interception API

Containerized Python (3.12+) FastAPI service that receives radar reports, classifies threats, and selects a feasible / cost-effective interception option using base + interceptor data stored in a MySQL database.

## Tech
- Docker + Docker Compose
- Python 3.12+
- FastAPI
- PyTest
- MySQL

## Prerequisites
- Docker Engine / Docker Desktop
- Docker Compose v2 (`docker compose ...`)

## Run (Linux / macOS / Windows)
From the repository root:

Start:
```bash
docker compose up -d --build
````

Check containers:

```bash
docker compose ps
```

Open API:

* Health check: http://localhost:8000/health
* Swagger UI: http://localhost:8000/docs

Stop:

```bash
docker compose down
```

Reset DB (re-seed from `db/init.sql`):

> MySQL init scripts run only on a fresh data volume.

```bash
docker compose down -v
docker compose up -d --build
```

## Tests

Run tests inside the API container:

```bash
docker compose exec api pytest -q
```

## VS Code Debug (Dev Container)

1. Open the repo in VS Code
2. Command Palette -> **Dev Containers: Reopen in Container**
3. Run and Debug -> **FastAPI (uvicorn)** -> F5
4. Open http://localhost:8000/docs

## Database

The system reads base locations and available interceptors from MySQL.

Schema + seed data:

* `db/init.sql`

Host connection (optional):

* Host: `127.0.0.1`
* Port: `3307`
* User: `app`
* Password: `app_pw`
* Database: `appdb`

## Threat classification rules

* If `speed_ms < 15` OR `altitude_m < 200` -> **not a threat**
* If `speed_ms > 50` -> **threat**
* If `speed_ms > 15` -> **caution**
* Otherwise -> **potential threat**

## Interceptors and bases (seeded in DB)

Interceptors:

* Interceptor drone: speed 80 m/s, range 30,000 m, max altitude 2,000 m, cost 10,000 EUR
* Fighter jet: speed 700 m/s, range 3,500 m, max altitude 15,000 m, cost 1,000 EUR / minute
* Rocket: speed 1,500 m/s, range 100,000 m, max altitude 30,000 m, cost 300,000 EUR
* 50Cal: speed 900 m/s, range 2,000 m, max altitude 2,000 m, cost 1 EUR / shot

Bases:

* Riga has all interceptor types
* Daugavpils lacks Fighter jet
* Liepaja has only Interceptor drone and 50Cal

## Radar report format

Radar sends a new report every 1 second:

```json
{
  "speed_ms": 0,
  "altitude_m": 0,
  "heading_deg": 0,
  "latitude": 0,
  "longitude": 0,
  "report_time": 0
}
```

## API (current / planned)

Current:

* `GET /health`

Planned:

* `POST /radar/report` -> returns classification + chosen base + chosen interceptor + intercept coordinates

```
::contentReference[oaicite:0]{index=0}
```
