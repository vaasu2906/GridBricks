from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app import core
from app.core import Forecast, fit_buffers, latest_forecast_before, quantile

UTC = timezone.utc
LONDON = ZoneInfo("Europe/London")


def test_settlement_periods_january_has_48():
    periods = core.settlement_periods(date(2026, 1, 15), LONDON)
    assert len(periods) == 48
    assert periods[0] == datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    assert periods[-1] == datetime(2026, 1, 15, 23, 30, tzinfo=UTC)


def test_settlement_periods_spring_clock_change_has_46():
    # UK clocks go forward on Sunday 29 March 2026.
    periods = core.settlement_periods(date(2026, 3, 29), LONDON)
    assert len(periods) == 46


def test_gate_closure_is_11_london_on_previous_day():
    cutoff = core.gate_closure_utc(date(2026, 1, 15), LONDON, 11)
    # January is GMT (UTC+0), so 11:00 local == 11:00 UTC on 14 January.
    assert cutoff == datetime(2026, 1, 14, 11, 0, tzinfo=UTC)


def test_latest_forecast_ignores_publications_after_cutoff():
    target = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    cutoff = datetime(2026, 1, 14, 11, 0, tzinfo=UTC)
    fcs = [
        Forecast(target, datetime(2026, 1, 14, 9, 0, tzinfo=UTC), 1000.0),
        Forecast(target, datetime(2026, 1, 14, 10, 30, tzinfo=UTC), 1200.0),
        Forecast(target, datetime(2026, 1, 14, 11, 30, tzinfo=UTC), 9999.0),  # after cutoff
    ]
    chosen = latest_forecast_before(fcs, cutoff)
    assert chosen is not None
    assert chosen.generation_mw == 1200.0


def test_quantile_linear_interpolation():
    assert quantile([1.0, 2.0, 3.0, 4.0], 0.5) == pytest.approx(2.5)
    assert quantile([10.0], 0.9) == 10.0
    assert quantile([0.0, 10.0], 0.9) == pytest.approx(9.0)


def test_fit_buffers_never_negative_and_falls_back_to_pooled():
    samples = [("12-24h", -50.0)] * 5 + [("24-48h", 100.0)] * 30
    buf = fit_buffers(samples, q=0.9, min_samples=20)
    # Only 5 in-bucket samples -> pooled fallback over all 35 (its 90th percentile is 100).
    assert buf.source_by_bucket["12-24h"] == "pooled"
    assert buf.mw_by_bucket["12-24h"] == pytest.approx(100.0)
    assert buf.source_by_bucket["24-48h"] == "bucket"
    assert buf.mw_by_bucket["24-48h"] == pytest.approx(100.0)
    assert buf.source_by_bucket["48h+"] == "pooled"  # empty bucket -> pooled fallback
    assert all(v >= 0 for v in buf.mw_by_bucket.values())

    # Not enough data even pooled -> zero buffer, flagged as "none".
    sparse = fit_buffers([("24-48h", 50.0)] * 3, q=0.9, min_samples=20)
    assert sparse.source_by_bucket["12-24h"] == "none"
    assert sparse.mw_by_bucket["12-24h"] == 0.0


def test_buffer_is_never_negative():
    samples = [("24-48h", -300.0)] * 30  # forecasts always too low -> no buffer needed
    buf = fit_buffers(samples, q=0.9, min_samples=20)
    assert buf.mw_by_bucket["24-48h"] == 0.0


def test_calibration_excludes_delivery_day_minus_one():
    """With lookback=2 only D-2 may contribute; D-1 must never be used."""
    delivery = date(2026, 1, 15)
    day_minus_2 = date(2026, 1, 13)
    day_minus_1 = date(2026, 1, 14)
    forecasts, actuals = {}, {}
    for d, err in ((day_minus_2, 10.0), (day_minus_1, 99999.0)):
        cutoff = core.gate_closure_utc(d, LONDON, 11)
        for t in core.settlement_periods(d, LONDON):
            actuals[t] = 1000.0
            forecasts[t] = [Forecast(t, cutoff - timedelta(hours=1), 1000.0 + err)]
    samples = core.calibration_samples(
        delivery, forecasts, actuals, tz=LONDON, closure_hour=11, lookback_days=2
    )
    assert len(samples) == 48
    assert all(err == pytest.approx(10.0) for _, err in samples)


def test_build_decision_coverage_is_consistent():
    delivery = date(2026, 1, 15)
    day_minus_2 = date(2026, 1, 13)
    forecasts, actuals = {}, {}
    for d in (day_minus_2, delivery):
        cutoff = core.gate_closure_utc(d, LONDON, 11)
        for t in core.settlement_periods(d, LONDON):
            actuals[t] = 2000.0
            forecasts[t] = [Forecast(t, cutoff - timedelta(hours=1), 2100.0)]
    dec = core.build_decision(
        delivery, forecasts, actuals,
        tz=LONDON, closure_hour=11, lookback_days=2, buffer_quantile=0.9, min_samples=10,
        demand_mw=5000.0,
    )
    for row in dec["periods"]:
        assert row["covered_wind_mw"] <= row["forecast_mw"]
        assert row["thermal_p90_mw"] >= row["thermal_central_mw"]
    assert dec["summary"]["periods_scored"] == 48
