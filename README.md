# Wind Forecast Portal

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

## Status of this build (read first)

| Item | Status |
|---|---|
| Backend (FastAPI) with domain logic, Elexon client, tests | Done — 14 unit/API tests pass |
| Frontend (React + Vite + Recharts) | Done — production build passes |
| Docker / docker-compose | Files written; **not executed in the build environment** (no Docker daemon there) |
| Live Elexon data | **Not verified.** The build sandbox's egress proxy blocked `bmrs.elexon.co.uk` / the Insights API (HTTP 403 on CONNECT). The app therefore ships with a clearly labelled **synthetic sample source** for development and tests. Set `DATA_SOURCE=elexon` to use the live API. |
| Vercel / Heroku deployment | **Not done** (requires account access). See "Deployment" below. |
| Demo video (YouTube, unlisted) | **Not done.** An outline is in `docs/VIDEO_OUTLINE.md`. |
| Submission form | **Not done.** |

Numbers shown with `DATA_SOURCE=sample` are **synthetic** and must not be presented as Elexon outturn.

---

## Repository layout

```
.
├── README.md                      This file
├── docker-compose.yml             Runs backend (:8000) and frontend via nginx (:8080)
├── .gitignore
├── docs/
│   └── VIDEO_OUTLINE.md           Script/outline for the two-part demo video
├── backend/
│   ├── Dockerfile                 python:3.12-slim, uvicorn
│   ├── requirements.txt           Runtime dependencies (pinned)
│   ├── requirements-dev.txt       + pytest
│   ├── .dockerignore
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py              Settings from environment variables; decision scope and data window
│   │   ├── core.py                Pure domain logic (no I/O): gate closure, settlement periods,
│   │   │                          forecast selection, calibration, decision view, accuracy report
│   │   ├── elexon.py              Elexon BMRS Insights client (FUELHH, WINDFOR), chunked by day
│   │   ├── sample_source.py       SYNTHETIC deterministic data source for dev/tests/offline demos
│   │   ├── data.py                DataSource protocol + in-memory cached dataset loader
│   │   ├── schemas.py             Pydantic response models
│   │   └── main.py                FastAPI app factory and routes
│   └── tests/
│       ├── test_core.py           Domain tests (calendar/DST, no-look-ahead, calibration, buffers)
│       └── test_api.py            HTTP contract tests
└── frontend/
    ├── Dockerfile                 Multi-stage: Node build → nginx static serve
    ├── nginx.conf                 Serves SPA, proxies /api/ to the backend
    ├── package.json
    ├── vite.config.js             Dev server with /api proxy to :8000
    ├── index.html
    └── src/
        ├── main.jsx, App.jsx      App shell and data loading
        ├── api.js                 Fetch wrapper for the API
        ├── format.js              Number/time formatting (UK local time)
        ├── styles.css             Light/dark theme
        └── components/
            ├── Controls.jsx       Delivery-day picker (Jan 2026 only), optional demand input
            ├── SummaryCards.jsx   Gate closure, lead time, MAE, bias, coverage, thermal/buffer totals
            ├── ForecastChart.jsx  Forecast vs actual vs planned wind (click a period to inspect)
            ├── VintagesPanel.jsx  Every WINDFOR publication for the selected period, flagging the one used
            ├── PeriodsTable.jsx   All 48 (or 46/50) periods with buffer, error, coverage, thermal need
            └── AccuracyPanel.jsx  January out-of-sample accuracy by lead time and per day
```

---

## How the decision logic works

* **Gate closure.** Day-ahead purchases for delivery day *D* are committed at **11:00 UK time on D-1**
  (configurable via `GATE_CLOSURE_HOUR`). Only forecasts with `publishTime ≤` that instant are eligible.
* **Forecast used.** For each settlement period, the most recent eligible WINDFOR publication. The lead time
  (`startTime − publishTime`) is recorded; with an 11:00 gate closure it is between roughly 13 h and 37 h.
