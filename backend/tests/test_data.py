from datetime import datetime, timezone

from app.core import Forecast
from app.data import fill_half_hour_forecasts

UTC = timezone.utc


def test_half_hour_periods_reuse_the_hours_forecast():
    hour = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    pub = datetime(2026, 1, 14, 9, 30, tzinfo=UTC)
    by_target = {hour: [Forecast(hour, pub, 15828.0)]}
    filled = fill_half_hour_forecasts(by_target)
    half = datetime(2026, 1, 15, 0, 30, tzinfo=UTC)
    assert filled[half] == [Forecast(hour, pub, 15828.0)]
    assert filled[hour] == by_target[hour]


def test_existing_half_hour_forecasts_are_not_overwritten():
    hour = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    half = datetime(2026, 1, 15, 0, 30, tzinfo=UTC)
    own = [Forecast(half, datetime(2026, 1, 14, 9, 0, tzinfo=UTC), 111.0)]
    by_target = {hour: [Forecast(hour, datetime(2026, 1, 14, 9, 30, tzinfo=UTC), 222.0)], half: own}
    filled = fill_half_hour_forecasts(by_target)
    assert filled[half] == own
