"""Deterministic SYNTHETIC wind data for development, tests and offline demos.

This is NOT Elexon data. It exists so the app can run when the live API is unreachable
(e.g. from a locked-down build environment). Generation is a mean-reverting process;
forecast errors have a shared component per target period plus per-vintage noise, and
both grow with lead time, with a mild over-forecast bias at long leads.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from .core import SETTLEMENT_PERIOD, Forecast, Observation

UTC = timezone.utc
ANCHOR = datetime(2025, 10, 1, tzinfo=UTC)
MEAN_MW = 8000.0
MIN_MW = 150.0
MAX_MW = 17000.0


class SyntheticWindSource:
    name = "sample"

    def __init__(self, seed: int = 20260101, vintage_every_hours: int = 3, max_lead_hours: int = 60):
        self._seed = seed
        self._every = vintage_every_hours
        self._max_lead = max_lead_hours
        self._rng = random.Random(f"{seed}-actual")
        self._actual: dict[datetime, float] = {}
        self._generated_until = ANCHOR
        self._last = MEAN_MW

    def _extend_to(self, end: datetime) -> None:
        while self._generated_until < end:
            x = 0.985 * self._last + 0.015 * MEAN_MW + self._rng.gauss(0, 420)
            x = min(max(x, MIN_MW), MAX_MW)
            self._actual[self._generated_until] = x
            self._last = x
            self._generated_until += SETTLEMENT_PERIOD

    def fetch_actuals(self, start: datetime, end: datetime) -> list[Observation]:
        self._extend_to(end)
        return [
            Observation(t, v, t + timedelta(hours=2))
            for t, v in sorted(self._actual.items())
            if start <= t < end
        ]

    def fetch_forecasts(self, start: datetime, end: datetime) -> list[Forecast]:
        self._extend_to(end)
        out: list[Forecast] = []
        for t in sorted(self._actual):
            if not start <= t < end:
                continue
            actual = self._actual[t]
            common = random.Random(f"{self._seed}-common-{t.isoformat()}").gauss(0, 1)
            for lead in range(self._every, self._max_lead + 1, self._every):
                sd = 350.0 + 90.0 * math.sqrt(lead)
                bias = 150.0 * lead / 48.0
                noise = random.Random(f"{self._seed}-v-{t.isoformat()}-{lead}").gauss(0, 1)
                value = actual + bias + sd * (0.85 * common + 0.5 * noise)
                out.append(
                    Forecast(
                        target_time=t,
                        publish_time=t - timedelta(hours=lead),
                        generation_mw=max(0.0, value),
                    )
                )
        return out
