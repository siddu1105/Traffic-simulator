"""
junction.py — Intersection node with traffic signal scheduling.

A Junction sits between incoming and outgoing roads.  Each tick it may
release ONE vehicle from the highest-priority incoming road into the
appropriate outgoing road (if space is available).

Scheduling policy: **Longest-Queue-First** (with Round-Robin tie-breaking).
This policy is demonstrably fair and maximises throughput under congestion,
which makes it ideal for an academic project.
"""

from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .road import Road
    from .vehicle import Vehicle


class Junction:
    """An intersection node.

    Parameters
    ----------
    junction_id : unique string id, e.g. "J3"
    x, y        : canvas coordinates used by the visualiser
    """

    def __init__(self, junction_id: str, x: float, y: float) -> None:
        self.junction_id = junction_id
        self.x = x
        self.y = y

        # road_id → Road  (populated by Engine after all roads are created)
        self.incoming: Dict[str, Road] = {}
        self.outgoing: Dict[str, Road] = {}

        # Round-robin tie-break counter
        self._rr_index: int = 0

        # Stats
        self.vehicles_passed: int = 0

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_incoming(self, road: Road) -> None:
        self.incoming[road.road_id] = road

    def add_outgoing(self, road: Road) -> None:
        self.outgoing[road.road_id] = road

    # ------------------------------------------------------------------
    # Signal logic
    # ------------------------------------------------------------------

    def _select_road(self) -> Optional[Road]:
        """Longest-Queue-First among incoming roads that have an arrived vehicle.

        Tie-break: round-robin over the sorted road list.
        Returns the winning Road or None.
        """
        candidates: List[Road] = [
            r for r in self.incoming.values() if r.has_arrived
        ]
        if not candidates:
            return None

        # Sort by descending queue length, then stable round-robin
        # We rotate the list so that the RR counter acts as a tie-breaker
        candidates.sort(key=lambda r: -r.occupancy)

        # Among roads with the same max occupancy, pick round-robin
        max_occ = candidates[0].occupancy
        top_tier = [r for r in candidates if r.occupancy == max_occ]

        chosen = top_tier[self._rr_index % len(top_tier)]
        self._rr_index = (self._rr_index + 1) % max(len(top_tier), 1)
        return chosen

    def _find_outgoing_road(self, vehicle: Vehicle) -> Optional[Road]:
        """Return the outgoing road this junction should send *vehicle* onto."""
        next_node = vehicle.next_node
        if next_node is None:
            return None
        for road in self.outgoing.values():
            if road.dst_id == next_node:
                return road
        return None

    def process(self) -> Optional[Vehicle]:
        """Try to release one vehicle per tick.

        Returns the released Vehicle (for stat tracking) or None.
        """
        chosen_road = self._select_road()
        if chosen_road is None:
            return None

        vehicle = chosen_road.front_vehicle
        if vehicle is None:
            return None

        # Determine where the vehicle wants to go next
        out_road = self._find_outgoing_road(vehicle)

        if out_road is None:
            # Vehicle has reached this junction as its final stop — pop it
            chosen_road.pop_front()
            vehicle.advance_route()
            self.vehicles_passed += 1
            return vehicle

        if out_road.is_full:
            # Vehicle must wait; do not pop — it stays at front of incoming road
            vehicle.waiting_ticks += 1
            return None

        # Move vehicle: pop from incoming road, push onto outgoing road
        chosen_road.pop_front()
        vehicle.advance_route()
        vehicle.current_road = out_road.road_id
        vehicle.road_progress = 0.0
        out_road.accept_vehicle(vehicle)
        self.vehicles_passed += 1
        return None   # vehicle is still in transit

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Junction({self.junction_id!r}, "
            f"in={list(self.incoming)}, out={list(self.outgoing)})"
        )
