"""Response models for the HTTP API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class PeriodOut(BaseModel):
    start_time: datetime
    forecast_mw: float | None
    publish_time: datetime | None
    horizon_hours: float | None
    horizon_bucket: str | None
    buffer_mw: float | None
    covered_wind_mw: float | None
    actual_mw: float | None
    error_mw: float | None
    within_coverage: bool | None
    thermal_central_mw: float | None
    thermal_p90_mw: float | None


class AccuracyBlock(BaseModel):
    n: int
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    nmae_pct: float | None


class DecisionSummary(BaseModel):
    periods: int
    periods_without_forecast: int
    periods_scored: int
    mean_horizon_hours: float | None
    accuracy: AccuracyBlock
    coverage_rate: float | None
    planning_buffer_mwh: float | None
    covered_wind_energy_mwh: float | None
    thermal_central_mwh: float | None
    thermal_p90_mwh: float | None
    buffers_mw: dict[str, float]
    buffer_sources: dict[str, str]
    calibration_samples: dict[str, int]
    calibration_sample_total: int


class DecisionOut(BaseModel):
    delivery_date: date
    decision_cutoff: datetime
    timezone: str
    source: str
    demand_mw: float | None
    summary: DecisionSummary
    periods: list[PeriodOut]


class DayAccuracy(BaseModel):
    delivery_date: date
    accuracy: AccuracyBlock
    coverage_rate: float | None
    periods_scored: int


class AccuracyOut(BaseModel):
    start_date: date
    end_date: date
    source: str
    overall: AccuracyBlock
    coverage_rate: float | None
    by_horizon: dict[str, AccuracyBlock]
    per_day: list[DayAccuracy]


class VintageOut(BaseModel):
    publish_time: datetime
    horizon_hours: float
    forecast_mw: float
    chosen: bool
    published_before_cutoff: bool


class VintagesOut(BaseModel):
    target_time: datetime
    delivery_date: date
    decision_cutoff: datetime
    vintages: list[VintageOut]


class MetaOut(BaseModel):
    source: str
    decision_start: date
    decision_end: date
    timezone: str
    gate_closure_hour: int
    calibration_lookback_days: int
    buffer_quantile: float
    settlement_period_minutes: int = 30
