# Demo video outline (unlisted YouTube, max 10 minutes)

Not yet recorded. Keep each part under 5 minutes.

## Part 1 — Customer pitch (≤ 5 min)

Goal: show the team can answer "what forecast do I trust at 11:00 yesterday, and how wrong is it likely to be?"

1. (0:00) The problem: buying day-ahead, forecasts are weather-driven, decisions are locked at gate closure.
2. (0:45) Pick **15 January 2026**. Point out the gate-closure timestamp and that only forecasts published before it count.
3. (1:30) Walk the chart: forecast, actual outturn, and the buffered planned-wind line.
4. (2:30) Enter a demand figure; show thermal central vs thermal P90 and the risk premium in MWh.
5. (3:30) Open the forecast-history panel for one period: how the forecast moved and which vintage was used.
6. (4:15) Accuracy section: January out-of-sample MAE, bias, and buffer coverage against the 90% target.
7. (4:45) What comes next (live Elexon feed, seasonal calibration).

Be explicit that the demo uses synthetic data if `DATA_SOURCE=sample` is on screen.

## Part 2 — Engineering review (≤ 5 min)

Goal: let a technical lead review the work and understand it quickly.

1. (0:00) Architecture: React SPA → nginx → FastAPI; Elexon client → in-memory dataset → pure domain module.
2. (1:00) Domain module `backend/app/core.py`: gate closure, settlement periods (46/48/50), latest-before-cutoff
   selection, calibration from D-14…D-2, buffer fitting, accuracy report. Point out the no-look-ahead rules.
3. (2:00) Tests: `pytest -q`. Show the DST test, the calibration-excludes-D-1 test, buffer edge cases.
4. (2:45) Data layer: `DataSource` protocol; Elexon vs synthetic; why synthetic exists and how it is labelled.
5. (3:30) Frontend structure and where state lives; API contract in `schemas.py`.
6. (4:15) Practices: pinned deps, Docker multi-stage builds, config via env, what is not verified (live API,
   Docker run, deployment) and the known limitations in the README.
