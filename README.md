# Modular Multi-Junction Traffic Simulator

**IIT Academic Project — Python 3 | OOP | Discrete-Event Simulation**

---

## Overview

A fully modular, object-oriented traffic simulator for arbitrary directed road networks.  
The simulator models vehicles travelling from sources to sinks through a network of junctions and roads, with realistic queuing, signal control, and shortest-path routing.

Key design philosophy: **only `main.py` needs modification** to deploy a completely new road network.

---

## Features

| Feature | Detail |
|---|---|
| **Routing** | Dijkstra's algorithm on weighted directed graph |
| **Queuing** | FIFO road queues with configurable capacity |
| **Signal Policy** | Longest-Queue-First with Round-Robin tie-break |
| **Traffic Generation** | Constant-rate and Poisson-distributed arrivals |
| **Statistics** | Throughput, travel time, wait time, utilisation, congestion rank |
| **Animation** | Colour-coded animated GIF with moving vehicle dots |
| **Architecture** | Clean OOP, type hints, modular package structure |

---

## Folder Structure

```
traffic_sim/
├── __init__.py      — Package exports
├── road.py          — Road segment (capacity, FIFO queue, utilisation)
├── junction.py      — Intersection with signal scheduling
├── vehicle.py       — Vehicle agent (routing, timing, colour)
├── source.py        — Traffic generators (Constant & Poisson)
├── sink.py          — Destination exit node
├── router.py        — Dijkstra shortest-path routing
├── engine.py        — Discrete-time simulation engine
└── visualizer.py    — Animated GIF renderer (matplotlib)

main.py              — Topology definition + simulation runner (MODIFY THIS)
requirements.txt     — Python dependencies
README.md            — This file
stats.txt            — Generated statistics report (after run)
traffic.gif          — Generated animation (after run)
```

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the simulation

```bash
python3 main.py
```

### 3. Outputs

| File | Description |
|---|---|
| `traffic.gif` | Animated visualisation of the simulation |
| `stats.txt` | Full statistics report |

---

## Demo Network Topology

The included demo uses **8 junctions, 2 dedicated sources, 3 sinks, and 16 roads**:

```
[S1]                     [S2]
  |                        |
[J1] ──────> [J2] ──────> [J3]
  |            |  ↘         |
[J4] ──────> [J5] ──────> [J6]
  |            |             |
[SK1]        [J7] ──> [SK2] [SK2]
               |
             [SK3]
```

- **S1, S2**: Traffic source nodes (Poisson arrivals)  
- **J1–J7**: Interior junctions (round traffic signals)  
- **SK1, SK2, SK3**: Sink nodes (vehicles are absorbed here)  
- A **diagonal shortcut** (J3→J5) creates competing route choices, producing realistic congestion.

---

## Defining a New Topology (modify main.py only)

### Step 1 — Node coordinates

```python
NODE_POSITIONS = {
    "A": (0, 0),
    "B": (3, 0),
    "SINK1": (6, 0),
}
```

### Step 2 — Junctions

```python
junctions = [
    Junction("A", *NODE_POSITIONS["A"]),
    Junction("B", *NODE_POSITIONS["B"]),
]
```

### Step 3 — Roads

```python
roads = [
    Road("A->B",     "A", "B",     length=1.0, capacity=5, speed=3),
    Road("B->SINK1", "B", "SINK1", length=1.0, capacity=5, speed=2),
]
```

### Step 4 — Sinks

```python
sinks = [Sink("SINK1")]
```

### Step 5 — Sources

```python
from traffic_sim.source import PoissonSource, ConstantSource

sources = [
    PoissonSource("A", destinations=["SINK1"], rate=0.3),
]
```

### Step 6 — Run

```python
engine = Engine(roads=roads, junctions=junctions, sources=sources, sinks=sinks, duration=150)
engine.run()
```

---

## Simulation Mechanics

### Discrete Time Steps

The simulator advances in integer **ticks**.  Each tick:

1. All vehicles on roads advance (ticks_remaining decremented).
2. Freshly spawned vehicles attempt to enter their first road.
3. Each junction runs its signal logic and releases one vehicle.
4. Vehicles that reach a sink are absorbed and logged.
5. Sources generate new vehicles according to their rate model.
6. A snapshot is recorded for the visualiser.

### Signal Policy — Longest-Queue-First

Each junction selects the incoming road with the **most waiting vehicles**.  
Ties are broken by round-robin rotation to prevent starvation.  
This policy provably maximises throughput under congestion compared to fixed-cycle signals.

### Routing — Dijkstra's Algorithm

On spawn, each vehicle computes its full route using the global `Router`.  
Road `length` is used as edge weight, so longer roads are avoided when shorter alternatives exist.  
If a road is blocked (full), the vehicle waits — it does **not** re-route dynamically (this is a deliberate simplification noted in assumptions).

---

## Statistics Explained

| Statistic | Meaning |
|---|---|
| **Total Generated** | Vehicles created by all sources |
| **Total Completed** | Vehicles that reached their sink |
| **Throughput** | Completed / Duration (vehicles per tick) |
| **Avg Travel Time** | Mean ticks from first road entry to sink arrival |
| **Avg Waiting Time** | Mean ticks spent waiting at junctions or blocked |
| **Max Queue Length** | Peak number of vehicles on any single road |
| **Road Utilisation** | Average occupancy / capacity (higher = more congested) |
| **Congestion Ranking** | Roads sorted by utilisation descending |

---

## Assumptions & Simplifications

1. **Static routing**: Routes are pre-computed at vehicle spawn and do not adapt to congestion.
2. **One vehicle released per junction per tick**: Simplified signal model; can be extended to multi-lane.
3. **Poisson arrivals**: Independently sampled each tick; burst traffic is possible but rare.
4. **Road speed is fixed**: All vehicles on a road take the same number of ticks to traverse it.
5. **No crashes or incidents**: The simulation models normal traffic flow only.

---

## Module Reference

| Module | Class | Responsibility |
|---|---|---|
| `road.py` | `Road` | Directed lane with capacity, queue, and stats |
| `junction.py` | `Junction` | Intersection with LQF signal scheduling |
| `vehicle.py` | `Vehicle` | Agent with route, timing, and colour |
| `source.py` | `ConstantSource`, `PoissonSource` | Traffic generation |
| `sink.py` | `Sink` | Vehicle absorption and per-sink stats |
| `router.py` | `Router` | Dijkstra shortest-path engine |
| `engine.py` | `Engine` | Orchestrates all components per tick |
| `visualizer.py` | `Visualizer` | Animated GIF renderer |

---

*Submitted as part of the Systems Simulation course — IIT Academic Project*
