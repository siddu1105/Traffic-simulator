"""
main.py — Define topology and run the traffic simulation.
==========================================================

This is the ONLY file that needs to be modified when deploying a new
road network.  All simulation logic lives in the traffic_sim/ package.

Network Topology (8 junctions, 2 sources, 3 sinks, 14+ roads):

       [S1]                   [S2]
        |                      |
       [J1] ----> [J2] ----> [J3]
        |          |           |
       [J4] ----> [J5] ----> [J6]
        |          |           |
       [SK1]      [J7] ----> [SK2]
                   |
                  [SK3]

Multiple parallel paths create genuine congestion and route competition.
"""

import os
import sys

from traffic_sim import Road, Junction, Sink, Engine, Visualizer
from traffic_sim.source import ConstantSource, PoissonSource

# ===========================================================================
# 1. DEFINE NODE COORDINATES (used by visualiser)
#    Format: node_id → (x, y)  — choose any planar layout
# ===========================================================================

NODE_POSITIONS = {
    # Sources (triangle markers)
    "S1": (1.0, 8.0),
    "S2": (7.0, 8.0),

    # Interior junctions (circle markers)
    "J1": (1.0, 6.0),
    "J2": (4.0, 6.0),
    "J3": (7.0, 6.0),
    "J4": (1.0, 4.0),
    "J5": (4.0, 4.0),
    "J6": (7.0, 4.0),
    "J7": (4.0, 2.0),

    # Sinks (square markers)
    "SK1": (1.0, 2.0),
    "SK2": (7.0, 2.0),
    "SK3": (4.0, 0.0),
}

# ===========================================================================
# 2. DEFINE JUNCTIONS
#    Only interior routing junctions — sources/sinks handled separately
# ===========================================================================

junctions = [
    Junction("J1", *NODE_POSITIONS["J1"]),
    Junction("J2", *NODE_POSITIONS["J2"]),
    Junction("J3", *NODE_POSITIONS["J3"]),
    Junction("J4", *NODE_POSITIONS["J4"]),
    Junction("J5", *NODE_POSITIONS["J5"]),
    Junction("J6", *NODE_POSITIONS["J6"]),
    Junction("J7", *NODE_POSITIONS["J7"]),
]

# ===========================================================================
# 3. DEFINE ROADS
#    Road(id, src_node, dst_node, length, capacity, speed)
#
#    length   : used by Dijkstra for route cost (higher = less preferred)
#    capacity : max simultaneous vehicles on this road
#    speed    : ticks to traverse this road (higher = slower road)
# ===========================================================================

roads = [
    # ---- Sources into network ----
    Road("S1->J1",  "S1", "J1",  length=1.0, capacity=6, speed=2),
    Road("S2->J3",  "S2", "J3",  length=1.0, capacity=6, speed=2),

    # ---- Top row (J1 → J2 → J3) ----
    Road("J1->J2",  "J1", "J2",  length=2.0, capacity=5, speed=3),
    Road("J2->J3",  "J2", "J3",  length=2.0, capacity=5, speed=3),

    # ---- Verticals left ----
    Road("J1->J4",  "J1", "J4",  length=2.0, capacity=4, speed=3),
    Road("J4->SK1", "J4", "SK1", length=1.0, capacity=6, speed=2),

    # ---- Middle row (J4 → J5 → J6) ----
    Road("J4->J5",  "J4", "J5",  length=2.0, capacity=5, speed=3),
    Road("J5->J6",  "J5", "J6",  length=2.0, capacity=5, speed=3),

    # ---- Verticals middle ----
    Road("J2->J5",  "J2", "J5",  length=2.0, capacity=4, speed=3),
    Road("J3->J6",  "J3", "J6",  length=2.0, capacity=4, speed=3),

    # ---- Verticals bottom ----
    Road("J5->J7",  "J5", "J7",  length=2.0, capacity=4, speed=3),
    Road("J6->SK2", "J6", "SK2", length=1.0, capacity=6, speed=2),

    # ---- Bottom row (J7 → SK2, J7 → SK3) ----
    Road("J7->SK2", "J7", "SK2", length=2.0, capacity=5, speed=3),
    Road("J7->SK3", "J7", "SK3", length=1.0, capacity=6, speed=2),

    # ---- Diagonal shortcut (creates interesting route choices) ----
    Road("J3->J5",  "J3", "J5",  length=2.8, capacity=3, speed=4),  # diagonal, narrow
    Road("J6->J7",  "J6", "J7",  length=2.0, capacity=4, speed=3),

    # ---- Back-route (allows loop avoidance by Dijkstra) ----
    Road("J2->J4",  "J2", "J4",  length=3.0, capacity=3, speed=4),  # longer shortcut
]

# ===========================================================================
# 4. DEFINE SINKS
#    Vehicles with matching destination_id are absorbed here
# ===========================================================================

sinks = [
    Sink("SK1"),
    Sink("SK2"),
    Sink("SK3"),
]

# ===========================================================================
# 5. DEFINE TRAFFIC SOURCES
#    Mix of constant-rate and Poisson sources for realism
# ===========================================================================

sources = [
    # S1 generates a mix of Poisson traffic towards all three sinks
    PoissonSource(
        source_id="S1",
        destinations=["SK1", "SK2", "SK3"],
        rate=0.4,          # avg 0.4 vehicles/tick
        seed=42,
    ),
    # S2 generates constant-rate traffic heavier on SK1 (long cross-town trip)
    PoissonSource(
        source_id="S2",
        destinations=["SK1", "SK2", "SK3"],
        rate=0.35,
        seed=99,
    ),
    # An additional constant-rate feeder from J3 (models on-ramp)
    ConstantSource(
        source_id="J3",
        destinations=["SK1", "SK3"],
        interval=8,        # one vehicle every 8 ticks
    ),
]

# ===========================================================================
# 6. SIMULATION PARAMETERS
# ===========================================================================

SIMULATION_DURATION = 200   # total ticks
ANIMATION_SKIP      = 2     # render every Nth tick for smaller GIF
OUTPUT_GIF          = "traffic.gif"
OUTPUT_STATS        = "stats.txt"

# ===========================================================================
# 7. RUN SIMULATION
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Modular Multi-Junction Traffic Simulator")
    print("  IIT Academic Project — traffic_sim v1.0")
    print("=" * 60)

    # Build and run engine
    engine = Engine(
        roads=roads,
        junctions=junctions,
        sources=sources,
        sinks=sinks,
        duration=SIMULATION_DURATION,
    )

    print(f"\n[Engine] Starting simulation: {SIMULATION_DURATION} ticks ...")
    engine.run()
    print(f"[Engine] Simulation complete.")
    print(f"[Engine] Generated={engine.total_generated}  Completed={engine.total_completed}")

    # Print and save statistics
    print()
    report = engine.print_stats()
    with open("stats.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n[Stats] Report saved → {OUTPUT_STATS}")

    # Render animated GIF
    viz = Visualizer(
        engine=engine,
        node_pos=NODE_POSITIONS,
        fps=8,
        interval=150,
        skip_frames=ANIMATION_SKIP,
    )
    viz.render(OUTPUT_GIF)
    print(f"\n[Done] All outputs saved.")
    print(f"       • {OUTPUT_GIF}")
    print(f"       • {OUTPUT_STATS}")
