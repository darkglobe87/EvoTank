"""Organism entity + utility-AI brain (DESIGN §2.2).

Sense -> decide -> act. The brain scores a small set of drives and blends a
heading from (a) the direction to nearby food and (b) the local comfort gradient.
Weighting shifts toward foraging as energy falls. No pathfinding.
"""

from __future__ import annotations

import math

import numpy as np

from . import config
from .genetics import Genome, Phenotype


class Organism:
    __slots__ = (
        "genome", "phenotype", "x", "y", "vx", "vy",
        "energy", "age", "hp", "last_birth_age", "alive", "speed",
    )

    def __init__(self, genome: Genome, phenotype: Phenotype,
                 x: float, y: float, energy: float):
        self.genome = genome
        self.phenotype = phenotype
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.energy = energy
        self.age = 0.0
        self.hp = phenotype["hp"]
        self.last_birth_age = 0.0
        self.alive = True
        self.speed = 0.0

    # --- sense + decide + act -------------------------------------------------
    def step_movement(self, grid, rng, dt: float) -> None:
        p = self.phenotype
        sense = p["senseRadius"]

        # (a) Forage vector: head toward the richest food cell within sense radius.
        fx, fy, best = 0.0, 0.0, 0.0
        cx, cy = grid.cell_of(self.x, self.y)
        reach = max(1, int(sense / (config.TANK_W / grid.w)))
        for dy in range(-reach, reach + 1):
            for dx in range(-reach, reach + 1):
                gx, gy = cx + dx, cy + dy
                if 0 <= gx < grid.w and 0 <= gy < grid.h:
                    f = grid.food[gy, gx]
                    if f > best:
                        wx, wy = grid.cell_center(gx, gy)
                        if (wx - self.x) ** 2 + (wy - self.y) ** 2 <= sense * sense:
                            best, fx, fy = f, wx - self.x, wy - self.y
        forage = _normalize(fx, fy)

        # (b) Comfort gradient: sample 4 neighbours, steer toward higher comfort.
        step = config.TANK_W / grid.w
        here = grid.comfort(p, self.x, self.y)
        gxv = grid.comfort(p, self.x + step, self.y) - grid.comfort(p, self.x - step, self.y)
        gyv = grid.comfort(p, self.x, self.y + step) - grid.comfort(p, self.x, self.y - step)
        comfort_dir = _normalize(gxv, gyv)

        # Drive weighting: hungrier organisms prioritise food over comfort.
        hunger = 1.0 - min(1.0, self.energy / p["reproThreshold"])
        w_food = 0.35 + 0.55 * hunger
        w_comfort = 0.25 + 0.35 * (1.0 - here)
        w_wander = 0.15
        wx = rng.normal(0.0, 1.0)
        wy = rng.normal(0.0, 1.0)
        wander = _normalize(wx, wy)

        dirx = w_food * forage[0] + w_comfort * comfort_dir[0] + w_wander * wander[0]
        diry = w_food * forage[1] + w_comfort * comfort_dir[1] + w_wander * wander[1]
        dirx, diry = _normalize(dirx, diry)

        self.vx = dirx * p["maxSpeed"]
        self.vy = diry * p["maxSpeed"]
        self.x = min(config.TANK_W, max(0.0, self.x + self.vx * dt))
        self.y = min(config.TANK_H, max(0.0, self.y + self.vy * dt))
        self.speed = math.hypot(self.vx, self.vy)

    def can_reproduce(self) -> bool:
        p = self.phenotype
        return (
            self.energy >= p["reproThreshold"]
            and self.age >= p["maturity"]
            and (self.age - self.last_birth_age) >= config.REPRO_COOLDOWN
        )

    def is_dead(self) -> bool:
        return self.energy <= 0.0 or self.age >= self.phenotype["lifespan"] or self.hp <= 0.0

    def death_cause(self) -> str:
        if self.energy <= 0.0:
            return "starvation"
        if self.hp <= 0.0:
            return "predation"
        return "old age"


def _normalize(x: float, y: float) -> tuple[float, float]:
    m = math.hypot(x, y)
    if m < 1e-9:
        return 0.0, 0.0
    return x / m, y / m
