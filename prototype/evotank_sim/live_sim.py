"""Live agent-based simulation loop (DESIGN §2).

Fixed-timestep tick over the whole tank in the DESIGN §2 order:
environment -> sense/decide/act -> metabolism+feed -> death -> reproduction ->
recount -> event log. Deterministic under a fixed seed. Headless: records
population/food time series for the experiment harnesses.
"""

from __future__ import annotations

import numpy as np

from . import config
from .environment import EnvironmentGrid
from .events import EventLog
from .genetics import Genome, TraitCatalog, compile_genome, mutate
from .metabolism import metabolic_drain
from .organism import Organism


class LiveSimulation:
    def __init__(self, catalog: TraitCatalog, seed: int = config.SEED):
        self.catalog = catalog
        self.rng = np.random.default_rng(seed)
        self.grid = EnvironmentGrid()
        self.log = EventLog()
        self.organisms: list[Organism] = []
        self.time = 0.0
        # Seed a modest standing-food level. Starting near full caused founders to
        # gorge and over-breed into a boom-bust crash (see FINDINGS.md); 0.25 of cap
        # gives a clean monotonic approach to carrying capacity instead.
        self.grid.food[:] = config.FOOD_CAP_PER_CELL * 0.25

    # --- seeding --------------------------------------------------------------
    def spawn(self, genome: Genome, x=None, y=None, energy=config.STARTING_ENERGY) -> Organism:
        ph = compile_genome(genome, self.catalog)
        x = self.rng.uniform(0, config.TANK_W) if x is None else x
        y = self.rng.uniform(0, config.TANK_H) if y is None else y
        org = Organism(genome, ph, x, y, energy)
        self.organisms.append(org)
        return org

    def seed_species(self, genome: Genome, count: int) -> None:
        for i in range(count):
            g = genome.copy()
            g.lineageId = f"{genome.lineageId}-{i}"
            self.spawn(g)

    # --- the tick (DESIGN §2) -------------------------------------------------
    def tick(self, dt: float = config.TICK_DT) -> None:
        self.time += dt
        self.grid.regen_food(dt)                                     # 1 environment

        for org in self.organisms:                                   # 2 sense/decide/act
            org.step_movement(self.grid, self.rng, dt)

        for org in self.organisms:                                   # 3 metabolism + feed
            org.age += dt
            stress = self.grid.stress(org.phenotype, org.x, org.y)
            org.energy -= metabolic_drain(org.phenotype, org.speed, stress) * dt
            eaten = self.grid.eat_at(org.x, org.y, org.phenotype["maxIntake"] * dt)
            if eaten > 0:
                org.energy += eaten * config.FOOD_ENERGY

        survivors: list[Organism] = []                               # 4 death
        for org in self.organisms:
            if org.is_dead():
                self.log.push(self.time, "DEATH", org.death_cause())
            else:
                survivors.append(org)
        self.organisms = survivors

        births: list[Organism] = []                                  # (5 combat: none pre-rivals)
        if len(self.organisms) < config.POP_HARD_CAP:                # reproduction
            for org in self.organisms:
                if org.can_reproduce():
                    org.energy -= org.phenotype["reproCost"]
                    org.last_birth_age = org.age
                    child_genome = mutate(org.genome, self.rng)
                    ph = compile_genome(child_genome, self.catalog)
                    child = Organism(
                        child_genome, ph,
                        min(config.TANK_W, max(0.0, org.x + self.rng.uniform(-5, 5))),
                        min(config.TANK_H, max(0.0, org.y + self.rng.uniform(-5, 5))),
                        config.STARTING_ENERGY,
                    )
                    births.append(child)
                    self.log.push(self.time, "BIRTH", f"gen{child_genome.generation}")
        self.organisms.extend(births)

    # --- driver ---------------------------------------------------------------
    def run(self, duration: float, record_every: float = 5.0) -> dict:
        """Advance `duration` time units; return sampled time series."""
        ts, pops, foods, energies = [], [], [], []
        next_record = 0.0
        end = self.time + duration
        while self.time < end and self.organisms:
            self.tick()
            if self.time >= next_record:
                ts.append(self.time)
                pops.append(len(self.organisms))
                foods.append(self.grid.total_food())
                energies.append(
                    float(np.mean([o.energy for o in self.organisms])) if self.organisms else 0.0
                )
                next_record += record_every
        return dict(t=np.array(ts), pop=np.array(pops),
                    food=np.array(foods), energy=np.array(energies))

    @property
    def population(self) -> int:
        return len(self.organisms)
