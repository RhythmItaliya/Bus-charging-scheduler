import pytest
from scheduler.physics import (
    base_arrival_minutes,
    minutes_to_hhmm,
    travel_minutes,
)


class TestTravelMinutes:

    def test_100km_at_60kmph_is_100_minutes(self):
        assert travel_minutes(100, 60) == pytest.approx(100.0)

    def test_120km_at_60kmph_is_120_minutes(self):
        assert travel_minutes(120, 60) == pytest.approx(120.0)

    def test_540km_total_at_60kmph_is_540_minutes(self):
        assert travel_minutes(540, 60) == pytest.approx(540.0)

    def test_non_default_speed_80kmph(self):
        assert travel_minutes(100, 80) == pytest.approx(75.0)

    def test_non_default_speed_120kmph(self):
        assert travel_minutes(120, 120) == pytest.approx(60.0)

    def test_zero_distance(self):
        assert travel_minutes(0, 60) == pytest.approx(0.0)

    def test_invalid_speed_raises(self):
        with pytest.raises(ValueError):
            travel_minutes(100, 0)
        with pytest.raises(ValueError):
            travel_minutes(100, -10)


class TestBaseArrivalMinutes:

    def test_bk_bus_arrives_at_A_after_100_min(self):
        arrival = base_arrival_minutes(departure_min=1140, cumulative_distance_km=100, speed_kmph=60)
        assert arrival == pytest.approx(1240.0)

    def test_bk_bus_arrives_at_B_after_220_min(self):
        arrival = base_arrival_minutes(departure_min=1140, cumulative_distance_km=220, speed_kmph=60)
        assert arrival == pytest.approx(1360.0)

    def test_kb_bus_arrives_at_D_after_100_min(self):
        arrival = base_arrival_minutes(departure_min=1140, cumulative_distance_km=100, speed_kmph=60)
        assert arrival == pytest.approx(1240.0)

    def test_different_departure_time(self):
        arrival = base_arrival_minutes(departure_min=1200, cumulative_distance_km=100, speed_kmph=60)
        assert arrival == pytest.approx(1300.0)


class TestMinutesToHHMM:

    def test_midnight(self):
        assert minutes_to_hhmm(0) == "00:00"

    def test_19h_00m(self):
        assert minutes_to_hhmm(1140) == "19:00"

    def test_20h_00m(self):
        assert minutes_to_hhmm(1200) == "20:00"

    def test_19h_08m(self):
        assert minutes_to_hhmm(1148) == "19:08"

    def test_rounding(self):
        assert minutes_to_hhmm(1140.4) == "19:00"
        assert minutes_to_hhmm(1140.6) == "19:01"

    def test_23h_59m(self):
        assert minutes_to_hhmm(1439) == "23:59"

    def test_midnight_wrap(self):
        assert minutes_to_hhmm(1440) == "00:00"
