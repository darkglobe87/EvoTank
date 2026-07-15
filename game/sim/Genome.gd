class_name Genome
extends RefCounted
## Per-organism heritable data (DESIGN §5.2).
## Ported from prototype/evotank_sim/genetics.py Genome.
##
## traitIds are structural genes: changed ONLY by player intervention in the
## gene editor (spending Evo Points), never by spontaneous mutation.
## scalars are continuous genes: drift by small random deltas on reproduction.

var core_body_id: String = "protoblob"
var trait_ids: Array = []            # Array[String] — structural genes
var scalars: Dictionary = {}         # String -> float — continuous genes
var generation: int = 0
var lineage_id: String = "L0"


func _init(p_core_body_id: String = "protoblob", p_trait_ids: Array = [],
		p_scalars: Dictionary = {}, p_generation: int = 0, p_lineage_id: String = "L0") -> void:
	core_body_id = p_core_body_id
	trait_ids = p_trait_ids.duplicate()
	scalars = SimConfig.DEFAULT_SCALARS.duplicate() if p_scalars.is_empty() else p_scalars.duplicate()
	generation = p_generation
	lineage_id = p_lineage_id


func duplicate_genome() -> Genome:
	return Genome.new(core_body_id, trait_ids, scalars, generation, lineage_id)


## Cohort bucket key (DESIGN §6.1) — not used by the vertical slice (cohort.py
## is out of scope) but ported for interface parity with the prototype.
func signature() -> String:
	var keys := scalars.keys()
	keys.sort()
	var coarse: Array = []
	for k in keys:
		coarse.append("%s:%.1f" % [k, scalars[k]])
	var traits_sorted := trait_ids.duplicate()
	traits_sorted.sort()
	return "%s|%s|%s" % [core_body_id, ",".join(traits_sorted), ",".join(coarse)]
