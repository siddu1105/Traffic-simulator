"""
engine.py — Discrete-time simulation engine.

The Engine orchestrates the entire simulation each tick:
    1. Advance vehicles on all roads (road.tick)
    2. Process junctions (release vehicles, signal scheduling)
    3. Place newly released vehicles from junctions onto their next road
    4. Absorb vehicles that have reached a sink
    5. Generate new vehicles from sources
    6. Record snapshot for visualiser

Order within a tick is carefully chosen to prevent double-movement:
vehicles that just arrived are NOT moved again in the same tick.
"""

from __future__ import annotations
from typing import Dict, List, Optional

from .road      import Road
from .junction  import Junction
from .vehicle   import Vehicle
from .source    import _BaseSource
from .sink      import Sink
from .router    import Router


class Engine:
    """Central simulation engine.

    Parameters
    ----------
    roads     : all Road objects
    junctions : all Junction objects (keyed by junction_id internally)
    sources   : traffic generators
    sinks     : destination nodes (keyed by sink_id internally)
    duration  : total ticks to simulate
    """

    def __init__(
        self,
        roads:     List[Road],
        junctions: List[Junction],
        sources:   List[_BaseSource],
        sinks:     List[Sink],
        duration:  int = 200,
    ) -> None:
        self.roads     = roads
        self.junctions = {j.junction_id: j for j in junctions}
        self.sources   = sources
        self.sinks     = {s.sink_id: s for s in sinks}
        self.duration  = duration

        self._road_map: Dict[str, Road] = {r.road_id: r for r in roads}

        # Build router over all roads and inject into sources
        self.router = Router(roads)
        for src in sources:
            src.set_router(self.router)

        # Wire incoming / outgoing roads to junctions
        self._wire_junctions()

        # Active vehicles not yet at sink (road_id→vehicle tracked via roads)
        self._pending_vehicles: List[Vehicle] = []   # waiting at source node

        # Simulation state
        self.tick: int = 0

        # Snapshot history for visualiser: list of per-tick snapshots
        # Each snapshot: {'tick': int, 'vehicles': [(vid, road_id, progress, colour)]}
        self.snapshots: List[dict] = []

        # Global stats
        self.total_generated: int = 0
        self.total_completed: int = 0

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _wire_junctions(self) -> None:
        """Register each road with the appropriate junction as in/out."""
        for road in self.roads:
            # road.src_id → junction or source; road.dst_id → junction or sink
            src_junc = self.junctions.get(road.src_id)
            dst_junc = self.junctions.get(road.dst_id)
            if src_junc:
                src_junc.add_outgoing(road)
            if dst_junc:
                dst_junc.add_incoming(road)

    # ------------------------------------------------------------------
    # Core simulation loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the simulation for *duration* ticks."""
        for t in range(self.duration):
            self.tick = t
            self._step()
        # Final snapshot
        self._record_snapshot()

    def _step(self) -> None:
        """Execute one simulation tick."""

        # 1. Advance all vehicles on every road
        for road in self.roads:
            road.tick()

        # 2. Try to place pending (freshly spawned) vehicles onto their first road
        still_pending: List[Vehicle] = []
        for vehicle in self._pending_vehicles:
            placed = self._place_on_first_road(vehicle)
            if not placed:
                vehicle.waiting_ticks += 1
                still_pending.append(vehicle)
        self._pending_vehicles = still_pending

        # 3. Process every junction: release one vehicle per junction per tick
        for junc in self.junctions.values():
            released = junc.process()
            # released is returned only when vehicle reached its final junction
            # (i.e., next_node is None or no outgoing road) — we absorb it
            if released is not None:
                self._absorb_if_done(released)

        # 4. Check whether any vehicle on a road leading INTO a sink has arrived
        self._absorb_from_roads()

        # 5. Generate new vehicles from all sources
        for source in self.sources:
            new_vehicles = source.generate(self.tick)
            for v in new_vehicles:
                self.total_generated += 1
                v.enter_tick = self.tick
                placed = self._place_on_first_road(v)
                if not placed:
                    v.waiting_ticks += 1
                    self._pending_vehicles.append(v)

        # 6. Record snapshot for visualiser
        self._record_snapshot()

    # ------------------------------------------------------------------
    # Placement helpers
    # ------------------------------------------------------------------

    def _place_on_first_road(self, vehicle: Vehicle) -> bool:
        """Attempt to move *vehicle* from its source node onto the first road.

        Returns True on success.
        """
        next_node = vehicle.next_node
        if next_node is None:
            # Single-node route (source == sink) — absorb immediately
            self._absorb_if_done(vehicle)
            return True

        # Find road from current_node to next_node
        road = self._road_between(vehicle.current_node, next_node)
        if road is None:
            return False   # should not happen with valid topology

        if road.is_full:
            return False

        vehicle.advance_route()
        vehicle.current_road = road.road_id
        vehicle.road_progress = 0.0
        road.accept_vehicle(vehicle)
        return True

    def _road_between(self, src: Optional[str], dst: Optional[str]) -> Optional[Road]:
        if src is None or dst is None:
            return None
        for road in self.roads:
            if road.src_id == src and road.dst_id == dst:
                return road
        return None

    # ------------------------------------------------------------------
    # Absorption
    # ------------------------------------------------------------------

    def _absorb_from_roads(self) -> None:
        """Check roads that lead directly into a sink and absorb arrived vehicles."""
        for road in self.roads:
            if road.dst_id in self.sinks and road.has_arrived:
                vehicle = road.pop_front()
                if vehicle:
                    vehicle.advance_route()
                    vehicle.current_road = None
                    self._absorb_if_done(vehicle)

    def _absorb_if_done(self, vehicle: Vehicle) -> None:
        sink = self.sinks.get(vehicle.dest_id)
        if sink is not None:
            sink.absorb(vehicle, self.tick)
            self.total_completed += 1

    # ------------------------------------------------------------------
    # Snapshot recording
    # ------------------------------------------------------------------

    def _record_snapshot(self) -> None:
        """Record vehicle positions for animation."""
        entries = []
        for road in self.roads:
            traffic = list(road._traffic)
            n = len(traffic)
            for i, (vehicle, ticks_left) in enumerate(traffic):
                # progress: 0 = just entered, 1 = about to exit
                if road.speed > 0:
                    progress = 1.0 - (ticks_left / road.speed)
                else:
                    progress = 1.0
                progress = max(0.0, min(1.0, progress))
                # Stagger vehicles along road so they don't overlap perfectly
                stagger = i * 0.08
                display_progress = min(progress + stagger, 0.95)
                entries.append({
                    "vid":      vehicle.vehicle_id,
                    "road_id":  road.road_id,
                    "progress": display_progress,
                    "colour":   vehicle.colour,
                    "src":      road.src_id,
                    "dst":      road.dst_id,
                })
        self.snapshots.append({"tick": self.tick, "vehicles": entries})

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def print_stats(self) -> str:
        """Compute, print, and return a formatted statistics report."""
        lines = []
        lines.append("=" * 60)
        lines.append("  TRAFFIC SIMULATION — STATISTICS REPORT")
        lines.append("=" * 60)
        lines.append(f"  Simulation Duration   : {self.duration} ticks")
        lines.append(f"  Total Vehicles Generated : {self.total_generated}")
        lines.append(f"  Total Vehicles Completed : {self.total_completed}")

        if self.duration > 0:
            throughput = self.total_completed / self.duration
        else:
            throughput = 0.0
        lines.append(f"  Throughput            : {throughput:.4f} vehicles/tick")

        # Aggregate travel/wait times across all sinks
        all_travel, all_wait = [], []
        for sink in self.sinks.values():
            for v in sink.completed_vehicles:
                if v.travel_time is not None:
                    all_travel.append(v.travel_time)
                all_wait.append(v.waiting_ticks)

        if all_travel:
            lines.append(f"  Avg Travel Time       : {sum(all_travel)/len(all_travel):.2f} ticks")
            lines.append(f"  Max Travel Time       : {max(all_travel)} ticks")
        else:
            lines.append("  Avg Travel Time       : N/A")

        if all_wait:
            lines.append(f"  Avg Waiting Time      : {sum(all_wait)/len(all_wait):.2f} ticks")
        else:
            lines.append("  Avg Waiting Time      : N/A")

        lines.append("")
        lines.append("  ROAD STATISTICS (sorted by utilisation ↓)")
        lines.append("  " + "-" * 56)
        lines.append(f"  {'Road':<18} {'Util%':>7} {'MaxQ':>5} {'Thput':>6}")
        lines.append("  " + "-" * 56)

        sorted_roads = sorted(
            self.roads, key=lambda r: r.utilisation, reverse=True
        )
        for road in sorted_roads:
            lines.append(
                f"  {road.road_id:<18} "
                f"{road.utilisation*100:>6.1f}% "
                f"{road.max_queue_length:>5} "
                f"{road.total_throughput:>6}"
            )

        lines.append("")
        lines.append("  CONGESTION RANKING (most congested roads)")
        lines.append("  " + "-" * 56)
        for rank, road in enumerate(sorted_roads[:5], 1):
            lines.append(
                f"  #{rank}  {road.road_id:<18}  util={road.utilisation*100:.1f}%"
            )

        lines.append("")
        lines.append("  SINK STATISTICS")
        lines.append("  " + "-" * 56)
        for sink in self.sinks.values():
            avg_tt = sink.average_travel_time
            avg_wt = sink.average_waiting_time
            avg_tt_str = f"{avg_tt:.1f}" if avg_tt is not None else "N/A"
            avg_wt_str = f"{avg_wt:.1f}" if avg_wt is not None else "N/A"
            lines.append(
                f"  Sink {sink.sink_id!r:10}  completed={sink.total_completed:4}  "
                f"avg_travel={avg_tt_str}  "
                f"avg_wait={avg_wt_str}"
            )

        lines.append("=" * 60)

        report = "\n".join(lines)
        print(report)
        return report
