"""Environment grid & trait-based navigation (DESIGN §4).

A layered scalar field over a coarse grid. Static gradients (light/temp/pressure)
are baked functions of position; the dynamic layer (foodDensity) evolves over
time. Creatures navigate by climbing the trait-derived `comfort` field — no
pathfinding needed.
"""

from __future__ import annotations

import math

import numpy as np

from . import config
from .genetics import Phenotype


class EnvironmentGrid:
    def __init__(self):
        self.w = config.GRID_W
        self.h = config.GRID_H
        # Baked static gradients, normalized 0..1. y=0 is the surface (top).
        ys = np.linspace(0.0, 1.0, self.h).reshape(self.h, 1)
        self.light = np.tile(1.0 - ys, (1, self.w))          # bright at surface
        self.temp = np.tile(1.0 - ys, (1, self.w))           # warm at surface
        self.pressure = np.tile(ys, (1, self.w))             # high at depth
        # Dynamic layer: standing food per cell.
        self.food = np.zeros((self.h, self.w), dtype=float)

    # --- indexing helpers -----------------------------------------------------
    def cell_of(self, x: float, y: float) -> tuple[int, int]:
        cx = min(self.w - 1, max(0, int(x / config.TANK_W * self.w)))
        cy = min(self.h - 1, max(0, int(y / config.TANK_H * self.h)))
        return cx, cy

    def cell_center(self, cx: int, cy: int) -> tuple[float, float]:
        x = (cx + 0.5) / self.w * config.TANK_W
        y = (cy + 0.5) / self.h * config.TANK_H
        return x, y

    def _bilinear(self, field: np.ndarray, x: float, y: float) -> float:
        """Bilinear sample of a scalar field at world (x, y) (DESIGN §4.1)."""
        gx = x / config.TANK_W * self.w - 0.5
        gy = y / config.TANK_H * self.h - 0.5
        x0 = min(self.w - 1, max(0, int(math.floor(gx))))
        y0 = min(self.h - 1, max(0, int(math.floor(gy))))
        x1 = min(self.w - 1, x0 + 1)
        y1 = min(self.h - 1, y0 + 1)
        tx = min(1.0, max(0.0, gx - x0))
        ty = min(1.0, max(0.0, gy - y0))
        top = field[y0, x0] * (1 - tx) + field[y0, x1] * tx
        bot = field[y1, x0] * (1 - tx) + field[y1, x1] * tx
        return top * (1 - ty) + bot * ty

    def sample(self, x: float, y: float) -> dict:
        return dict(
            light=self._bilinear(self.light, x, y),
            temperature=self._bilinear(self.temp, x, y),
            pressure=self._bilinear(self.pressure, x, y),
            foodDensity=self._bilinear(self.food, x, y),
        )

    # --- comfort & stress (DESIGN §4.2) --------------------------------------
    def comfort(self, phenotype: Phenotype, x: float, y: float) -> float:
        """Product of per-axis Gaussians: ~1 in the ideal niche, ->0 in hostile."""
        s = self.sample(x, y)
        c = 1.0
        for axis, opt_key, rng_key in (
            ("temperature", "tempOptimum", "tempRange"),
            ("light", "lightOptimum", "lightRange"),
            ("pressure", "pressureOptimum", "pressureRange"),
        ):
            rng = max(1e-3, phenotype[rng_key])
            d = s[axis] - phenotype[opt_key]
            c *= math.exp(-(d * d) / (2 * rng * rng))
        return c

    def stress(self, phenotype: Phenotype, x: float, y: float) -> float:
        return 1.0 + config.STRESS_K * (1.0 - self.comfort(phenotype, x, y))

    # --- dynamic update (DESIGN §4.3) ----------------------------------------
    def regen_food(self, dt: float) -> None:
        """Logistic self-limiting regrowth so food never piles up unbounded."""
        cap = config.FOOD_CAP_PER_CELL
        self.food += config.FOOD_REGEN_RATE * (1.0 - self.food / cap) * dt
        np.clip(self.food, 0.0, cap, out=self.food)

    def total_food(self) -> float:
        return float(self.food.sum())

    def eat_at(self, x: float, y: float, amount: float) -> float:
        """Consume up to `amount` food units from the organism's cell."""
        cx, cy = self.cell_of(x, y)
        available = self.food[cy, cx]
        eaten = min(amount, available)
        self.food[cy, cx] = available - eaten
        return eaten