* **Buffer (quantified error).** Per lead-time bucket, the 90th percentile of historical `forecast − actual`
  (`BUFFER_QUANTILE`, default 0.9). Planned wind = forecast − buffer, which should be exceeded by the outturn
  about 90% of the time. Buffers are never negative. Calibration uses only settled days **D-14 … D-2**
  (D-1 actuals are not known at gate closure), and each historical day is scored with the forecast that was
  current at its own gate closure. Buckets with too few samples fall back to a pooled estimate, then to zero,
  and the fallback is reported.
* **Thermal requirement.** If a flat demand (MW) is entered, the view shows the thermal requirement implied
  by the central forecast and by the planned (buffered) wind level. Demand is **user input**, not Elexon data.
* **Validation.** The accuracy report evaluates each January day out-of-sample with the same rules and reports
  MAE, RMSE, bias, normalised MAE and the realised buffer coverage (should be close to 90%).

Deliberate omissions: no demand or price data (out of scope), no look-ahead, no upside buffer.

---

## Running the application

### Option A — Docker

```bash
docker compose up --build
# UI:  http://localhost:8080
# API: http://localhost:8000/docs
```

To use live Elexon data: `DATA_SOURCE=elexon docker compose up --build`.

### Option B — Local development

Backend:

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                                   # 14 tests
uvicorn app.main:app --reload --port 8000   # DATA_SOURCE=sample by default
```

Frontend (in another terminal):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api to :8000)
npm run build        # production build to frontend/dist
```

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATA_SOURCE` | `sample` | `elexon` for the live API, `sample` for synthetic data |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Insights API base; verify against Elexon docs |
| `DECISION_TIMEZONE` | `Europe/London` | Timezone of gate closure and settlement periods |
| `GATE_CLOSURE_HOUR` | `11` | Local hour on D-1 when buying closes |
| `CALIBRATION_LOOKBACK_DAYS` | `14` | Historical window for buffers |
| `BUFFER_QUANTILE` | `0.9` | Confidence level of the planning buffer |
| `MIN_CALIBRATION_SAMPLES` | `20` | Minimum samples before a bucket is used on its own |
| `CORS_ORIGINS` | localhost dev/docker origins | Comma-separated allowed origins |

### Verifying the live Elexon integration

The Elexon client issues `GET {base}/datasets/{FUELHH|WINDFOR}/stream` with `publishDateTimeFrom` and
`publishDateTimeTo` (one-day chunks), then filters `fuelType == "WIND"` and the `startTime` window
client-side. I could not confirm these parameter names or the base URL against the live service from the build
environment, so **check them against the Elexon API documentation before going live**. The parsing is
covered by no tests yet, so add fixture-based tests once a sample response has been captured.

---

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness |
| GET | `/api/meta` | Scope, timezone, gate closure, calibration settings, data source |
| GET | `/api/decision?delivery_date=YYYY-MM-DD&demand_mw=` | Decision view for one day |
| GET | `/api/accuracy?start_date=&end_date=` | Out-of-sample accuracy over a range (defaults to all of January) |
| GET | `/api/forecast-vintages?target_time=&delivery_date=` | Every publication for one period and which one was used |

Dates outside January 2026 return HTTP 400. Interactive docs are at `/docs`.

---

## Deployment

* **Vercel / Heroku — not yet deployed.** For Heroku, deploy the backend container and serve the frontend build
  as static files pointed at it. For Vercel, the frontend can be deployed as a static Vite app with the backend
  hosted separately (set `VITE_API_BASE` to the backend URL).
* After deployment, the link should be added here: **`<TODO: deployment URL>`**.

## Known limitations and next steps

* Live Elexon ingestion is unverified (see above); add contract tests with captured fixtures.
* Forecast selection scans all vintages per period (linear). Fine for one month; index by publish time if the
  window grows.
* The whole January window is held in memory, loaded on first request. A production version would cache to
  storage and refresh incrementally.
* Buffers are a single empirical quantile per lead-time bucket. Next: seasonal/conditional calibration
  (e.g. wind speed regime), and a proper probabilistic forecast if one becomes available.
* No authentication. Add SSO before exposing internally.
