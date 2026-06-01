from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:


    speed_kmph: float = 60.0

    charge_minutes: int = 25

    battery_range_km: float = 240.0

    default_weight: float = 1.0


    scenarios_dir: str = "data/scenarios"


    log_level_env_var: str = "BCS_LOG_LEVEL"

    default_log_level: str = "INFO"


    page_title: str = "Bus Charging Scheduler"

    page_icon: str = "⚡"

    page_layout: str = "wide"

    sidebar_state: str = "expanded"


    weight_slider_min: float = 0.0

    weight_slider_max: float = 5.0

    weight_slider_step: float = 0.5


    wait_warn_min: int = 1

    wait_crit_min: int = 30


CONFIG = AppConfig()


DEFAULTS: dict = {
    "speed_kmph":       CONFIG.speed_kmph,
    "charge_minutes":   CONFIG.charge_minutes,
    "battery_range_km": CONFIG.battery_range_km,
}

SCENARIOS_DIR: str = CONFIG.scenarios_dir

DEFAULT_WEIGHT: float = CONFIG.default_weight
