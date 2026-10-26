"""Domain logic for day-ahead wind procurement decisions.

Pure functions only (no I/O) so everything here can be unit-tested offline.

Conventions
-----------
* All timestamps are timezone-aware UTC ``datetime`` objects.
* ``error = forecast - actual``. A positive error means the wind forecast was too
  high, i.e. the system would have been short of wind and must cover the gap with
  thermal plant.
* Decisions are taken at *gate closure* on D-1 (local time, default 11:00 London).
  Only forecasts published at or before that instant may influence the decision.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
SETTLEMENT_PERIOD = timedelta(minutes=30)

# Lead-time buckets (hours). Day-ahead decisions are taken at D-1 gate closure, so every
# delivery-day period is at least ~13h ahead; "<12h" exists for completeness.
HORIZON_BUCKETS: tuple[tuple[float, float, str], ...] = (
    (0.0, 12.0, "<12h"),
    (12.0, 24.0, "12-24h"),
    (24.0, 48.0, "24-48h"),
    (48.0, math.inf, "48h+"),
)
BUCKET_LABELS: list[str] = [label for _, _, label in HORIZON_BUCKETS]


@dataclass(frozen=True)
class Observation:
    """A metered national wind generation value for one settlement period."""

    start_time: datetime
    generation_mw: float
    publish_time: datetime | None


@dataclass(frozen=True)
class Forecast:
    """One published wind generation forecast for one target settlement period."""

    target_time: datetime
    publish_time: datetime
    generation_mw: float

    @property
    def horizon_hours(self) -> float:
        return (self.target_time - self.publish_time).total_seconds() / 3600.0


def horizon_bucket(hours: float) -> str:
    if hours < 0:
        raise ValueError(f"Forecast published after its target time (horizon {hours:.2f}h)")
    for lo, hi, label in HORIZON_BUCKETS:
        if lo <= hours < hi:
            return label
    return HORIZON_BUCKETS[-1][2]


# --------------------------------------------------------------------------- calendar


def gate_closure_utc(delivery_day: date, tz: ZoneInfo, closure_hour: int) -> datetime:
    """Gate closure for buying ``delivery_day`` power: ``closure_hour`` local time on D-1."""
    local = datetime.combine(delivery_day - timedelta(days=1), time(closure_hour), tzinfo=tz)
    return local.astimezone(UTC)


def settlement_periods(delivery_day: date, tz: ZoneInfo) -> list[datetime]:
    """UTC start times of the settlement periods of a local delivery day.

    Returns 46, 48 or 50 periods depending on UK clock changes.
    """
    start = datetime.combine(delivery_day, time(0), tzinfo=tz).astimezone(UTC)
    end = datetime.combine(delivery_day + timedelta(days=1), time(0), tzinfo=tz).astimezone(UTC)
    count = round((end - start) / SETTLEMENT_PERIOD)
    return [start + i * SETTLEMENT_PERIOD for i in range(count)]


# --------------------------------------------------------------------------- selection


def latest_forecast_before(forecasts: list[Forecast], cutoff: datetime) -> Forecast | None:
    """Most recent forecast published at or before ``cutoff`` (no look-ahead)."""
    best: Forecast | None = None
    for f in forecasts:
        if f.publish_time <= cutoff and (best is None or f.publish_time > best.publish_time):
            best = f
    return best


def forecast_vintages(target: datetime, forecasts: list[Forecast], cutoff: datetime) -> list[dict]:
    """All published vintages for one target period, flagging the one used at ``cutoff``."""
    chosen = latest_forecast_before(forecasts, cutoff)
    out = []
    for f in sorted(forecasts, key=lambda f: f.publish_time):
        out.append(
            {
                "publish_time": f.publish_time,
                "horizon_hours": f.horizon_hours,
                "forecast_mw": f.generation_mw,
                "chosen": chosen is not None and f.publish_time == chosen.publish_time,
                "published_before_cutoff": f.publish_time <= cutoff,
            }
        )
    return out


# --------------------------------------------------------------------------- statistics


def quantile(values: list[float], q: float) -> float:
    """Linear-interpolated sample quantile for 0 <= q <= 1."""
    if not values:
        raise ValueError("quantile of an empty sequence")
    xs = sorted(values)
    pos = q * (len(xs) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def summarize_errors(errors: list[float], actuals: list[float]) -> dict:
    n = len(errors)
    if n == 0:
        return {"n": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None, "nmae_pct": None}
    mae = sum(abs(e) for e in errors) / n
    rmse = math.sqrt(sum(e * e for e in errors) / n)
    bias = sum(errors) / n
    mean_actual = sum(actuals) / n
    nmae = 100.0 * mae / mean_actual if mean_actual > 0 else None
    return {"n": n, "mae_mw": mae, "rmse_mw": rmse, "bias_mw": bias, "nmae_pct": nmae}


# --------------------------------------------------------------------------- calibration


@dataclass(frozen=True)
class Buffers:
    """Planning buffers (MW) per lead-time bucket, plus how each was obtained."""

    mw_by_bucket: dict[str, float]
    samples_by_bucket: dict[str, int]
    source_by_bucket: dict[str, str]  # "bucket" | "pooled" | "none"


def fit_buffers(samples: list[tuple[str, float]], q: float, min_samples: int) -> Buffers:
    """Fit a one-sided buffer per lead-time bucket from historical forecast errors.

    The buffer is the q-quantile of ``forecast - actual``. Planning with
    ``forecast - buffer`` therefore covers the wind outturn with probability ~q.
    Buffers are never negative: we do not plan on upside wind.
    """
    grouped: dict[str, list[float]] = defaultdict(list)
    for bucket, err in samples:
        grouped[bucket].append(err)
    pooled = [err for _, err in samples]

    mw, counts, sources = {}, {}, {}
    for label in BUCKET_LABELS:
        errs = grouped.get(label, [])
        counts[label] = len(errs)
        if len(errs) >= min_samples:
            mw[label], sources[label] = max(0.0, quantile(errs, q)), "bucket"
        elif len(pooled) >= min_samples:
            mw[label], sources[label] = max(0.0, quantile(pooled, q)), "pooled"
        else:
            mw[label], sources[label] = 0.0, "none"
    return Buffers(mw, counts, sources)


def calibration_samples(
    delivery_day: date,
    forecasts_by_target: dict[datetime, list[Forecast]],
    actuals: dict[datetime, float],
    *,
    tz: ZoneInfo,
    closure_hour: int,
    lookback_days: int,
) -> list[tuple[str, float]]:
    """Historical ``(bucket, error)`` pairs usable at the decision for ``delivery_day``.

    Uses settled days D-lookback .. D-2. Actuals for D-1 are not known at D-1 gate
    closure, so D-2 is the most recent usable day (no look-ahead). Each historical
    day is scored with the forecast that was current at *its own* gate closure, which
    mirrors what the desk would have seen then.
    """
    samples: list[tuple[str, float]] = []
    day = delivery_day - timedelta(days=lookback_days)
    last = delivery_day - timedelta(days=2)
    while day <= last:
        hist_cutoff = gate_closure_utc(day, tz, closure_hour)
        for t in settlement_periods(day, tz):
            actual = actuals.get(t)
            if actual is None:
                continue
            fc = latest_forecast_before(forecasts_by_target.get(t, []), hist_cutoff)
            if fc is None:
                continue
            samples.append((horizon_bucket(fc.horizon_hours), fc.generation_mw - actual))
        day += timedelta(days=1)
    return samples


# --------------------------------------------------------------------------- decision


def build_decision(
    delivery_day: date,
    forecasts_by_target: dict[datetime, list[Forecast]],
    actuals: dict[datetime, float],
    *,
    tz: ZoneInfo,
    closure_hour: int,
    lookback_days: int,
    buffer_quantile: float,
    min_samples: int,
    demand_mw: float | None = None,
) -> dict:
    """Build the procurement view for one delivery day as it would have been at gate closure.

    ``actuals`` is used only to *score* the decision (and to calibrate from past days).
    If ``demand_mw`` is given (a user-supplied flat demand, not from Elexon), the view
    includes the thermal requirement implied by the central forecast and by the
    P-quantile covered wind level.
    """
    cutoff = gate_closure_utc(delivery_day, tz, closure_hour)
    samples = calibration_samples(
        delivery_day,
        forecasts_by_target,
        actuals,
        tz=tz,
        closure_hour=closure_hour,
        lookback_days=lookback_days,
    )
    buffers = fit_buffers(samples, buffer_quantile, min_samples)

    rows: list[dict] = []
    for t in settlement_periods(delivery_day, tz):
        fc = latest_forecast_before(forecasts_by_target.get(t, []), cutoff)
        actual = actuals.get(t)
        row: dict = {
            "start_time": t,
            "forecast_mw": None,
            "publish_time": None,
            "horizon_hours": None,
            "horizon_bucket": None,
            "buffer_mw": None,
            "covered_wind_mw": None,
            "actual_mw": actual,
            "error_mw": None,
            "within_coverage": None,
            "thermal_central_mw": None,
            "thermal_p90_mw": None,
        }
        if fc is not None:
            bucket = horizon_bucket(fc.horizon_hours)
            buffer = buffers.mw_by_bucket[bucket]
            covered = max(0.0, fc.generation_mw - buffer)
            row.update(
                forecast_mw=fc.generation_mw,
                publish_time=fc.publish_time,
                horizon_hours=fc.horizon_hours,
                horizon_bucket=bucket,
                buffer_mw=buffer,
                covered_wind_mw=covered,
            )
            if actual is not None:
                row["error_mw"] = fc.generation_mw - actual
                row["within_coverage"] = actual >= covered
            if demand_mw is not None:
                row["thermal_central_mw"] = max(0.0, demand_mw - fc.generation_mw)
                row["thermal_p90_mw"] = max(0.0, demand_mw - covered)
        rows.append(row)

    return {
        "delivery_date": delivery_day,
        "decision_cutoff": cutoff,
        "demand_mw": demand_mw,
        "periods": rows,
        "summary": _summarise(rows, buffers, samples, demand_mw),
    }


def _summarise(rows: list[dict], buffers: Buffers, samples: list, demand_mw: float | None) -> dict:
    """Aggregate a day. Energy totals use 30-minute periods (MW x 0.5 h = MWh)."""
    scored = [r for r in rows if r["error_mw"] is not None]
    horizons = [r["horizon_hours"] for r in rows if r["horizon_hours"] is not None]
    coverage = [r["within_coverage"] for r in scored]
    buffers_total = [r["buffer_mw"] for r in rows if r["buffer_mw"] is not None]
    covered_total = [r["covered_wind_mw"] for r in rows if r["covered_wind_mw"] is not None]
    thermal_central = [r["thermal_central_mw"] for r in rows if r["thermal_central_mw"] is not None]
    thermal_p90 = [r["thermal_p90_mw"] for r in rows if r["thermal_p90_mw"] is not None]

    return {
        "periods": len(rows),
        "periods_without_forecast": sum(1 for r in rows if r["forecast_mw"] is None),
        "periods_scored": len(scored),
        "mean_horizon_hours": sum(horizons) / len(horizons) if horizons else None,
        "accuracy": summarize_errors(
            [r["error_mw"] for r in scored], [r["actual_mw"] for r in scored]
        ),
        "coverage_rate": sum(coverage) / len(coverage) if coverage else None,
        "planning_buffer_mwh": 0.5 * sum(buffers_total) if buffers_total else None,
        "covered_wind_energy_mwh": 0.5 * sum(covered_total) if covered_total else None,
        "thermal_central_mwh": 0.5 * sum(thermal_central) if demand_mw is not None else None,
        "thermal_p90_mwh": 0.5 * sum(thermal_p90) if demand_mw is not None else None,
        "buffers_mw": buffers.mw_by_bucket,
        "buffer_sources": buffers.source_by_bucket,
        "calibration_samples": buffers.samples_by_bucket,
        "calibration_sample_total": len(samples),
    }


def accuracy_report(
    days: list[date],
    forecasts_by_target: dict[datetime, list[Forecast]],
    actuals: dict[datetime, float],
    **kwargs,
) -> dict:
    """Out-of-sample accuracy of the latest-before-gate-closure forecast over many days.

    Each day is evaluated with calibration from earlier data only, so the coverage
    numbers are honest out-of-sample estimates.
    """
    per_day = []
    pooled: list[tuple[str, float, float]] = []  # (bucket, error, actual)
    all_hits: list[bool] = []
    for d in days:
        dec = build_decision(d, forecasts_by_target, actuals, demand_mw=None, **kwargs)
        for r in dec["periods"]:
            if r["error_mw"] is not None:
                pooled.append((r["horizon_bucket"], r["error_mw"], r["actual_mw"]))
            if r["within_coverage"] is not None:
                all_hits.append(r["within_coverage"])
        per_day.append(
            {
                "delivery_date": d,
                "accuracy": dec["summary"]["accuracy"],
                "coverage_rate": dec["summary"]["coverage_rate"],
                "periods_scored": dec["summary"]["periods_scored"],
            }
        )

    def block(items: list[tuple[str, float, float]]) -> dict:
        return summarize_errors([e for _, e, _ in items], [a for _, _, a in items])

    return {
        "overall": block(pooled),
        "coverage_rate": sum(all_hits) / len(all_hits) if all_hits else None,
        "by_horizon": {
            label: block([p for p in pooled if p[0] == label]) for label in BUCKET_LABELS
        },
        "per_day": per_day,
    }
