"""
scheduler/config.py — Single source of truth for every configurable value.

USAGE:
    from scheduler.config import CONFIG

    CONFIG.scenarios_dir          # "data/scenarios"
    CONFIG.speed_kmph             # 60.0
    CONFIG.page_title             # "Bus Charging Scheduler"
    CONFIG.weight_slider_max      # 5.0
    CONFIG.wait_crit_min          # 30  (minutes above which wait turns red)

WHY ONE FILE?
    The PDF explicitly says "changing a weight must be trivial — a value in
    one obvious place, not scattered across code."  We extend that principle
    to every tunable value in the project: UI labels, slider bounds, colour
    thresholds, log level, scenario path.  One file to rule them all.

BACKWARD COMPATIBILITY:
    The module-level names DEFAULTS, SCENARIOS_DIR, DEFAULT_WEIGHT are kept
    so existing imports in loader.py and sidebar.py continue to work without
    change.  New code should always import CONFIG.

WHAT LIVES HERE:
    ┌─ Physical defaults ─────────── world constants (override per scenario JSON)
    ├─ Paths ─────────────────────── where to find scenario files
    ├─ Logging ───────────────────── env var and default level
    ├─ UI — page ─────────────────── Streamlit page_config values
    ├─ UI — weight sliders ───────── min / max / step shared by 3 sliders
    └─ UI — wait colour thresholds ── yellow and red bands in tables + terminal

WHAT DOES NOT LIVE HERE:
    - Rule weights (those live in the scenario JSON — user controlled)
    - Operator names, station names, route geometry (all in scenario JSON)
    - Any value that changes per run or per user session
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """
    Immutable application configuration.  All defaults are set here.
    To customise a value, change it in this class — one edit, one place.

    The dataclass is frozen so that importing code cannot accidentally mutate
    global state; the singleton CONFIG below is the only instance you need.
    """

    # ── Physical world defaults ───────────────────────────────────────────
    # These are the fallback values used by loader.py when a scenario JSON
    # does not supply a "world" block.  A scenario can always override them.

    speed_kmph: float = 60.0
    """Travel speed in km/h.  100 km / 60 km/h = 100 min (clean math)."""

    charge_minutes: int = 25
    """Minutes every charge takes — hard rule H4: always exactly this."""

    battery_range_km: float = 240.0
    """Maximum km a bus can travel between charges — hard rule H1."""

    default_weight: float = 1.0
    """Fallback multiplier for any soft-rule weight not found in a scenario."""

    # ── Paths ─────────────────────────────────────────────────────────────
    scenarios_dir: str = "data/scenarios"
    """Directory (relative to project root) where scenario JSON files live."""

    # ── Logging ───────────────────────────────────────────────────────────
    log_level_env_var: str = "BCS_LOG_LEVEL"
    """
    Name of the environment variable that controls log verbosity.
    Set to DEBUG to see every charger reservation; INFO shows committed buses.
    Valid values: DEBUG, INFO, WARN, ERROR.

    Example:
        BCS_LOG_LEVEL=DEBUG python -m scheduler.engine data/scenarios/scenario_1.json
    """

    default_log_level: str = "INFO"
    """Log level used when the env var is absent or unrecognised."""

    # ── UI — Streamlit page settings ──────────────────────────────────────
    page_title: str = "Bus Charging Scheduler"
    """Browser tab title and window caption."""

    page_icon: str = "⚡"
    """Favicon shown in the browser tab."""

    page_layout: str = "wide"
    """Streamlit layout mode — 'wide' uses the full browser width."""

    sidebar_state: str = "expanded"
    """Sidebar starts open so the scenario dropdown is immediately visible."""

    # ── UI — Weight sliders ───────────────────────────────────────────────
    # All three weight sliders (Individual, Operator, Overall) share the same
    # range and step.  Change here to apply to all three simultaneously.

    weight_slider_min: float = 0.0
    """Minimum weight value.  0.0 = rule is fully silenced."""

    weight_slider_max: float = 5.0
    """Maximum weight value.  Practical upper bound for demonstration."""

    weight_slider_step: float = 0.5
    """Slider increment.  0.5 gives clean half-integer steps."""

    # ── UI — Wait time colour thresholds ─────────────────────────────────
    # These drive the yellow / red colour coding in both the Streamlit tables
    # and the rich terminal output.  One value, consumed in three places.

    wait_warn_min: int = 1
    """Waits >= this many minutes are shown in yellow (moderate queue)."""

    wait_crit_min: int = 30
    """Waits > this many minutes are shown in red (long queue — high S1 cost)."""


# ── Singleton ─────────────────────────────────────────────────────────────────
# Import this object everywhere instead of importing individual constants.
#
#   from scheduler.config import CONFIG
#   CONFIG.scenarios_dir      # "data/scenarios"
#   CONFIG.wait_crit_min      # 30
#
CONFIG = AppConfig()


# ── Backward-compatible module-level aliases ──────────────────────────────────
# These names were used in scheduler/loader.py and frontend/sidebar.py before
# AppConfig was introduced.  They are kept so that any import that worked
# before continues to work unchanged.

DEFAULTS: dict = {
    "speed_kmph":       CONFIG.speed_kmph,
    "charge_minutes":   CONFIG.charge_minutes,
    "battery_range_km": CONFIG.battery_range_km,
}
"""Backward-compat dict for loader.py.  New code should use CONFIG directly."""

SCENARIOS_DIR: str = CONFIG.scenarios_dir
"""Backward-compat alias for sidebar.py.  New code should use CONFIG.scenarios_dir."""

DEFAULT_WEIGHT: float = CONFIG.default_weight
"""Backward-compat alias.  New code should use CONFIG.default_weight."""
