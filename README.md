# MoTA AI-GIS PoC — Runnable minimal prototype

This package is a **single-container monolithic Docker reference system** for the Jordan tourism AI-GIS PoC.

It keeps the architecture intentionally compact, but added majority of main features described in the ToR:

- PostgreSQL 16 + PostGIS in the same container
- FastAPI backend
- browser dashboard served directly by FastAPI
- session-based login
- CSV import pipelines for key datasets
- overview, investment explorer, simulation, and admin/import pages
- CSV / HTML export endpoints
- sample dummy data for all 12 governorates

## Included functions

### Auth
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Overview / Analytics
- `GET /api/overview/kpis`
- `GET /api/overview/regions`
- `GET /api/overview/map`
- `GET /api/overview/regions/{governorate_id}`
- `POST /api/analytics/recompute`

### Forecast
- `POST /api/forecasts/run`
- `GET /api/forecasts/runs`
- `GET /api/forecasts/latest`
- `GET /api/forecasts/runs/{model_run_id}`

### Simulation
- `POST /api/simulations/run`
- `GET /api/simulations/runs`
- `GET /api/simulations/latest`
- `GET /api/simulations/runs/{scenario_run_id}`

### Imports
- `POST /api/imports/visitors_monthly`
- `POST /api/imports/rooms_beds_monthly`
- `POST /api/imports/hotel_occupancy_monthly`
- `POST /api/imports/admin_boundaries`
- `GET /api/imports`
- `GET /api/imports/{job_id}/errors`

### Exports
- `GET /api/exports/overview.csv`
- `GET /api/exports/regions/{governorate_id}.csv`
- `GET /api/exports/executive-summary.html`

## Quick start

```bash
cd motapoc 
cp .env.example .env
docker compose up --build -d
```

Open:

- App: `http://localhost:8080`
- Health: `http://localhost:8080/health`

## Default login

- Username: `admin`
- Password: `admin123`

## First use

1. Sign in.
2. Open **Overview** and click **Recompute Indicators**.
3. Click **Run Forecast**.
4. Open **Scenario Simulation** and run a scenario.
5. Open **Data Import / Admin** to test CSV upload.

## Sample import files

See:

```text
tests/sample_imports/
```

Included sample files:

- `visitors_monthly_sample.csv`
- `rooms_beds_monthly_sample.csv`
- `hotel_occupancy_monthly_sample.csv`
- `admin_boundaries_sample.csv`

## Smoke test

```bash
bash scripts/smoke_test.sh
```

## Common commands

```bash
docker compose logs -f
docker compose down
docker compose down -v
```

## Reset database and start fresh

```bash
docker compose down -v
docker compose up --build -d
```

## Notes

This is still a **minimal runnable** package, not a full final ToR implementation.

Main simplifications that remain:

- simple session auth instead of db-based auth
- lightweight CSV import logic rather than a full ETL workflow engine
- HTML executive summary export instead of PDF export
- simple seasonal forecast method instead of SARIMA/Prophet
- simplified front-end implemented in plain HTML/JS/CSS
- simplified demo boundary geometries in seed data

## Suggested next step after this package

- add configurable thresholds and weights in UI
- add PDF export
- add deeper regional time-series charts
- add richer import validation and staging tables
- replace forecast baseline with stricter model selection
