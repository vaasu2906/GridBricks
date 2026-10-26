from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.sample_source import SyntheticWindSource


def client() -> TestClient:
    return TestClient(create_app(get_settings(), SyntheticWindSource()))


def test_health_and_meta():
    c = client()
    assert c.get("/api/health").json() == {"status": "ok"}
    meta = c.get("/api/meta").json()
    assert meta["source"] == "sample"
    assert meta["gate_closure_hour"] == 11


def test_decision_returns_48_periods_with_no_lookahead_fields():
    r = client().get("/api/decision", params={"delivery_date": "2026-01-15", "demand_mw": 20000})
    assert r.status_code == 200
    body = r.json()
    assert len(body["periods"]) == 48
    assert body["decision_cutoff"].startswith("2026-01-14T11:00:00")
    assert body["summary"]["periods_without_forecast"] == 0
    for p in body["periods"]:
        assert p["publish_time"] <= body["decision_cutoff"]
        assert p["horizon_hours"] > 0


def test_decision_rejects_out_of_scope_dates():
    assert client().get("/api/decision", params={"delivery_date": "2026-02-01"}).status_code == 400


def test_accuracy_range_reports_each_day():
    r = client().get("/api/accuracy", params={"start_date": "2026-01-10", "end_date": "2026-01-12"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["per_day"]) == 3
    assert body["overall"]["n"] == 3 * 48
    assert set(body["by_horizon"]) == {"<12h", "12-24h", "24-48h", "48h+"}


def test_vintages_mark_exactly_one_chosen():
    r = client().get(
        "/api/forecast-vintages",
        params={"target_time": "2026-01-15T12:00:00Z", "delivery_date": "2026-01-15"},
    )
    assert r.status_code == 200
    vintages = r.json()["vintages"]
    assert sum(v["chosen"] for v in vintages) == 1
    assert all(v["published_before_cutoff"] or not v["chosen"] for v in vintages)
