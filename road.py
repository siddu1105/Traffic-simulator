"""
road.py — Directional road segment between two nodes.

Each Road models a single-direction lane with:
  - finite capacity (max vehicles on road at once)
  - a FIFO queue of vehicles currently travelling
  - per-tick progress tracking for each vehicle
  - statistics collection (utilisation, max queue, throughput)
"""

from __future__ import annotations
from collections import deque
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .vehicle import Vehicle


class Road:
    """A directed road from *src_id* to *dst_id*.

    Parameters
    ----------
    road_id   : unique string identifier, e.g. "J1->J2"
    src_id    : node id of the tail of this road
    dst_id    : node id of the head of this road
    length    : logical length used by the router (default 1)
    capacity  : maximum number of vehicles allowed on road simultaneously
    speed     : ticks a vehicle needs to traverse the full road
    """

    def __init__(
        self,
        road_id: str,
        src_id: str,
        dst_id: str,
        length: float = 1.0,
        capacity: int = 5,
        speed: int = 3,
    ) -> None:
        self.road_id   = road_id
        self.src_id    = src_id
        self.dst_id    = dst_id
        self.length    = length
        self.capacity  = capacity
        self.speed     = speed          # ticks to traverse the road

        # vehicles currently on the road: deque of (vehicle, ticks_remaining)
        self._traffic: deque[tuple[Vehicle, int]] = deque()

        # Stats
        self._total_passed  = 0         # vehicles that exited this road
        self._tick_load_sum = 0         # sum of occupancy each tick (for util%)
        self._max_queue     = 0         # peak concurrent occupancy
        self._tick_count    = 0         # total ticks this road was active

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def occupancy(self) -> int:
        """Number of vehicles currently on the road."""
        return len(self._traffic)

    @property
    def is_full(self) -> bool:
        """True when no more vehicles can enter."""
        return self.occupancy >= self.capacity

    @property
    def has_arrived(self) -> bool:
        """True when the front vehicle has completed its journey along this road."""
        if not self._traffic:
            return False
        _, ticks_left = self._traffic[0]
        return ticks_left <= 0

    @property
    def front_vehicle(self) -> Optional[Vehicle]:
        """The vehicle at the head of the road (closest to exit), or None."""
        if self._traffic:
            return self._traffic[0][0]
        return None

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def accept_vehicle(self, vehicle: Vehicle) -> bool:
        """Place *vehicle* onto this road.  Returns False if road is full."""
        if self.is_full:
            return False
        self._traffic.append((vehicle, self.speed))
        self._max_queue = max(self._max_queue, self.occupancy)
        return True

    def pop_front(self) -> Optional[Vehicle]:
        """Remove and return the front vehicle (call only when has_arrived)."""
        if self._traffic:
            vehicle, _ = self._traffic.popleft()
            self._total_passed += 1
            return vehicle
        return None

    def tick(self) -> None:
        """Advance all vehicles on this road by one time unit."""
        self._tick_count += 1
        occ = self.occupancy
        self._tick_load_sum += occ
        self._max_queue = max(self._max_queue, occ)

        # Decrement ticks_remaining for every vehicle
        updated: deque[tuple[Vehicle, int]] = deque()
        for vehicle, ticks_left in self._traffic:
            updated.append((vehicle, ticks_left - 1))
        self._traffic = updated

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    @property
    def utilisation(self) -> float:
        """Average load / capacity as a fraction [0, 1]."""
        if self._tick_count == 0 or self.capacity == 0:
            return 0.0
        avg_load = self._tick_load_sum / self._tick_count
        return min(avg_load / self.capacity, 1.0)

    @property
    def max_queue_length(self) -> int:
        return self._max_queue

    @property
    def total_throughput(self) -> int:
        return self._total_passed

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Road({self.road_id!r}, {self.src_id}->{self.dst_id}, "
            f"occ={self.occupancy}/{self.capacity})"
        )
