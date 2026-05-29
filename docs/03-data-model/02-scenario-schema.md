# Scenario File Schema

**Purpose.** The exact JSON contract for a scenario file. An agent can author all five
scenarios from this doc alone, without reading the PDF.

## Top-level shape
```json
{
  "name": "Scenario 1 — Even spacing",
  "world": { "speed_kmph": 60, "charge_minutes": 25, "battery_range_km": 240 },
  "route": {
    "nodes": ["Bengaluru", "A", "B", "C", "D", "Kochi"],
    "segments": [
      { "from": "Bengaluru", "to": "A", "distance_km": 100 },
      { "from": "A", "to": "B", "distance_km": 120 },
      { "from": "B", "to": "C", "distance_km": 100 },
      { "from": "C", "to": "D", "distance_km": 120 },
      { "from": "D", "to": "Kochi", "distance_km": 100 }
    ]
  },
  "stations": {
    "A": { "num_chargers": 1 },
    "B": { "num_chargers": 1 },
    "C": { "num_chargers": 1 },
    "D": { "num_chargers": 1 }
  },
  "weights": { "individual": 1.0, "operator": 1.0, "overall": 1.0 },
  "buses": [
    { "id": "bus-BK-01", "operator": "kpn", "origin": "Bengaluru",
      "destination": "Kochi", "departure_min": 1140 }
  ]
}
```

## Field rules
`world` keys are optional; missing keys fall back to `config.DEFAULTS`. `route.nodes` includes
endpoints; `route.segments` must connect consecutive nodes and have positive distances.
`stations` keys must be intermediate route nodes (never endpoints); `num_chargers` defaults to
1. `weights` requires `individual/operator/overall` but accepts **additional keys** for future
objectives. Each bus needs `id`, `operator`, `origin`, `destination`, `departure_min`
(minutes from midnight; 19:00 = 1140); optional `range_km` (defaults to `battery_range_km`) and
`priority` (defaults 0).

## Departure-time encoding
Times are integer minutes from midnight to keep arithmetic clean; HH:MM formatting happens
only in the UI adapter. Reference: 19:00=1140, 19:08=1148, 19:15=1155, 19:24=1164, 19:30=1170,
19:32=1172, 19:35=1175, 19:40=1180, 19:45=1185, 19:48=1188, 19:56=1196, 20:00=1200,
20:03=1203, 20:04=1204, 20:10=1210, 20:12=1212, 20:15=1215, 20:18=1218, 20:30=1230,
20:33=1233, 20:45=1245, 21:00=1260, 21:15=1275.

## The five scenarios — EXACT operator + departure tables

> ⚠ **Source of truth:** operators are fixed by the PDF. The BK and KB fleets use **different**
> operator rotations. Always verify against this table, not by pattern-copying BK operators.

### Scenario 1 — Even spacing (weights 1/1/1)
| Bus ID | Operator | Direction | Departure |
|--------|----------|-----------|-----------|
| bus-BK-01 | **kpn** | BK | 19:00 (1140) |
| bus-BK-02 | **freshbus** | BK | 19:15 (1155) |
| bus-BK-03 | **flixbus** | BK | 19:30 (1170) |
| bus-BK-04 | **kpn** | BK | 19:45 (1185) |
| bus-BK-05 | **freshbus** | BK | 20:00 (1200) |
| bus-BK-06 | **flixbus** | BK | 20:15 (1215) |
| bus-BK-07 | **kpn** | BK | 20:30 (1230) |
| bus-BK-08 | **freshbus** | BK | 20:45 (1245) |
| bus-BK-09 | **flixbus** | BK | 21:00 (1260) |
| bus-BK-10 | **kpn** | BK | 21:15 (1275) |
| bus-KB-01 | **freshbus** | KB | 19:00 (1140) |
| bus-KB-02 | **flixbus** | KB | 19:15 (1155) |
| bus-KB-03 | **kpn** | KB | 19:30 (1170) |
| bus-KB-04 | **freshbus** | KB | 19:45 (1185) |
| bus-KB-05 | **flixbus** | KB | 20:00 (1200) |
| bus-KB-06 | **kpn** | KB | 20:15 (1215) |
| bus-KB-07 | **freshbus** | KB | 20:30 (1230) |
| bus-KB-08 | **flixbus** | KB | 20:45 (1245) |
| bus-KB-09 | **kpn** | KB | 21:00 (1260) |
| bus-KB-10 | **freshbus** | KB | 21:15 (1275) |

**KB pattern:** freshbus → flixbus → kpn (repeating), NOT kpn/freshbus/flixbus.

### Scenario 2 — Bunched start (weights 1/1/1)
Same operators as Scenario 1. Departures every 8 min then spread:
BK: 19:00, 19:08, 19:16, 19:24, 19:32, 19:40, 19:48, **20:03**, **20:18**, **20:33**
KB: 19:00, 19:08, 19:16, 19:24, 19:32, 19:40, 19:48, **20:03**, **20:18**, **20:33**

### Scenario 3 — Asymmetric load (weights 1/1/1)
BK: 10 buses, 15 min spacing 19:00–21:15 (same operators as Scenario 1 BK side).
KB: only 4 buses:
| Bus ID | Operator | Departure |
|--------|----------|-----------|
| bus-KB-01 | **freshbus** | 19:00 (1140) |
| bus-KB-02 | **flixbus** | 19:35 (1175) |
| bus-KB-03 | **kpn** | 20:10 (1210) |
| bus-KB-04 | **freshbus** | 20:45 (1245) |

### Scenario 4 — Operator-heavy (weights individual=1.0, **operator=2.0**, overall=1.0)
BK: bus-BK-01..08 are all **kpn**; bus-BK-09=**freshbus**; bus-BK-10=**flixbus**.
All depart every 15 min 19:00–21:15.
KB: same freshbus/flixbus/kpn rotation, 15 min spacing 19:00–21:15.

### Scenario 5 — Worst-case convergence (weights 1/1/1)
All 20 buses every 8 min from both ends 19:00–20:12.
BK operators: kpn/freshbus/flixbus rotation (BK-01=kpn, BK-02=freshbus...).
KB operators: **freshbus/flixbus/kpn rotation** (KB-01=freshbus, KB-02=flixbus...).

## Common encoding mistake to avoid
> ❌ **Wrong:** copying the BK operator sequence (kpn/freshbus/flixbus) onto KB buses.
> ✅ **Correct:** KB buses start with **freshbus**, then flixbus, then kpn.
> The BK and KB fleets are staggered by one step in the operator rotation.
> Always verify by running the scenario verification script or checking the table above.
