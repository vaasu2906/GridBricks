"""FastAPI application: decision view, accuracy report and forecast vintages."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import core
from .config import Settings, get_settings
from .data import DataService, DataSource
from .elexon import ElexonClient
from .sample_source import SyntheticWindSource
from .schemas import AccuracyOut, DecisionOut, MetaOut, VintagesOut


def create_source(settings: Settings) -> DataSource:
    if settings.data_source == "elexon":
        return ElexonClient(settings.elexon_base_url)
    if settings.data_source == "sample":
        return SyntheticWindSource()
    raise ValueError(f"Unknown DATA_SOURCE={settings.data_source!r} (use 'elexon' or 'sample')")


def create_app(settings: Settings | None = None, source: DataSource | None = None) -> FastAPI:
    settings = settings or get_settings()
    source = source or create_source(settings)
    service = DataService(source, settings.data_window_start, settings.data_window_end)
    tz = ZoneInfo(settings.decision_timezone)

    app = FastAPI(title="Wind Forecast Portal API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    def calc_kwargs() -> dict:
        return dict(
            tz=tz,
            closure_hour=settings.gate_closure_hour,
            lookback_days=settings.calibration_lookback_days,
            buffer_quantile=settings.buffer_quantile,
            min_samples=settings.min_calibration_samples,
        )

    def check_in_scope(*days: date) -> None:
        for d in days:
            if not settings.decision_start <= d <= settings.decision_end:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Decision dates must be between {settings.decision_start} "
                        f"and {settings.decision_end}"
                    ),
                )

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/meta", response_model=MetaOut)
    def meta() -> dict:
        return {
            "source": source.name,
            "decision_start": settings.decision_start,
            "decision_end": settings.decision_end,
            "timezone": settings.decision_timezone,
            "gate_closure_hour": settings.gate_closure_hour,
            "calibration_lookback_days": settings.calibration_lookback_days,
            "buffer_quantile": settings.buffer_quantile,
        }

    @app.get("/api/decision", response_model=DecisionOut)
    def decision(
        delivery_date: date,
        demand_mw: float | None = Query(default=None, ge=0, le=100_000),
    ) -> dict:
        check_in_scope(delivery_date)
        ds = service.get()
        dec = core.build_decision(
            delivery_date,
            ds.forecasts_by_target,
            ds.actuals,
            demand_mw=demand_mw,
            **calc_kwargs(),
        )
        return {
            "delivery_date": dec["delivery_date"],
            "decision_cutoff": dec["decision_cutoff"],
            "timezone": settings.decision_timezone,
            "source": ds.source,
            "demand_mw": demand_mw,
            "summary": dec["summary"],
            "periods": dec["periods"],
        }

    @app.get("/api/accuracy", response_model=AccuracyOut)
    def accuracy(
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        start = start_date or settings.decision_start
        end = end_date or settings.decision_end
        if end < start:
            raise HTTPException(status_code=400, detail="end_date must not precede start_date")
        check_in_scope(start, end)
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        ds = service.get()
        rep = core.accuracy_report(days, ds.forecasts_by_target, ds.actuals, **calc_kwargs())
        return {
            "start_date": start,
            "end_date": end,
            "source": ds.source,
            "overall": rep["overall"],
            "coverage_rate": rep["coverage_rate"],
            "by_horizon": rep["by_horizon"],
            "per_day": rep["per_day"],
        }

    @app.get("/api/forecast-vintages", response_model=VintagesOut)
    def vintages(target_time: datetime, delivery_date: date) -> dict:
        check_in_scope(delivery_date)
        ds = service.get()
        if target_time.tzinfo is None:
            raise HTTPException(status_code=400, detail="target_time must include a timezone offset")
        cutoff = core.gate_closure_utc(delivery_date, tz, settings.gate_closure_hour)
        key = target_time.astimezone(timezone.utc)
        return {
            "target_time": key,
            "delivery_date": delivery_date,
            "decision_cutoff": cutoff,
            "vintages": core.forecast_vintages(key, ds.forecasts_by_target.get(key, []), cutoff),
        }

    return app


app = create_app()
