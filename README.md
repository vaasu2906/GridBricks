# Wind Forecast Portal

**Live app:** https://grid-bricks-iota.vercel.app
**Backend API:** https://gridbricks-c0ou.onrender.com/api (health check: `/api/health`)
**Video (2 parts, unlisted):** Part 1: <add link> · Part 2: <add link>

A web portal for the day-ahead purchasing team of a UK energy utility. It answers two questions for every
settlement period of a delivery day:

1. **What is the latest wind generation forecast available when we must commit to buying power?**
   (the most recent Elexon WINDFOR publication before gate closure on D-1)
2. **How accurate has that forecast been, and how much error should we plan for?**
   (out-of-sample MAE / RMSE / bias, and a calibrated planning buffer with measured coverage)

Scope follows the brief: GB national wind only, from Elexon (FUELHH actuals and WINDFOR forecasts), purchase
decisions for **January 2026** only.

> **AI tools disclosure:** this project was built with assistance from **Claude** (Anthropic), an AI
> assistant, for code generation, design review and documentation. All code was reviewed and tested by the author.

---

## Status

| Item | Status |
|---|---|
| Backend (FastAPI), domain logic, Elexon client | Done. 16 tests pass |
| Frontend (React + Vite + Recharts) | Done |
| Docker / docker-compose | Done. Runs locally |
| Live Elexon data | Done. Checked against the Elexon documentation |
| Deployment | Done. Frontend on Vercel, backend on Render |
| Demo video | Done. Links at the top |

---

## Results on live Elexon data (January 2026)

| Measure | Value |
|---|---|
| Periods scored | 1,488 (31 days × 48) |
| MAE | about 2,126 MW |
| RMSE | about 2,621 MW |
| Bias | about +1,840 MW (forecasts run high) |
| Buffer coverage, default settings | about 89% (target 90%) |

Buffer coverage is the share of periods where the actual wind was at or above the planned level after the
buffer. The figure is measured on the same January data used to choose the settings, so it is optimistic.
Because forecasts run about 1.8 GW high, the planning buffers are large (about 4–6 GW).

---

## Repository layout

```
.
├── README.md                      This file
├── docker-compose.yml             Runs backend (:8000) and frontend via nginx (:8080)
├── .gitignore
├── docs/
│   └── VIDEO_OUTLINE.md           Outline for the demo video
├── backend/
│   ├── Dockerfile                 python:3.12-slim, uvicorn
│   ├── requirements.txt           Runtime dependencies (pinned)
│   ├── requirements-dev.txt       + pytest
│   ├── .dockerignore
│   ├── app/
│   │   ├── config.py              Settings from environment variables
│   │   ├── core.py                Pure domain logic: gate closure, settlement periods,
│   │   │                          forecast selection, calibration, decision view, accuracy report
│   │   ├── elexon.py              Elexon Insights client (FUELHH, WINDFOR), chunked by day
│   │   ├── sample_source.py       SYNTHETIC data source for development and tests
│   │   ├── data.py                DataSource protocol, cached dataset loader, half-hour fill
│   │   ├── schemas.py             Pydantic response models
│   │   └── main.py                FastAPI app factory and routes
│   ├── scripts/
│   │   └── sweep_calibration.py   Tests calibration settings against live data
│   └── tests/
│       ├── test_core.py           Domain tests (clock changes, no look-ahead, calibration, buffers)
│       ├── test_api.py            HTTP contract tests
│       └── test_data.py           Data loading and half-hour fill tests
└── frontend/
    ├── Dockerfile                 Multi-stage: Node build, then nginx
    ├── nginx.conf                 Serves the app and proxies /api/ to the backend
    ├── package.json
    ├── vite.config.js             Dev server with /api proxy to :8000
    └── src/
        ├── App.jsx, main.jsx      App shell and data loading
        ├── api.js                 API calls (base URL from VITE_API_BASE)
        ├── format.js              Number and time formatting (UK time)
        ├── styles.css             Light and dark theme
        └── components/
            ├── Controls.jsx       Delivery-day picker (January 2026 only), optional demand input
            ├── SummaryCards.jsx   Gate closure, lead time, MAE, bias, coverage, thermal need
            ├── ForecastChart.jsx  Forecast vs actual vs planned wind (click a period)
            ├── VintagesPanel.jsx  Every WINDFOR publication for a period, with the one used marked
            ├── PeriodsTable.jsx   All 48 periods with buffer, error, coverage and thermal need
            └── AccuracyPanel.jsx  January accuracy by lead time and by day
```

