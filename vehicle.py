"""
vehicle.py — Vehicle agent.

Each Vehicle carries its own routing plan and records timing statistics
(waiting time, travel time) throughout the simulation.
"""

from __future__ import annotations
from typing import List, Optional


# Palette: one colour per destination (cycles if more than palette size)
_DEST_PALETTE = [
    "#E74C3C",  # red
    "#2ECC71",  # green
    "#3498DB",  # blue
    "#F39C12",  # orange
    "#9B59B6",  # purple
    "#1ABC9C",  # teal
    "#E67E22",  # carrot
    "#C0392B",  # dark-red
    "#27AE60",  # dark-green
    "#2980B9",  # dark-blue
]

# Maps destination → colour (populated lazily by VehicleFactory)
_dest_colour_map: dict[str, str] = {}
_colour_index: int = 0


def get_dest_colour(dest_id: str) -> str:
    """Return a consistent hex colour for *dest_id*."""
    global _colour_index
    if dest_id not in _dest_colour_map:
        _dest_colour_map[dest_id] = _DEST_PALETTE[_colour_index % len(_DEST_PALETTE)]
        _colour_index += 1
    return _dest_colour_map[dest_id]


class Vehicle:
    """Represents a single vehicle travelling through the network.

    Parameters
    ----------
    vehicle_id  : globally unique integer id
    source_id   : node id where this vehicle was generated
    dest_id     : node id this vehicle is heading to
    route       : ordered list of node ids from source to destination
    spawn_tick  : simulation tick when this vehicle was created
    """

    def __init__(
        self,
        vehicle_id: int,
        source_id: str,
        dest_id: str,
        route: List[str],
        spawn_tick: int,
    ) -> None:
        self.vehicle_id  = vehicle_id
        self.source_id   = source_id
        self.dest_id     = dest_id
        self.route       = list(route)   # copy; first entry == source
        self.spawn_tick  = spawn_tick
        self.colour      = get_dest_colour(dest_id)

        # Routing state
        self.route_index  = 0            # index of current position in route[]
        self.current_node: Optional[str] = source_id
        self.current_road: Optional[str] = None  # road_id the vehicle is on

        # Timing
        self.enter_tick: Optional[int]  = None   # tick vehicle first moved
        self.finish_tick: Optional[int] = None   # tick vehicle reached sink
        self.waiting_ticks = 0                   # ticks spent waiting at junction

        # Position interpolation for visualiser [0.0, 1.0] along current road
        self.road_progress: float = 0.0

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    @property
    def next_node(self) -> Optional[str]:
        """Node id of the next hop after the current position, or None."""
        idx = self.route_index + 1
        if idx < len(self.route):
            return self.route[idx]
        return None

    def advance_route(self) -> None:
        """Move route pointer forward by one hop."""
        self.route_index += 1
        if self.route_index < len(self.route):
            self.current_node = self.route[self.route_index]
        else:
            self.current_node = None

    @property
    def has_arrived(self) -> bool:
        """True when the vehicle has reached its final destination node."""
        return self.current_node == self.dest_id

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def travel_time(self) -> Optional[int]:
        if self.finish_tick is not None and self.enter_tick is not None:
            return self.finish_tick - self.enter_tick
        return None

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Vehicle(id={self.vehicle_id}, "
            f"{self.source_id}->{self.dest_id}, "
            f"node={self.current_node}, road={self.current_road})"
        )
