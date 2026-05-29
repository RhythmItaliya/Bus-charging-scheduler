"""
scheduler/config.py — Centralised default constants.

All physical defaults live here so that every plausibly-changing world
parameter is a single, named value.  The scenario JSON can override any of
these per-scenario; if a key is absent the loader falls back to these defaults.

References:
    docs/01-architecture/01-system-architecture.md  (data-driven world)
    docs/03-data-model/01-data-model-design.md       (field-level design)
    docs/03-data-model/02-scenario-schema.md         (`world` keys optional)
"""

# ---------------------------------------------------------------------------
# Physical world defaults (overridable per scenario via the "world" JSON key)
# ---------------------------------------------------------------------------

DEFAULTS: dict = {
    # Speed used to derive travel time: distance(km) / speed = travel_time(min).
    # Assumption: constant 60 km/h (documented in README / ARCHITECTURE).
    "speed_kmph": 60,

    # Every charge always refills to full and takes exactly this many minutes.
    # Hard rule H4 — no partial charging permitted.
    "charge_minutes": 25,

    # Maximum km a bus can travel between two consecutive charges (or
    # origin→first-charge or last-charge→destination).
    # Hard rule H1 / R14 / R18.
    "battery_range_km": 240,
}

# ---------------------------------------------------------------------------
# Scenario data directory (relative to project root)
# ---------------------------------------------------------------------------

SCENARIOS_DIR: str = "data/scenarios"

# ---------------------------------------------------------------------------
# Soft-weight defaults — used when a weight key is missing from the scenario.
# R23: weights live only in the scenario file; engine code NEVER hardcodes a
# weight value — it always looks up ctx.weights[key], defaulting to 1.0.
# ---------------------------------------------------------------------------

DEFAULT_WEIGHT: float = 1.0
