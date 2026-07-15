class_name LiveSim
extends RefCounted
## Live agent-based simulation loop (DESIGN §2).
## Ported from prototype/evotank_sim/live_sim.py.
##
## Fixed-timestep tick over the whole tank in the DESIGN §2 order:
## environment -> sense/decide/act -> metabolism+feed -> death -> reproduction
## -> event log. Deterministic under a fixed seed.
##
## Pure sim layer: no Node dependency. Emits signals so the view layer can
## observe births/deaths without the sim knowing about rendering.

signal organism_born(organism: OrganismAgent)
signal organism_died(organism: OrganismAgent, cause: String)

var catalog: TraitCatalog
var rng: RandomNumberGenerator
var grid: EnvironmentGrid
var log: EventLog
var organisms: Array[OrganismAgent] = []
var time: float = 0.0


func _init(p_catalog: TraitCatalog, seed: int = SimConfig.SEED) -> void:
	catalog = p_catalog
	rng = RandomNumberGenerator.new()
	rng.seed = seed
	grid = EnvironmentGrid.new()
	log = EventLog.new()
	# Seed a modest standing-food level. Starting near full caused founders to
	# gorge and over-breed into a boom-bust crash (see prototype/FINDINGS.md);
	# 0.25 of cap gives a clean monotonic approach to carrying capacity instead.
	var seed_level: float = SimConfig.FOOD_CAP_PER_CELL * 0.25
	for i in range(grid.food.size()):
		grid.food[i] = seed_level


# --- seeding -------------------------------------------------------------------
func spawn(genome: Genome, sx=null, sy=null, energy: float = SimConfig.STARTING_ENERGY) -> OrganismAgent:
	var ph := PhenotypeCompiler.compile_genome(genome, catalog)
	var px: float = rng.randf_range(0.0, SimConfig.TANK_W) if sx == null else sx
	var py: float = rng.randf_range(0.0, SimConfig.TANK_H) if sy == null else sy
	var org := OrganismAgent.new(genome, ph, px, py, energy)
	organisms.append(org)
	return org


func seed_species(genome: Genome, count: int) -> void:
	for i in range(count):
		var g := genome.duplicate_genome()
		g.lineage_id = "%s-%d" % [genome.lineage_id, i]
		spawn(g)


# --- the tick (DESIGN §2) -------------------------------------------------------
func tick(dt: float = SimConfig.TICK_DT) -> void:
	time += dt
	grid.regen_food(dt)  # 1 environment

	for org in organisms:  # 2 sense/decide/act
		org.step_movement(grid, rng, dt)

	for org in organisms:  # 3 metabolism + feed
		org.age += dt
		var stress: float = grid.stress(org.phenotype, org.x, org.y)
		org.energy -= Metabolism.metabolic_drain(org.phenotype, org.speed, stress) * dt
		var eaten: float = grid.eat_at(org.x, org.y, org.phenotype["maxIntake"] * dt)
		if eaten > 0.0:
			org.energy += eaten * SimConfig.FOOD_ENERGY

	var survivors: Array[OrganismAgent] = []  # 4 death
	for org in organisms:
		if org.is_dead():
			var cause: String = org.death_cause()
			log.push(time, "DEATH", cause)
			organism_died.emit(org, cause)
		else:
			survivors.append(org)
	organisms = survivors

	var births: Array[OrganismAgent] = []  # (5 combat: none pre-rivals)
	if organisms.size() < SimConfig.POP_HARD_CAP:  # reproduction
		for org in organisms:
			if org.can_reproduce():
				org.energy -= org.phenotype["reproCost"]
				org.last_birth_age = org.age
				var child_genome := PhenotypeCompiler.mutate(org.genome, rng)
				var ph := PhenotypeCompiler.compile_genome(child_genome, catalog)
				var child := OrganismAgent.new(
					child_genome, ph,
					clampf(org.x + rng.randf_range(-5.0, 5.0), 0.0, SimConfig.TANK_W),
					clampf(org.y + rng.randf_range(-5.0, 5.0), 0.0, SimConfig.TANK_H),
					SimConfig.STARTING_ENERGY,
				)
				births.append(child)
				log.push(time, "BIRTH", "gen%d" % child_genome.generation)
				organism_born.emit(child)
	organisms.append_array(births)


func population() -> int:
	return organisms.size()
