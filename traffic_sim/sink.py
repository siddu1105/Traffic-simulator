"""
sink.py — Destination exit node.

A Sink absorbs vehicles that have completed their route.  The Engine
calls sink.absorb(vehicle, tick) to finalise timing stats and remove
the vehicle from active simulation.
"""

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .vehicle import Vehicle


class Sink:
    """Represents a terminal destination node in the road network.

    Parameters
    ----------
    sink_id : node id (matches the destination id used by vehicles)
    """

    def __init__(self, sink_id: str) -> None:
        self.sink_id = sink_id
        self._completed: List[Vehicle] = []

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def absorb(self, vehicle: Vehicle, tick: int) -> None:
        """Record *vehicle* as completed at simulation tick *tick*."""
        vehicle.finish_tick = tick
        if vehicle.enter_tick is None:
            vehicle.enter_tick = tick   # edge-case: zero-hop route
        self._completed.append(vehicle)

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    @property
    def total_completed(self) -> int:
        return len(self._completed)

    @property
    def average_travel_time(self) -> Optional[float]:
        times = [v.travel_time for v in self._completed if v.travel_time is not None]
        return sum(times) / len(times) if times else None

    @property
    def average_waiting_time(self) -> Optional[float]:
        waits = [v.waiting_ticks for v in self._completed]
        return sum(waits) / len(waits) if waits else None

    @property
    def completed_vehicles(self) -> List[Vehicle]:
        return list(self._completed)

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Sink({self.sink_id!r}, completed={self.total_completed})"
