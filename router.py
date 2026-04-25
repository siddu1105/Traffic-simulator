"""
router.py — Shortest-path routing via Dijkstra's algorithm.

The Router is initialised once with the full road graph.  Every vehicle
calls Router.route(src, dst) to obtain its hop-by-hop node path.

Edge weights = Road.length, so longer roads are penalised.
"""

from __future__ import annotations
import heapq
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .road import Road


class Router:
    """Computes shortest paths on the directed road network.

    Parameters
    ----------
    roads : list of all Road objects in the network
    """

    def __init__(self, roads: List[Road]) -> None:
        # Adjacency: src_id → list of (dst_id, road_length, road_id)
        self._adj: Dict[str, List[tuple[str, float, str]]] = {}
        for road in roads:
            self._adj.setdefault(road.src_id, [])
            self._adj[road.src_id].append((road.dst_id, road.length, road.road_id))

    def route(self, src: str, dst: str) -> Optional[List[str]]:
        """Return the shortest node-path from *src* to *dst*, or None if unreachable.

        The returned list includes both endpoints:
            [src, intermediate_1, ..., dst]

        Algorithm: Dijkstra with a binary min-heap.
        """
        if src == dst:
            return [src]

        # dist[node] = best cumulative distance found so far
        dist: Dict[str, float] = {src: 0.0}
        prev: Dict[str, Optional[str]] = {src: None}

        # Priority queue entries: (distance, node_id)
        heap: List[tuple[float, str]] = [(0.0, src)]

        while heap:
            d, node = heapq.heappop(heap)

            # Stale entry
            if d > dist.get(node, float("inf")):
                continue

            if node == dst:
                # Reconstruct path
                path: List[str] = []
                cur: Optional[str] = dst
                while cur is not None:
                    path.append(cur)
                    cur = prev.get(cur)
                path.reverse()
                return path

            for neighbour, length, _ in self._adj.get(node, []):
                new_dist = d + length
                if new_dist < dist.get(neighbour, float("inf")):
                    dist[neighbour] = new_dist
                    prev[neighbour] = node
                    heapq.heappush(heap, (new_dist, neighbour))

        return None  # unreachable

    def all_pairs(self, nodes: List[str]) -> Dict[tuple[str, str], Optional[List[str]]]:
        """Pre-compute routes for every (src, dst) pair — useful for debugging."""
        result: Dict[tuple[str, str], Optional[List[str]]] = {}
        for src in nodes:
            for dst in nodes:
                if src != dst:
                    result[(src, dst)] = self.route(src, dst)
        return result
