"""The economy of energy (DESIGN §3).

Single source of truth for how expensive a body is to run. Reads the pre-summed
drains cached on the Phenotype by genetics.compile_genome().
"""

from __future__ import annotations

from . import config
from .genetics import Phenotype


def metabolic_drain(phenotype: Phenotype, speed: float, stress: float) -> float:
    """Energy drained per unit time (multiply by dt at the call site).

    drain = (baseDrain + traitDrain + MOVE_COST*speed) * stress / efficiency

    - baseDrain grows allometrically with size (already size^0.75 in compile).
    - traitDrain is the summed metabolicCost of attached modules — this is what
      makes a heavily armored creature hungry without any special-casing.
    - stress (>= 1.0) comes from being outside the comfort zone (DESIGN §4).
    - metabolicEfficiency (a continuous gene) divides total drain.
    """
    efficiency = phenotype.get("metabolicEfficiency", 1.0)
    upkeep = phenotype["baseDrain"] + phenotype["traitDrain"] + config.MOVE_COST * speed
    return upkeep * stress / efficiency
