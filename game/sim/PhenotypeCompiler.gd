class_name PhenotypeCompiler
extends RefCounted
## Compiles genes -> a flat, cached Phenotype (Dictionary) (DESIGN §5.3).
## Ported from prototype/evotank_sim/genetics.py compile_genome()/mutate().
##
## CRITICAL ORDER (this is the exact fix for a real bug found during the
## Python prototype phase — see prototype/FINDINGS.md #1): continuous scalars
## apply FIRST to set the genetic baseline, THEN trait modifiers apply ON TOP.
## Applying traits before scalars silently clobbers tolerance shifts (e.g.
## dark pigment's lightOptimum shift would never show up). Do not reorder.


static func compile_genome(genome: Genome, catalog: TraitCatalog) -> Dictionary:
	var p: Dictionary = SimConfig.BASE_PLAN.duplicate(true)

	# Continuous genes first (DESIGN §5.2): they set the *genetic* baseline.
	# Optima are absolute gene positions; size/speed are biases; efficiency
	# divides drain.
	var s: Dictionary = genome.scalars
	p["size"] = p["size"] * s.get("size", 1.0)
	p["maxSpeed"] = p["maxSpeed"] * s.get("speedBias", 1.0)
	p["metabolicEfficiency"] = s.get("metabolicEfficiency", 1.0)
	p["tempOptimum"] = s.get("tempOptimum", p["tempOptimum"])
	p["lightOptimum"] = s.get("lightOptimum", p["lightOptimum"])
	p["pressureOptimum"] = s.get("pressureOptimum", p["pressureOptimum"])

	# Trait modules apply ON TOP of the genetic baseline, so an attachment
	# (e.g. dark pigment shifting lightOptimum) actually moves the compiled
	# value.
	var trait_drain := 0.0
	for tid in genome.trait_ids:
		var td: TraitDefinition = catalog.get_trait(tid)
		if td == null:
			push_error("PhenotypeCompiler: unknown trait id %s" % tid)
			continue
		for stat in td.stat_modifiers:
			var mod: Dictionary = td.stat_modifiers[stat]
			_apply_modifier(p, stat, mod["op"], mod["value"])
		for axis in td.tolerance_modifiers:
			var mod2: Dictionary = td.tolerance_modifiers[axis]
			_apply_modifier(p, axis, mod2["op"], mod2["value"])
		trait_drain += td.metabolic_cost

	p["tempOptimum"] = clampf(p["tempOptimum"], 0.0, 1.0)
	p["lightOptimum"] = clampf(p["lightOptimum"], 0.0, 1.0)
	p["pressureOptimum"] = clampf(p["pressureOptimum"], 0.0, 1.0)

	# Derived drains, pre-summed for the metabolism hot path (DESIGN §3).
	p["baseDrain"] = SimConfig.BODY_BASE * pow(p["size"], SimConfig.SIZE_EXP)
	p["traitDrain"] = trait_drain
	return p


static func _apply_modifier(target: Dictionary, key: String, op: String, value: float) -> void:
	if not target.has(key):
		# tolerance ranges may not exist on the base plan for every axis; seed at 0
		target[key] = 0.0
	if op == "add":
		target[key] = target[key] + value
	elif op == "mul":
		target[key] = target[key] * value
	else:
		push_error("PhenotypeCompiler: unknown modifier op %s" % op)


## Minor mutation on reproduction: drift continuous genes only (DESIGN §5.4).
## Structural genes (trait_ids) are copied verbatim — adding a trait requires
## player intervention + Evo Points, never spontaneous mutation.
static func mutate(genome: Genome, rng: RandomNumberGenerator) -> Genome:
	var g := genome.duplicate_genome()
	g.generation += 1
	for key in g.scalars.keys():
		g.scalars[key] = g.scalars[key] * (1.0 + rng.randfn(0.0, SimConfig.MUT_SIGMA))
		if SimConfig.GENE_BOUNDS.has(key):
			var bounds: Array = SimConfig.GENE_BOUNDS[key]
			g.scalars[key] = clampf(g.scalars[key], bounds[0], bounds[1])
	return g
