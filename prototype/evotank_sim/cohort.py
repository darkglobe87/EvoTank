"""Idle math — statistical cohort model (DESIGN §6).

On app-pause, deflate() buckets live entities into genotype cohorts. The
CohortModel advances them in closed form (coupled logistic with resource
coupling) over the whole idle interval in a handful of large sub-steps — O(1) in
elapsed time. inflate() resamples discrete entities to repopulate the live tank.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

import numpy as np

from . import config

# Cap on integration sub-step size (time units). Guarantees the exponential
# update stays accurate and stable no matter how long the idle interval is, at
# the cost of more (still trivially cheap) sub-steps for very long absences.
H_MAX = 25.0
from .genetics import Genome, TraitCatalog, compile_genome
from .metabolism import metabolic_drain
from .organism import Organism


@dataclass
class Cohort:
    genome: Genome                 # representative genome for the bucket
    phenotype: dict
    N: float
    meanEnergy: float
    meanAge: float

    # cached per-capita rates (DESIGN §6.2)
    intake_energy: float = field(init=False)   # max energy/time when fully fed
    drain: float = field(init=False)           # metabolic drain/time at cruising

    def __post_init__(self):
        self.intake_energy = self.phenotype["maxIntake"] * config.FOOD_ENERGY
        cruise = self.phenotype["maxSpeed"] * 0.4
        self.drain = metabolic_drain(self.phenotype, cruise, stress=1.0)


@dataclass
class IdleResult:
    cohorts: List[Cohort]
    food_stock: float
    births: int
    deaths: int


def deflate(sim) -> tuple[list[Cohort], float]:
    """Bucket live organisms into cohorts by genome signature (DESIGN §6.1)."""
    buckets: dict = {}
    for org in sim.organisms:
        sig = org.genome.signature()
        buckets.setdefault(sig, []).append(org)
    cohorts = []
    for members in buckets.values():
        rep = members[0]
        cohorts.append(Cohort(
            genome=rep.genome.copy(),
            phenotype=rep.phenotype,
            N=float(len(members)),
            meanEnergy=float(np.mean([m.energy for m in members])),
            meanAge=float(np.mean([m.age for m in members])),
        ))
    return cohorts, sim.grid.total_food()


class CohortModel:
    """Coupled logistic population dynamics with shared-resource coupling."""

    def __init__(self, params: dict | None = None):
        p = dict(config.IDLE)
        if params:
            p.update(params)
        self.B0 = p["B0"]
        self.D0 = p["D0"]
        self.S = p["S"]
        self.K = p["K"]
        self.substeps = int(p["substeps"])
        # Aggregate food regeneration rate (energy/time) available tank-wide.
        self.regen_rate = (
            config.GRID_W * config.GRID_H
            * config.FOOD_REGEN_RATE * config.FOOD_ENERGY
        )

    def _rates(self, cohorts, fed_frac, Ntot):
        for c in cohorts:
            net = fed_frac * c.intake_energy - c.drain
            birth = self.B0 * max(0.0, net)
            death = self.D0 + self.S * max(0.0, -net) + _old_age(c.meanAge)
            yield c, net, birth, death

    def step(self, cohorts, food_stock, h):
        Ntot = sum(c.N for c in cohorts)
        total_demand = sum(c.N * c.intake_energy for c in cohorts)
        supply = self.regen_rate + food_stock / h if h > 0 else self.regen_rate
        fed_frac = 1.0 if total_demand <= 0 else min(1.0, supply / total_demand)
        consumed = fed_frac * total_demand
        food_stock = max(0.0, food_stock + (self.regen_rate - consumed) * h)

        births = deaths = 0.0
        dens = max(0.0, 1.0 - Ntot / self.K)
        for c, net, birth, death in self._rates(cohorts, fed_frac, Ntot):
            # Semi-analytic (exponential) per-capita update: unconditionally stable
            # and non-negative even for large h, unlike a raw Euler step.
            g = birth * dens - death
            new_n = c.N * math.exp(g * h)
            births += c.N * birth * dens * h        # gross flows for the event digest
            deaths += c.N * death * h
            c.N = max(0.0, new_n)
            # Cohort ages by h, but the influx of age-0 newborns dilutes mean age
            # (birth fraction beta). Without this the cohort "ages to death" even
            # at demographic steady state and the population spuriously collapses.
            beta = min(1.0, birth * dens * h)
            c.meanAge = (1.0 - beta) * (c.meanAge + h)
        return food_stock, births, deaths

    def _nsub(self, elapsed: float) -> int:
        """Enough sub-steps to keep every step <= H_MAX (stability), >= configured floor."""
        return max(self.substeps, int(math.ceil(elapsed / H_MAX)))

    def advance(self, cohorts, food_stock, elapsed) -> IdleResult:
        """Integrate the whole idle interval (DESIGN §6.3), sub-step size capped at H_MAX."""
        nsub = self._nsub(elapsed)
        h = elapsed / nsub
        births = deaths = 0.0
        for _ in range(nsub):
            food_stock, b, d = self.step(cohorts, food_stock, h)
            births += b
            deaths += d
        return IdleResult(cohorts, food_stock, int(round(births)), int(round(deaths)))

    def curve_at(self, cohorts, food_stock, times):
        """Population at each requested timepoint (exact sampling, for calibration)."""
        work = [Cohort(c.genome, c.phenotype, c.N, c.meanEnergy, c.meanAge)
                for c in cohorts]
        fs = food_stock
        out = np.empty(len(times))
        prev = 0.0
        for i, target in enumerate(times):
            seg = float(target) - prev
            if seg > 0:
                nsub = max(1, int(math.ceil(seg / H_MAX)))
                h = seg / nsub
                for _ in range(nsub):
                    fs, _, _ = self.step(work, fs, h)
            out[i] = sum(c.N for c in work)
            prev = float(target)
        return out

    def project_population(self, cohorts, food_stock, elapsed, samples):
        """Return a population curve at `samples` timepoints (for calibration)."""
        cohorts = [Cohort(c.genome, c.phenotype, c.N, c.meanEnergy, c.meanAge)
                   for c in cohorts]
        h = elapsed / self.substeps
        times = np.linspace(0.0, elapsed, samples)
        out = np.empty(samples)
        t = 0.0
        idx = 0
        out[0] = sum(c.N for c in cohorts)
        step_i = 0
        recorded = 1
        while recorded < samples and step_i < self.substeps:
            food_stock, _, _ = self.step(cohorts, food_stock, h)
            t += h
            step_i += 1
            # record whenever we've passed the next sample time
            while recorded < samples and t >= times[recorded] - 1e-9:
                out[recorded] = sum(c.N for c in cohorts)
                recorded += 1
        out[recorded:] = sum(c.N for c in cohorts)
        return times, out


def inflate(result: IdleResult, sim, catalog: TraitCatalog) -> None:
    """Resample discrete organisms from cohort distributions (DESIGN §6.4)."""
    sim.organisms.clear()
    for c in result.cohorts:
        n = int(round(c.N))
        for _ in range(n):
            ph = compile_genome(c.genome, catalog)
            energy = max(1.0, sim.rng.normal(c.meanEnergy, 5.0))
            org = Organism(
                c.genome.copy(), ph,
                sim.rng.uniform(0, config.TANK_W),
                sim.rng.uniform(0, config.TANK_H),
                energy,
            )
            org.age = max(0.0, c.meanAge)
            sim.organisms.append(org)
    sim.grid.food[:] = np.clip(
        result.food_stock / (config.GRID_W * config.GRID_H),
        0.0, config.FOOD_CAP_PER_CELL,
    )


def _old_age(mean_age: float) -> float:
    """Extra mortality as a cohort approaches its lifespan."""
    frac = mean_age / config.BASE_PLAN["lifespan"]
    return max(0.0, frac - 0.7) * 0.01
