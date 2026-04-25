"""
visualizer.py — Animated GIF renderer using Matplotlib.

Renders the road network as a directed graph and overlays moving
vehicle dots, queue buildup colours, and a live tick counter.

Designed to work with the snapshot history recorded by Engine.
"""

from __future__ import annotations
import math
from typing import Dict, List, Tuple, TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — must be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
from matplotlib.patches import FancyArrowPatch

if TYPE_CHECKING:
    from .engine import Engine


# -----------------------------------------------------------------------
# Colour helpers
# -----------------------------------------------------------------------

def _lerp_colour(c1: str, c2: str, t: float) -> str:
    """Linear interpolation between two hex colours."""
    def _hex_to_rgb(h: str) -> Tuple[float, float, float]:
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))   # type: ignore

    def _rgb_to_hex(r: float, g: float, b: float) -> str:
        return "#{:02X}{:02X}{:02X}".format(
            int(r * 255), int(g * 255), int(b * 255)
        )

    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    t = max(0.0, min(1.0, t))
    return _rgb_to_hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def _util_colour(utilisation: float) -> str:
    """Green → yellow → red as utilisation rises."""
    if utilisation < 0.5:
        return _lerp_colour("#27AE60", "#F39C12", utilisation * 2)
    else:
        return _lerp_colour("#F39C12", "#E74C3C", (utilisation - 0.5) * 2)


# -----------------------------------------------------------------------
# Main visualiser
# -----------------------------------------------------------------------

