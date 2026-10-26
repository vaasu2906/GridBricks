"""Client for the Elexon BMRS Insights API (FUELHH and WINDFOR stream datasets).

Only national-level wind is used:
* FUELHH  -> actual generation, rows where ``fuelType == "WIND"``
* WINDFOR -> wind generation forecasts with ``publishTime`` (forecast creation time)

Requests are chunked by publish-time day to keep payloads small. Base URL and
parameter names are configurable because Elexon has moved its hosts over time;
verify them against https://bmrs.elexon.co.uk/api-documentation before going live.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from .core import Forecast, Observation

UTC = timezone.utc


def parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    """Implements the ``DataSource`` protocol against the live Elexon API."""

    name = "elexon"
    FUEL_DATASET = "FUELHH"
    FORECAST_DATASET = "WINDFOR"
    # Actuals are published some time after the settlement period; look a little past the window.
    ACTUAL_PUBLISH_LAG = timedelta(days=2)
    # Forecasts used for a target period can be published up to this long before it.
    FORECAST_MAX_LEAD = timedelta(days=3)

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._http = httpx.Client(timeout=timeout, transport=transport)

    # -- DataSource -------------------------------------------------------------

    def fetch_actuals(self, start: datetime, end: datetime) -> list[Observation]:
        rows = self._stream_chunked(self.FUEL_DATASET, start, end + self.ACTUAL_PUBLISH_LAG)
        out: list[Observation] = []
        for r in rows:
            if r.get("fuelType") != "WIND":
                continue
            t = parse_ts(r["startTime"])
            if start <= t < end:
                publish = parse_ts(r["publishTime"]) if r.get("publishTime") else None
                out.append(Observation(t, float(r["generation"]), publish))
        return out

    def fetch_forecasts(self, start: datetime, end: datetime) -> list[Forecast]:
        rows = self._stream_chunked(self.FORECAST_DATASET, start - self.FORECAST_MAX_LEAD, end)
        out: list[Forecast] = []
        for r in rows:
            t = parse_ts(r["startTime"])
            if start <= t < end:
                out.append(
                    Forecast(
                        target_time=t,
                        publish_time=parse_ts(r["publishTime"]),
                        generation_mw=float(r["generation"]),
                    )
                )
        return out

    # -- HTTP -------------------------------------------------------------------

    def _stream_chunked(self, dataset: str, start: datetime, end: datetime) -> list[dict]:
        rows: list[dict] = []
        cur = start
        while cur < end:
            nxt = min(cur + timedelta(days=1), end)
            rows.extend(
                self._stream(
                    dataset,
                    {"publishDateTimeFrom": _iso(cur), "publishDateTimeTo": _iso(nxt)},
                )
            )
            cur = nxt
        return rows

    def _stream(self, dataset: str, params: dict[str, str]) -> list[dict]:
        resp = self._http.get(f"{self._base}/datasets/{dataset}/stream", params=params)
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):  # tolerate a wrapped {"data": [...]} response
            payload = payload.get("data", [])
        return payload
