"""Runtime configuration, read from environment variables with safe defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Settings:
    data_source: str  # "elexon" (live API) or "sample" (synthetic, offline)
    elexon_base_url: str
    decision_timezone: str
    gate_closure_hour: int  # local hour on D-1 when day-ahead buying closes
    calibration_lookback_days: int
    buffer_quantile: float
    min_calibration_samples: int
    cors_origins: list[str]
    decision_start: date
    decision_end: date
    data_window_start: date
    data_window_end: date  # exclusive


def get_settings() -> Settings:
    env = os.environ
    origins = env.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8080")
    return Settings(
        data_source=env.get("DATA_SOURCE", "sample"),
        elexon_base_url=env.get("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1"),
        decision_timezone=env.get("DECISION_TIMEZONE", "Europe/London"),
        gate_closure_hour=int(env.get("GATE_CLOSURE_HOUR", "11")),
        calibration_lookback_days=int(env.get("CALIBRATION_LOOKBACK_DAYS", "14")),
        buffer_quantile=float(env.get("BUFFER_QUANTILE", "0.9")),
        min_calibration_samples=int(env.get("MIN_CALIBRATION_SAMPLES", "20")),
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        # Scope from the brief: purchase decisions in January 2026 only.
        decision_start=date(2026, 1, 1),
        decision_end=date(2026, 1, 31),
        # Extra history before January is needed to calibrate early-January decisions.
        data_window_start=date(2025, 12, 1),
        data_window_end=date(2026, 2, 1),
    )
