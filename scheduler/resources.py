"""
scheduler/resources.py — ChargerPool: charger-slot reservation and exclusivity.

A ChargerPool manages one physical charging station with N charger slots.
It enforces hard rule H3: at most num_chargers buses may charge simultaneously.
With num_chargers=1 (today's default), charges strictly serialise.

Design: reservation is monotonic — once a slot is reserved it stays reserved.
The pool exposes a single `reserve(arrive_min)` method that returns the actual
charge start, wait, and charger index, extending the slot's busy window to
start + charge_minutes.  This is the mechanism used by engine.py to price
charger waits during plan evaluation.

References:
    docs/02-scheduler-engine/02-charging-allocation-strategy.md
    docs/02-scheduler-engine/04-conflict-resolution.md
    docs/00-requirements/02-constraints-and-rules.md  (H3 — charger exclusivity)
    docs/07-testing/01-testing-plan.md                (test_charger.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ChargerPool:
    """
    Resource allocator for a single charging station with one or more charger slots.

    Each slot is represented as the minute at which it next becomes free
    (initially 0 = available immediately).  When a bus arrives:
      • If any slot is free (slot_free_at ≤ arrive_min), the bus starts charging
        at arrive_min with zero wait.
      • If all slots are busy, the bus waits for the earliest-freeing slot and
        starts charging at that slot's free_at time.

    The pool is keyed by physical station node (in the engine), so two buses
    arriving from opposite directions contend on the *same* pool — satisfying R5
    (buses share chargers) and the future multi-route sharing requirement.
    """

    node: str           # which station this pool serves
    num_chargers: int   # capacity; defaults to 1 (validated by loader)
    charge_minutes: int # fixed charge duration (from World.charge_minutes)

    # Internal: free_at[i] = the minute slot i becomes available next.
    # Initialised to [0, 0, ...] (all slots free at minute 0).
    _slot_free_at: List[int] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Initialise slot availability to 0 (all free at simulation start)."""
        if not self._slot_free_at:
            self._slot_free_at = [0] * self.num_chargers

    def reserve(self, arrive_min: int) -> Tuple[int, int, int]:
        """
        Reserve the earliest available charger slot for a bus arriving at arrive_min.

        Algorithm:
          1. Find the slot with the minimum free_at value.
          2. Actual start = max(arrive_min, slot.free_at).
          3. Wait = actual_start - arrive_min.
          4. Mark the slot busy until actual_start + charge_minutes.

        This is called tentatively during plan evaluation (the engine simulates
        reservations before committing them); the caller must call `rollback` if
        the plan is not selected.

        Args:
            arrive_min: The wall-clock minute the bus arrives at this station.

        Returns:
            (start_min, wait_min, charger_index) — all guaranteed non-negative.
        """
        # Choose the slot that frees earliest (greedy earliest-available policy)
        charger_idx = min(range(self.num_chargers), key=lambda i: self._slot_free_at[i])
        free_at = self._slot_free_at[charger_idx]

        start_min = max(arrive_min, free_at)
        wait_min = start_min - arrive_min
        end_min = start_min + self.charge_minutes

        # Commit the reservation for this slot
        self._slot_free_at[charger_idx] = end_min

        return start_min, wait_min, charger_idx

    def snapshot(self) -> List[int]:
        """
        Return a copy of the current slot-free-at state.

        Used by the engine to save state before a speculative (tentative)
        reservation so it can roll back if a better plan is found.
        """
        return list(self._slot_free_at)

    def restore(self, state: List[int]) -> None:
        """
        Restore slot state to a previously captured snapshot.

        Called after a tentative reservation that was not ultimately committed,
        allowing the engine to evaluate multiple candidate plans without side
        effects.
        """
        self._slot_free_at = list(state)
