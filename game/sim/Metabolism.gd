class_name Metabolism
extends RefCounted
## The economy of energy (DESIGN §3). Ported from prototype/evotank_sim/metabolism.py.
## Single source of truth for how expensive a body is to run.


## Energy drained per unit time (multiply by dt at the call site).
## drain = (baseDrain + traitDrain + MOVE_COST*speed) * stress / efficiency
static func metabolic_drain(phenotype: Dictionary, speed: float, stress: float) -> float:
	var efficiency: float = phenotype.get("metabolicEfficiency", 1.0)
	var upkeep: float = phenotype["baseDrain"] + phenotype["traitDrain"] + SimConfig.MOVE_COST * speed
	return upkeep * stress / efficiency
