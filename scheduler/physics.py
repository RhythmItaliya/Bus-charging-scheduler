from __future__ import annotations


def travel_minutes(distance_km: float, speed_kmph: float) -> float:
    if speed_kmph <= 0:
        raise ValueError(f"speed_kmph must be > 0, got {speed_kmph}")
    return (distance_km / speed_kmph) * 60.0


def base_arrival_minutes(
    departure_min: int,
    cumulative_distance_km: float,
    speed_kmph: float,
) -> float:
    return departure_min + travel_minutes(cumulative_distance_km, speed_kmph)


def minutes_to_hhmm(minutes: float) -> str:
    total_minutes = int(round(minutes))
    hh = (total_minutes // 60) % 24
    mm = total_minutes % 60
    return f"{hh:02d}:{mm:02d}"


def leg_distance(
    route_positions: dict[str, float],
    from_node: str,
    to_node: str,
) -> float:
    return abs(route_positions[to_node] - route_positions[from_node])
