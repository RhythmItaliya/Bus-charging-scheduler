from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ChargerPool:

    node: str
    num_chargers: int
    charge_minutes: int


    _slot_free_at: List[int] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self._slot_free_at:
            self._slot_free_at = [0] * self.num_chargers

    def reserve(self, arrive_min: int) -> Tuple[int, int, int]:

        charger_idx = min(range(self.num_chargers), key=lambda i: self._slot_free_at[i])
        free_at = self._slot_free_at[charger_idx]

        start_min = max(arrive_min, free_at)
        wait_min = start_min - arrive_min
        end_min = start_min + self.charge_minutes


        self._slot_free_at[charger_idx] = end_min

        return start_min, wait_min, charger_idx

    def snapshot(self) -> List[int]:
        return list(self._slot_free_at)

    def restore(self, state: List[int]) -> None:
        self._slot_free_at = list(state)
