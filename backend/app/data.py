"""Data access layer: loads actuals and forecasts once and serves them from memory."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol

from .core import Forecast, Observation


class DataSource(Protocol):
    name: str

    def fetch_actuals(self, start: datetime, end: datetime) -> list[Observation]: ...

    def fetch_forecasts(self, start: datetime, end: datetime) -> list[Forecast]: ...


@dataclass(frozen=True)
class Dataset:
    source: str
    actuals: dict[datetime, float]
    forecasts_by_target: dict[datetime, list[Forecast]]


def fill_half_hour_forecasts(by_target: dict[datetime, list[Forecast]]) -> dict[datetime, list[Forecast]]:
    """Give half-hour settlement periods the forecast of their hour when none exists.

    Elexon WINDFOR is published at whole-hour resolution: each forecast covers the hour
    starting at its ``startTime``, which contains two settlement periods. Where a
    half-hour period has no forecast of its own, it reuses the forecasts for the hour
    that contains it. Periods that already have forecasts (e.g. synthetic data) are untouched.
    """
    filled = dict(by_target)
    for target, forecasts in by_target.items():
        if target.minute != 0:
            continue
        half = target + timedelta(minutes=30)
        if half not in filled:
            filled[half] = list(forecasts)
    return filled


class DataService:
    """Lazily loads the in-scope window on first use (thread-safe, then cached)."""

    def __init__(self, source: DataSource, window_start: date, window_end: date) -> None:
        self._source = source
        self._start = datetime.combine(window_start, time(0), tzinfo=timezone.utc)
        self._end = datetime.combine(window_end, time(0), tzinfo=timezone.utc)
        self._lock = threading.Lock()
        self._dataset: Dataset | None = None

    def get(self) -> Dataset:
        with self._lock:
            if self._dataset is None:
                self._dataset = self._load()
            return self._dataset

    def _load(self) -> Dataset:
        observations = self._source.fetch_actuals(self._start, self._end)
        forecasts = self._source.fetch_forecasts(self._start, self._end)
        by_target: dict[datetime, list[Forecast]] = defaultdict(list)
        for f in forecasts:
            by_target[f.target_time].append(f)
        return Dataset(
            source=self._source.name,
            actuals={o.start_time: o.generation_mw for o in observations},
            forecasts_by_target=fill_half_hour_forecasts(dict(by_target)),
        )
