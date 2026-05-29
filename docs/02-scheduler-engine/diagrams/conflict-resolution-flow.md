# Diagram — Conflict Resolution

```mermaid
sequenceDiagram
    participant E as Engine
    participant P as ChargerPool(node=B, chargers=1)
    Note over E: Bus BK-03 arrives B at 19:20
    E->>P: reserve(19:20)
    P-->>E: start 19:20, charger 0, wait 0
    Note over E: Bus KB-05 arrives B at 19:35 (overlaps 19:20-19:45)
    E->>P: reserve(19:35)
    P-->>E: start 19:45, charger 0, wait 10
    Note over E: Objective may instead choose plan {C,A} for KB-05 if cheaper
    E->>E: Compare cost(BK route via B) vs alt plan; commit min
```