---

## How the decision logic works

* **Gate closure.** Purchases for delivery day *D* are committed at **11:00 UK time on D-1**
  (configurable via `GATE_CLOSURE_HOUR`). Only forecasts published at or before that time are used.
* **Forecast used.** For each settlement period, the most recent eligible WINDFOR publication. The lead time
  (start time minus publish time) is recorded.
* **Buffer.** Per lead-time bucket, a quantile (`BUFFER_QUANTILE`, default 0.95) of past `forecast − actual`.
  Planned wind = forecast − buffer. Buffers are never negative. Calibration uses only settled days in the
  lookback window before the delivery day, and each historical day is scored with the forecast that was
  current at its own gate closure. Buckets with too few samples fall back to a pooled estimate, then to zero,
  and the fallback is reported.
* **Half-hour periods.** WINDFOR is published hourly, so a half-hour period reuses the forecast for its hour.
  This is an assumption, not an Elexon product, and it affects half of all periods.
* **Thermal requirement.** If a flat demand (MW) is entered, the view shows the thermal requirement implied by
  the central forecast and by the planned wind level. Demand is user input, not Elexon data.
* **Validation.** The accuracy report evaluates each January day out-of-sample with the same rules.

Deliberate omissions: no demand or price data (out of scope), no look-ahead, no upside buffer.

### Tuning calibration

`backend/scripts/sweep_calibration.py` runs the accuracy report for several lookback windows and buffer
quantiles and prints realised coverage:

```bash
cd backend
DATA_SOURCE=elexon python -m scripts.sweep_calibration
```

---

## Running the application

### Option A: Docker

```bash
docker compose up --build
# App: http://localhost:8080
# API docs: http://localhost:8000/docs
```

To use live Elexon data: `DATA_SOURCE=elexon docker compose up --build`.

### Option B: Local development

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
DATA_SOURCE=elexon uvicorn app.main:app --reload --port 8000
```

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
npm run build        # production build to frontend/dist
```

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATA_SOURCE` | `sample` | `elexon` for live data, `sample` for synthetic data |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Elexon Insights API base |
| `DECISION_TIMEZONE` | `Europe/London` | Timezone for gate closure and settlement periods |
| `GATE_CLOSURE_HOUR` | `11` | Local hour on D-1 when buying closes |
| `CALIBRATION_LOOKBACK_DAYS` | `14` | Historical window for buffers |
| `BUFFER_QUANTILE` | `0.95` | Confidence level of the planning buffer |
| `MIN_CALIBRATION_SAMPLES` | `20` | Minimum samples before a bucket is used on its own |
| `CORS_ORIGINS` | localhost origins | Comma-separated allowed frontend origins |
| `VITE_API_BASE` | `/api` | Frontend build setting: backend API address |

### Elexon integration

The client calls `GET {base}/datasets/{FUELHH|WINDFOR}/stream` with `publishDateTimeFrom` and
`publishDateTimeTo`, in one-day chunks, then filters `fuelType == "WIND"` and the time window.

The endpoint paths, parameter names and response fields (`startTime`, `publishTime`, `generation`,
`fuelType`) were checked against the Elexon documentation pages for FUELHH and WINDFOR. The documentation does
not name the API host; `https://data.elexon.co.uk/bmrs/api/v1` is the host that returned data.

---

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/meta` | Scope, timezone, gate closure, calibration settings, data source |
| GET | `/api/decision?delivery_date=YYYY-MM-DD&demand_mw=` | Decision view for one day |
| GET | `/api/accuracy?start_date=&end_date=` | Accuracy over a range (defaults to all of January) |
| GET | `/api/forecast-vintages?target_time=&delivery_date=` | Every publication for one period, and which was used |

Dates outside January 2026 return HTTP 400. Interactive docs are at `/docs` on the backend.

---

## Deployment

* **Frontend:** Vercel, https://grid-bricks-iota.vercel.app
* **Backend:** Render (Docker), https://gridbricks-c0ou.onrender.com. The free plan sleeps when idle, so the
  first request can take a minute while live data loads.

## Known limitations

* Coverage is measured on the same January data used to choose the settings. A fair check would tune on early
  January and test on late January.
* A few WINDFOR publish times look odd (for example 12:25, with negative lead times). The gate-closure rule
  excludes them, but they should be confirmed with Elexon.
* The Elexon parsing has no fixture-based tests yet.
* The whole January window is held in memory after loading. A production version would cache to storage.
* No authentication. Add SSO before exposing this internally.