class Visualizer:
    """Renders an animated GIF of the simulation.

    Parameters
    ----------
    engine   : completed Engine instance (snapshots already recorded)
    node_pos : dict mapping node_id → (x, y) coordinates
    fps      : frames per second for the output animation
    interval : ms between frames in the GIF
    """

    def __init__(
        self,
        engine: Engine,
        node_pos: Dict[str, Tuple[float, float]],
        fps: int = 10,
        interval: int = 120,
        skip_frames: int = 1,
    ) -> None:
        self.engine      = engine
        self.node_pos    = node_pos
        self.fps         = fps
        self.interval    = interval
        self.skip_frames = max(1, skip_frames)   # render every Nth snapshot

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self, output_path: str = "traffic.gif") -> None:
        """Build and save the animated GIF to *output_path*."""
        print(f"[Visualizer] Rendering animation → {output_path} ...")

        snapshots = self.engine.snapshots[::self.skip_frames]
        total_frames = len(snapshots)

        # ---- figure setup ----
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor("#1A1A2E")
        ax.set_facecolor("#16213E")
        ax.set_aspect("equal")
        ax.axis("off")

        # Compute axis limits from node positions with padding
        xs = [p[0] for p in self.node_pos.values()]
        ys = [p[1] for p in self.node_pos.values()]
        pad = 1.5
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)

        # ---- static elements: draw roads as arrows ----
        self._draw_static_roads(ax)

        # ---- static elements: draw nodes ----
        node_artists = self._draw_nodes(ax)

        # ---- dynamic elements: vehicle scatter ----
        veh_scatter = ax.scatter(
            [], [], s=60, zorder=6, linewidths=0.5, edgecolors="#FFFFFF"
        )

        # ---- title ----
        title = ax.set_title(
            "Traffic Simulation — Tick 0",
            color="white",
            fontsize=14,
            fontweight="bold",
            pad=12,
        )

        # ---- legend: destination colours ----
        from .vehicle import _dest_colour_map
        legend_patches = [
            mpatches.Patch(color=col, label=f"→ {dest}")
            for dest, col in _dest_colour_map.items()
        ]
        if legend_patches:
            leg = ax.legend(
                handles=legend_patches,
                loc="upper right",
                fontsize=8,
                framealpha=0.3,
                facecolor="#1A1A2E",
                edgecolor="#555",
                labelcolor="white",
            )

        # ---- animation function ----
        def _update(frame_idx: int):
            snap = snapshots[frame_idx]
            tick = snap["tick"]
            vehicles = snap["vehicles"]

            # Update vehicle dots
            if vehicles:
                xs_v, ys_v, colours = [], [], []
                for entry in vehicles:
                    x, y = self._interpolate_pos(
                        entry["src"], entry["dst"], entry["progress"]
                    )
                    xs_v.append(x)
                    ys_v.append(y)
                    colours.append(entry["colour"])
                veh_scatter.set_offsets(list(zip(xs_v, ys_v)))
                veh_scatter.set_facecolor(colours)
            else:
                veh_scatter.set_offsets([])

            title.set_text(
                f"Traffic Simulation — Tick {tick} / {self.engine.duration}"
            )
            return veh_scatter, title

        ani = animation.FuncAnimation(
            fig,
            _update,
            frames=total_frames,
            interval=self.interval,
            blit=False,
        )

        # ---- save ----
        writer = animation.PillowWriter(fps=self.fps)
        ani.save(output_path, writer=writer, dpi=100)
        plt.close(fig)
        print(f"[Visualizer] Saved → {output_path}")

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_static_roads(self, ax) -> None:
        """Draw all roads as curved arrows, coloured by utilisation."""
        for road in self.engine.roads:
            sx, sy = self.node_pos.get(road.src_id, (0, 0))
            dx, dy = self.node_pos.get(road.dst_id, (0, 0))
            colour = _util_colour(road.utilisation)

            # Slight curve to distinguish parallel roads
            cx = (sx + dx) / 2 + (dy - sy) * 0.12
            cy = (sy + dy) / 2 - (dx - sx) * 0.12

            ax.annotate(
                "",
                xy=(dx, dy),
                xytext=(sx, sy),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=colour,
                    lw=1.8,
                    connectionstyle=f"arc3,rad=0.15",
                    shrinkA=14,
                    shrinkB=14,
                ),
                zorder=3,
            )

            # Road label (road_id) at midpoint
            mid_x = (sx + dx) / 2 + (dy - sy) * 0.08
            mid_y = (sy + dy) / 2 - (dx - sx) * 0.08
            ax.text(
                mid_x, mid_y,
                road.road_id,
                fontsize=5.5,
                color="#AAAAAA",
                ha="center",
                va="center",
                zorder=4,
            )

    def _draw_nodes(self, ax) -> Dict[str, any]:
        """Draw junction and sink/source nodes. Returns artist map."""
        junc_ids  = set(self.engine.junctions.keys())
        sink_ids  = set(self.engine.sinks.keys())
        source_ids = {s.source_id for s in self.engine.sources}

        artists = {}
        for node_id, (x, y) in self.node_pos.items():
            if node_id in sink_ids:
                colour, shape, size, zorder = "#E74C3C", "s", 220, 5
                label_colour = "#FF8080"
            elif node_id in source_ids:
                colour, shape, size, zorder = "#2ECC71", "^", 220, 5
                label_colour = "#80FF80"
            else:
                colour, shape, size, zorder = "#3498DB", "o", 180, 5
                label_colour = "#AADDFF"

            sc = ax.scatter(x, y, c=colour, s=size, marker=shape,
                            zorder=zorder, edgecolors="white", linewidths=1.0)
            ax.text(
                x, y + 0.35,
                node_id,
                fontsize=8,
                fontweight="bold",
                color=label_colour,
                ha="center",
                va="bottom",
                zorder=6,
            )
            artists[node_id] = sc

        # Draw a small legend for node types
        legend_elems = [
            ax.scatter([], [], c="#2ECC71", s=120, marker="^", label="Source"),
            ax.scatter([], [], c="#E74C3C", s=120, marker="s", label="Sink"),
            ax.scatter([], [], c="#3498DB", s=120, marker="o", label="Junction"),
        ]
        ax.legend(
            handles=legend_elems,
            loc="lower left",
            fontsize=8,
            framealpha=0.3,
            facecolor="#1A1A2E",
            edgecolor="#555",
            labelcolor="white",
        )
        return artists

    def _interpolate_pos(
        self, src_id: str, dst_id: str, progress: float
    ) -> Tuple[float, float]:
        """Linear interpolation of position along a road."""
        sx, sy = self.node_pos.get(src_id, (0, 0))
        dx, dy = self.node_pos.get(dst_id, (0, 0))
        # Slight perpendicular offset to match the curved arrow
        cx = (sx + dx) / 2 + (dy - sy) * 0.12
        cy = (sy + dy) / 2 - (dx - sx) * 0.12

        # Quadratic Bezier: P(t) = (1-t)^2 * P0 + 2(1-t)t * Pm + t^2 * P1
        t = max(0.0, min(1.0, progress))
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t ** 2 * dx
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t ** 2 * dy
        return bx, by
