"""
tests/test_physics.py — Unit tests for travel-time arithmetic.

Covers:
  • travel_minutes: 100 km @ 60 km/h = 100 min; 120 km = 120 min.
  • base_arrival_minutes: departure + cumulative distance / speed.
  • Non-default speed: 80 km/h gives different times.
  • minutes_to_hhmm: 1140 → "19:00", edge cases.

References:
    docs/07-testing/01-testing-plan.md (test_physics.py requirements)
    scheduler/physics.py
"""

import pytest
from scheduler.physics import (
    base_arrival_minutes,
    minutes_to_hhmm,
    travel_minutes,
)


class TestTravelMinutes:
    """Test the travel_minutes(distance, speed) → minutes calculation."""

    def test_100km_at_60kmph_is_100_minutes(self):
        """Standard: 100 km at 60 km/h = 100 min (key spec fact)."""
        assert travel_minutes(100, 60) == pytest.approx(100.0)

    def test_120km_at_60kmph_is_120_minutes(self):
        """120 km segment (A→B, C→D) at 60 km/h = 120 min."""
        assert travel_minutes(120, 60) == pytest.approx(120.0)

    def test_540km_total_at_60kmph_is_540_minutes(self):
        """Total route 540 km at 60 km/h = 540 min (9 hours)."""
        assert travel_minutes(540, 60) == pytest.approx(540.0)

    def test_non_default_speed_80kmph(self):
        """Non-default speed: 100 km @ 80 km/h = 75 min."""
        assert travel_minutes(100, 80) == pytest.approx(75.0)

    def test_non_default_speed_120kmph(self):
        """High speed: 120 km @ 120 km/h = 60 min."""
        assert travel_minutes(120, 120) == pytest.approx(60.0)

    def test_zero_distance(self):
        """Zero distance = zero travel time."""
        assert travel_minutes(0, 60) == pytest.approx(0.0)

    def test_invalid_speed_raises(self):
        """Speed ≤ 0 must raise ValueError."""
        with pytest.raises(ValueError):
            travel_minutes(100, 0)
        with pytest.raises(ValueError):
            travel_minutes(100, -10)


class TestBaseArrivalMinutes:
    """Test base_arrival_minutes: departure + physics-only travel."""

    def test_bk_bus_arrives_at_A_after_100_min(self):
        """Bus departs Bengaluru at 19:00 (1140). A is 100 km → arrive 1240."""
        arrival = base_arrival_minutes(departure_min=1140, cumulative_distance_km=100, speed_kmph=60)
        assert arrival == pytest.approx(1240.0)

    def test_bk_bus_arrives_at_B_after_220_min(self):
        """B is 220 km from Bengaluru → arrive at 1140 + 220 = 1360."""
        arrival = base_arrival_minutes(departure_min=1140, cumulative_distance_km=220, speed_kmph=60)
        assert arrival == pytest.approx(1360.0)

    def test_kb_bus_arrives_at_D_after_100_min(self):
        """KB bus: D is 100 km from Kochi → arrive 1140 + 100 = 1240."""
        arrival = base_arrival_minutes(departure_min=1140, cumulative_distance_km=100, speed_kmph=60)
        assert arrival == pytest.approx(1240.0)

    def test_different_departure_time(self):
        """Bus departing at 20:00 (1200) to A (100 km) arrives at 1300."""
        arrival = base_arrival_minutes(departure_min=1200, cumulative_distance_km=100, speed_kmph=60)
        assert arrival == pytest.approx(1300.0)


class TestMinutesToHHMM:
    """Test HH:MM formatting of minute values."""

    def test_midnight(self):
        assert minutes_to_hhmm(0) == "00:00"

    def test_19h_00m(self):
        assert minutes_to_hhmm(1140) == "19:00"

    def test_20h_00m(self):
        assert minutes_to_hhmm(1200) == "20:00"

    def test_19h_08m(self):
        assert minutes_to_hhmm(1148) == "19:08"

    def test_rounding(self):
        """Float minutes are rounded to nearest minute."""
        assert minutes_to_hhmm(1140.4) == "19:00"
        assert minutes_to_hhmm(1140.6) == "19:01"

    def test_23h_59m(self):
        assert minutes_to_hhmm(1439) == "23:59"

    def test_midnight_wrap(self):
        """Values ≥ 1440 wrap via %24 (minutes beyond midnight)."""
        assert minutes_to_hhmm(1440) == "00:00"
