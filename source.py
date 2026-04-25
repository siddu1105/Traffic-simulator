"""
source.py — Traffic generation nodes.

A Source creates vehicles at configurable rates:
  - ConstantSource  : exactly one vehicle every N ticks
  - PoissonSource   : Poisson-distributed arrivals (λ vehicles / tick)

Both share a common base class so the Engine can call .generate(tick)
uniformly.
"""

from __future__ import annotations
import random
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .vehicle import Vehicle
    from .router import Router


# We keep a global counter here; Engine will reset/manage vehicle ids.
_vehicle_counter: int = 0


def _next_id() -> int:
    global _vehicle_counter
    _vehicle_counter += 1
    return _vehicle_counter


class _BaseSource:
    """Common interface for all source types.

    Sub-classes must implement _should_spawn(tick) → bool.
    """

    def __init__(
        self,
        source_id: str,
        destinations: List[str],
        router: Optional[Router] = None,
    ) -> None:
        self.source_id    = source_id
        self.destinations = list(destinations)
        self.router       = router          # injected by Engine

        self.total_generated: int = 0

    def set_router(self, router: Router) -> None:
        self.router = router

    def _should_spawn(self, tick: int) -> bool:  # pragma: no cover
        raise NotImplementedError

    def generate(self, tick: int) -> List[Vehicle]:
        """Return a list of new Vehicle objects for this tick (may be empty)."""
        from .vehicle import Vehicle  # local import to avoid circular deps

        if not self._should_spawn(tick):
            return []
        if not self.destinations:
            return []
        if self.router is None:
            raise RuntimeError("Router not set on Source before simulation start.")

        dest = random.choice(self.destinations)
        route = self.router.route(self.source_id, dest)
        if route is None:
            # No path exists — skip silently
            return []

        v = Vehicle(
            vehicle_id=_next_id(),
            source_id=self.source_id,
            dest_id=dest,
            route=route,
            spawn_tick=tick,
        )
        self.total_generated += 1
        return [v]


class ConstantSource(_BaseSource):
    """Emits exactly one vehicle every *interval* ticks.

    Parameters
    ----------
    source_id    : node id of this source
    destinations : list of possible destination sink ids
    interval     : ticks between successive vehicle births
    """

    def __init__(
        self,
        source_id: str,
        destinations: List[str],
        interval: int = 5,
    ) -> None:
        super().__init__(source_id, destinations)
        self.interval = max(1, interval)

    def _should_spawn(self, tick: int) -> bool:
        return tick % self.interval == 0


class PoissonSource(_BaseSource):
    """Emits vehicles following a Poisson process with mean rate λ.

    Parameters
    ----------
    source_id    : node id of this source
    destinations : list of possible destination sink ids
    rate         : expected vehicles per tick (λ)
    seed         : optional RNG seed for reproducibility
    """

    def __init__(
        self,
        source_id: str,
        destinations: List[str],
        rate: float = 0.3,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(source_id, destinations)
        self.rate = rate
        self._rng = random.Random(seed)

    def _should_spawn(self, tick: int) -> bool:
        # Poisson: number of arrivals in one interval ~ Poisson(λ)
        # P(at least one) = 1 - e^(-λ) ≈ λ for small λ
        # We draw from Poisson and return True if count ≥ 1
        k = self._rng.choices(
            range(5), weights=self._poisson_weights(self.rate, 5)
        )[0]
        return k >= 1

    @staticmethod
    def _poisson_weights(lam: float, k_max: int) -> List[float]:
        """Unnormalised Poisson PMF values for k=0..k_max-1."""
        import math
        weights = []
        for k in range(k_max):
            weights.append((lam ** k) * math.exp(-lam) / math.factorial(k))
        return weights

    def generate(self, tick: int) -> List[Vehicle]:
        """Override to potentially spawn *multiple* vehicles per tick."""
        from .vehicle import Vehicle
        import math

        if self.router is None:
            raise RuntimeError("Router not set on Source before simulation start.")

        # Draw actual count from Poisson distribution
        u = self._rng.random()
        # Inverse CDF approximation: keep subtracting PMF until u < 0
        cumulative = 0.0
        lam = self.rate
        count = 0
        for k in range(10):
            pmf = (lam ** k) * math.exp(-lam) / math.factorial(k)
            cumulative += pmf
            if u < cumulative:
                count = k
                break

        vehicles = []
        for _ in range(count):
            if not self.destinations:
                break
            dest = self._rng.choice(self.destinations)
            route = self.router.route(self.source_id, dest)
            if route is None:
                continue
            v = Vehicle(
                vehicle_id=_next_id(),
                source_id=self.source_id,
                dest_id=dest,
                route=route,
                spawn_tick=tick,
            )
            self.total_generated += 1
            vehicles.append(v)
        return vehicles
