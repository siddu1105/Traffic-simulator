"""
traffic_sim — Modular Multi-Junction Traffic Simulator
======================================================
A reusable library for simulating vehicles on directional road networks.

Modules:
    road        — Road segment with capacity and queue
    junction    — Intersection with signal scheduling
    vehicle     — Vehicle agent with routing info
    source      — Traffic generation (constant / Poisson)
    sink        — Destination exit node
    router      — Dijkstra shortest-path routing
    engine      — Discrete-time simulation engine
    visualizer  — Animated GIF renderer
"""

from .road import Road
from .junction import Junction
from .vehicle import Vehicle
from .source import ConstantSource, PoissonSource
from .sink import Sink
from .router import Router
from .engine import Engine
from .visualizer import Visualizer

__all__ = [
    "Road", "Junction", "Vehicle", "ConstantSource", "PoissonSource", "Sink",
    "Router", "Engine", "Visualizer",
]
