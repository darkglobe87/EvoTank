"""Data-driven genetics (DESIGN §5).

TraitDefinition assets (data/traits/*.json) declare BOTH visual and statistical
effects, so the two never diverge. A Genome carries structural genes (traitIds,
changed only by player intervention) and continuous genes (scalars, mutated on
reproduction). compile() is the single choke point turning genes into a flat,
cached Phenotype that the hot loop reads.
"""

from __future__ import annotations

import copy
import glob
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List

from . import config

_TRAITS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "traits")


def _apply_modifier(target: dict, key: str, op: str, value: float) -> None:
    """Apply one {op, value} modifier to a phenotype field."""
    if key not in target:
        # tolerance ranges may not exist on the base plan for every axis; seed at 0
        target[key] = 0.0
    if op == "add":
        target[key] += value
    elif op == "mul":
        target[key] *= value
    else:
        raise ValueError(f"unknown modifier op: {op!r}")


@dataclass
class TraitDefinition:
    id: str
    displayName: str
    category: str
    evoCost: float
    metabolicCost: float
    statModifiers: Dict[str, dict]
    toleranceModifiers: Dict[str, dict]
    visual: dict
    prerequisites: List[str]
    incompatibleWith: List[str]

    @staticmethod
    def from_json(d: dict) -> "TraitDefinition":
        return TraitDefinition(
            id=d["id"],
            displayName=d.get("displayName", d["id"]),
            category=d.get("category", "misc"),
            evoCost=float(d.get("evoCost", 0)),
            metabolicCost=float(d.get("metabolicCost", 0.0)),
            statModifiers=d.get("statModifiers", {}),
            toleranceModifiers=d.get("toleranceModifiers", {}),
            visual=d.get("visual", {}),
            prerequisites=d.get("prerequisites", []),
            incompatibleWith=d.get("incompatibleWith", []),
        )


class TraitCatalog:
    """Loads and indexes all TraitDefinition assets."""

    def __init__(self, traits: Dict[str, TraitDefinition]):
        self._traits = traits

    @classmethod
    def load(cls, directory: str | None = None) -> "TraitCatalog":
        directory = directory or _TRAITS_DIR
        traits: Dict[str, TraitDefinition] = {}
        for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
            with open(path, "r", encoding="utf-8") as fh:
                td = TraitDefinition.from_json(json.load(fh))
            traits[td.id] = td
        if not traits:
            raise FileNotFoundError(f"no trait assets found in {directory}")
        return cls(traits)

    def __getitem__(self, trait_id: str) -> TraitDefinition:
        return self._traits[trait_id]

    def __contains__(self, trait_id: str) -> bool:
        return trait_id in self._traits

    def ids(self) -> List[str]:
        return list(self._traits.keys())


@dataclass
class Genome:
    """Per-organism heritable data (DESIGN §5.2)."""

    coreBodyId: str = "protoblob"
    traitIds: List[str] = field(default_factory=list)          # structural genes
    scalars: Dict[str, float] = field(
        default_factory=lambda: dict(config.DEFAULT_SCALARS)
    )                                                          # continuous genes
    generation: int = 0
    lineageId: str = "L0"

    def copy(self) -> "Genome":
        return Genome(
            coreBodyId=self.coreBodyId,
            traitIds=list(self.traitIds),
            scalars=dict(self.scalars),
            generation=self.generation,
            lineageId=self.lineageId,
        )

    def signature(self) -> tuple:
        """Cohort bucket key (DESIGN §6.1): body + traits + coarse scalars."""
        coarse = tuple(sorted((k, round(v, 1)) for k, v in self.scalars.items()))
        return (self.coreBodyId, tuple(sorted(self.traitIds)), coarse)


# Phenotype is a plain dict keyed by BASE_PLAN fields plus derived drains.
Phenotype = Dict[str, float]


def compile_genome(genome: Genome, catalog: TraitCatalog) -> Phenotype:
    """Compile genes -> flat cached Phenotype (DESIGN §5.3).

    Order: base plan -> trait stat/tolerance modifiers -> continuous scalars ->
    derived metabolic drains. This is the ONLY place data becomes live numbers.
    """
    p: Phenotype = copy.deepcopy(config.BASE_PLAN)

    # Continuous genes first (DESIGN §5.2): they set the *genetic* baseline. Optima
    # are absolute gene positions; size/speed are biases; efficiency divides drain.
    s = genome.scalars
    p["size"] *= s.get("size", 1.0)
    p["maxSpeed"] *= s.get("speedBias", 1.0)
    p["metabolicEfficiency"] = s.get("metabolicEfficiency", 1.0)
    p["tempOptimum"] = s.get("tempOptimum", p["tempOptimum"])
    p["lightOptimum"] = s.get("lightOptimum", p["lightOptimum"])
    p["pressureOptimum"] = s.get("pressureOptimum", p["pressureOptimum"])

    # Trait modules apply ON TOP of the genetic baseline, so an attachment (e.g.
    # dark pigment shifting lightOptimum) actually moves the compiled value.
    trait_drain = 0.0
    for tid in genome.traitIds:
        td = catalog[tid]
        for stat, mod in td.statModifiers.items():
            _apply_modifier(p, stat, mod["op"], mod["value"])
        for axis, mod in td.toleranceModifiers.items():
            _apply_modifier(p, axis, mod["op"], mod["value"])
        trait_drain += td.metabolicCost

    p["tempOptimum"] = _clamp01(p["tempOptimum"])
    p["lightOptimum"] = _clamp01(p["lightOptimum"])
    p["pressureOptimum"] = _clamp01(p["pressureOptimum"])

    # Derived drains, pre-summed for the metabolism hot path (DESIGN §3).
    p["baseDrain"] = config.BODY_BASE * (p["size"] ** config.SIZE_EXP)
    p["traitDrain"] = trait_drain
    return p


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def mutate(genome: Genome, rng) -> Genome:
    """Minor mutation on reproduction: drift continuous genes only (DESIGN §5.4).

    Structural genes (traitIds) are copied verbatim — adding a trait requires
    player intervention + Evo Points, never spontaneous mutation.
    """
    g = genome.copy()
    g.generation += 1
    for key in list(g.scalars.keys()):
        g.scalars[key] *= 1.0 + rng.normal(0.0, config.MUT_SIGMA)
        lo, hi = config.GENE_BOUNDS.get(key, (float("-inf"), float("inf")))
        g.scalars[key] = max(lo, min(hi, g.scalars[key]))
    return g
