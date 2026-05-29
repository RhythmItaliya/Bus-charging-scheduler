# Diagram — Scheduler Workflow

```mermaid
flowchart TD
    Start([schedule(scenario)]) --> Arr[Compute wait-free arrivals per bus]
    Arr --> Enum[Enumerate candidate plans per bus]
    Enum --> Sort[Sort buses: priority desc, departure asc, id asc]
    Sort --> Loop{For each bus in order}
    Loop -->|next bus| Eval[For each candidate plan]
    Eval --> Sim[Simulate ChargerPool reservations]
    Sim --> Score[Score incremental weighted objective]
    Score --> Pick[Pick lowest-cost feasible plan]
    Pick --> Commit[Commit reservations + timeline]
    Commit --> Loop
    Loop -->|all committed| Build[Build BusPlans + station_order]
    Build --> Val[validate hard rules]
    Val -->|violations| Err[[Raise / surface error]]
    Val -->|clean| Out([ScheduleResult])
```
