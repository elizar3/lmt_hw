# Threat Classification & Interception API

Containerized Python (3.12+) FastAPI service for receiving radar reports, classifying threats, and selecting a feasible/cost-effective interception option using data stored in MySQL.

## Tech

* Docker + Docker Compose
* Python 3.12+
* FastAPI
* PyTest
* MySQL

## Prerequisites

* Docker Engine / Docker Desktop
* Docker Compose v2 (`docker compose ...`)

## Run

From the repository root:

Start:

```bash
docker compose up -d --build
```

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

```bash
docker compose down -v
docker compose up -d --build
```

## Tests

Run tests inside the API container:

```bash
docker compose exec api pytest -q
```

## VS Code (Dev Container + Debug)

1. Open repo in VS Code
2. Command Palette -> **Dev Containers: Reopen in Container**
3. Run and Debug -> **FastAPI (uvicorn)** -> F5

## Database

Base locations, interceptor definitions, and base inventory are seeded from:

* `db/init.sql`

Optional host MySQL connection:

* Host: `127.0.0.1`
* Port: `3307`
* User: `app`
* Password: `app_pw`
* Database: `appdb`

## Threat classification rules

* If `speed_ms < 15` OR `altitude_m < 200` -> `not_threat`
* If `speed_ms > 50` -> `threat`
* If `speed_ms > 15` -> `caution`
* Otherwise -> `potential_threat`

## Interception logic (current)

For reports that are not `not_threat`, the decision engine:

1. Checks altitude feasibility (`target altitude <= interceptor max altitude`)
2. Solves moving-target interception in the horizontal plane using target speed + heading
3. Rejects options that exceed interceptor range before intercept
4. Estimates cost
5. Selects the lowest-cost viable option (tie-breakers: faster intercept, then shorter interceptor travel)

The selected result includes:

* base
* interceptor
* predicted interception coordinates (future target position)
* intercept time
* interceptor travel distance
* estimated cost

## Movement model (current)

* Target moves with constant speed and heading
* Target altitude is treated as constant during the intercept calculation
* Interceptor launches immediately and flies at constant speed
* Intercept math is 2D (horizontal plane); altitude is a separate feasibility constraint

## Cost model assumptions (implementation)

* Fighter jet (`per_minute`) is billed per started minute: `ceil(intercept_time_s / 60) * 1000`
* 50Cal (`per_shot`) uses a fixed burst of 100 shots by default (`100 EUR`)

## Seeded interceptors and bases

Interceptors:

* Interceptor drone: `80 m/s`, range `30,000 m`, max altitude `2,000 m`, cost `10,000 EUR`
* Fighter jet: `700 m/s`, range `3,500 m`, max altitude `15,000 m`, cost `1,000 EUR / minute`
* Rocket: `1,500 m/s`, range `100,000 m`, max altitude `30,000 m`, cost `300,000 EUR`
* 50Cal: `900 m/s`, range `2,000 m`, max altitude `2,000 m`, cost `1 EUR / shot`

Bases:

* Riga: all interceptor types
* Daugavpils: no Fighter jet
* Liepaja: Interceptor drone + 50Cal only

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

## API

Current:

* `GET /health`

Planned:

* `POST /radar/report` -> returns classification + chosen base + chosen interceptor + predicted interception coordinates
