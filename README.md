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
* VS Code (optional, for Dev Containers + debugging)

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

## VS Code (Dev Container + Debug)

1. Open repo in VS Code
2. Command Palette -> **Dev Containers: Reopen in Container**
3. Run and Debug -> **FastAPI (uvicorn)** -> F5
4. Use Swagger UI at http://localhost:8000/docs

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
2. Solves moving-target interception using target speed + heading (+ altitude)
3. Rejects options that exceed interceptor range before intercept
4. Estimates cost
5. Selects the lowest-cost viable option (tie-breakers: faster intercept, then shorter interceptor travel)

The selected result includes:

* base
* interceptor
* predicted interception coordinates (future target position)
* intercept time (seconds)
* interceptor travel distance (meters)
* estimated cost (EUR)

## Movement model (current)

Targets are assumed to:

* keep a constant speed (`speed_ms`)
* keep a constant heading (`heading_deg`)
* keep a constant altitude (`altitude_m`)

Interceptors are assumed to:

* launch immediately
* launch at max speed
* steer directly toward the intercept point

Intercept calculation uses a simple 3D model:

* base/interceptor start altitude is assumed to be `0 m`
* target altitude is constant
* target vertical speed is assumed to be `0 m/s`

## Engagement tracking (single target)

Radar passes data for **one object / threat at a time**.

To avoid launching a new interceptor every second for the same target, the API keeps a simple in-memory active engagement state:

* first actionable report -> launch interceptor
* next reports -> track the already launched interceptor
* once predicted intercept time is reached -> mark as intercepted

Notes:

* state is in-memory (reset if API restarts)
* this is intentionally simple for the single-target case

## Cost model assumptions (implementation)

To keep the decision deterministic and easy to test:

* Fighter jet (`per_minute`) is billed per started minute: `ceil(intercept_time_s / 60) * 1000`
* 50Cal (`per_shot`) uses a fixed burst of 100 shots by default (`100 EUR`)

## Seeded interceptors and bases

Interceptors:

* Interceptor drone: speed `80 m/s`, range `30,000 m`, max altitude `2,000 m`, cost `10,000 EUR`
* Fighter jet: speed `700 m/s`, range `350,000 m`, max altitude `15,000 m`, cost `1,000 EUR / minute`
* Rocket: speed `1,500 m/s`, range `100,000 m`, max altitude `30,000 m`, cost `300,000 EUR`
* 50Cal: speed `900 m/s`, range `2,000 m`, max altitude `2,000 m`, cost `1 EUR / shot`

Bases:

* Riga: all interceptor types
* Daugavpils: no Fighter jet
* Liepaja: Interceptor drone + 50Cal only

## Radar report format

Radar sends a new report every 1 second for the same tracked object:

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
* `GET /debug/db-data` (optional helper) -> shows bases + inventory currently read from MySQL
* `POST /radar/report` -> returns classification + chosen base + chosen interceptor + predicted interception coordinates

Optional debug helpers (if enabled in your local version):

* `GET /engagement/active` -> shows current in-memory engagement state
* `POST /engagement/reset` -> clears current in-memory engagement state

Example request:

```json
{
  "speed_ms": 20,
  "altitude_m": 500,
  "heading_deg": 45,
  "latitude": 56.516083346891044,
  "longitude": 21.0182217849017,
  "report_time": 0
}
```

## Simulator (manual testing)

A simple script is included to simulate one moving target with constant speed, heading, and altitude, and send radar data every second.

Example:

```bash
python scripts/simulate_single_target.py --mode balanced
```

`balanced` mode tries to generate scenarios that more often exercise different interceptor types (50Cal, Interceptor drone, Fighter jet, Rocket).
