extends SceneTree
## Headless verification runner. Run with:
##   godot --headless --path . --script res://test/test_runner.gd
##
## Asserts the ported GDScript sim produces numbers traceable to the Python
## prototype's validated outputs (prototype/FINDINGS.md). No GPU/window/Android
## needed — this is the cheapest gate, same role as the prototype's pytest
## suite and experiment harnesses.

var _pass_count := 0
var _fail_count := 0


func _initialize() -> void:
	print("=== EvoTank GDScript port — headless verification ===\n")

	_test_genetics_compile()
	_test_environment_grid()
	_test_live_sim_life_cycle()
	_test_extinction_fsm()

	print("\n=== %d passed, %d failed ===" % [_pass_count, _fail_count])
	quit(1 if _fail_count > 0 else 0)


func _check(label: String, cond: bool, detail: String = "") -> void:
	if cond:
		_pass_count += 1
		print("  [PASS] %s" % label)
	else:
		_fail_count += 1
		print("  [FAIL] %s  %s" % [label, detail])


func _almost(a: float, b: float, eps: float = 1e-6) -> bool:
	return absf(a - b) < eps


# --- M1: genetics / compile order -------------------------------------------
func _test_genetics_compile() -> void:
	print("-- genetics / PhenotypeCompiler (M1) --")
	var catalog := TraitCatalog.load_from("res://data/traits")
	_check("catalog loads 7 traits", catalog.size() == 7, "got %d" % catalog.size())

	var base_p := PhenotypeCompiler.compile_genome(Genome.new(), catalog)
	# Ground truth from the Python prototype (prototype/evotank_sim/genetics.py):
	# base baseDrain=0.150000 maxSpeed=4.000000 traitDrain=0.000000 turnRate=1.000000
	_check("base baseDrain == 0.15", _almost(base_p["baseDrain"], 0.15), str(base_p["baseDrain"]))
	_check("base maxSpeed == 4.0", _almost(base_p["maxSpeed"], 4.0), str(base_p["maxSpeed"]))
	_check("base traitDrain == 0.0", _almost(base_p["traitDrain"], 0.0), str(base_p["traitDrain"]))

	var fin_genome := Genome.new("protoblob", ["dorsal_fin"])
	var fin_p := PhenotypeCompiler.compile_genome(fin_genome, catalog)
	# Ground truth: fin baseDrain=0.150000 maxSpeed=5.000000 traitDrain=0.050000 turnRate=1.150000
	_check("fin baseDrain unchanged == 0.15", _almost(fin_p["baseDrain"], 0.15), str(fin_p["baseDrain"]))
	_check("fin maxSpeed == baseline+1.0 == 5.0", _almost(fin_p["maxSpeed"], 5.0), str(fin_p["maxSpeed"]))
	_check("fin traitDrain == 0.05", _almost(fin_p["traitDrain"], 0.05), str(fin_p["traitDrain"]))
	_check("fin turnRate == 1.15", _almost(fin_p["turnRate"], 1.15), str(fin_p["turnRate"]))

	# Compile-order regression test (FINDINGS.md bug #1): dark_pigment must
	# actually shift lightOptimum, proving traits apply AFTER scalars.
	var base_lo: float = base_p["lightOptimum"]
	var dark_genome := Genome.new("protoblob", ["dark_pigment"])
	var dark_p := PhenotypeCompiler.compile_genome(dark_genome, catalog)
	_check("dark_pigment shifts lightOptimum down (bug #1 regression)",
		dark_p["lightOptimum"] < base_lo,
		"base=%.3f dark=%.3f" % [base_lo, dark_p["lightOptimum"]])

	# Mutation stays within GENE_BOUNDS and never touches trait_ids.
	var rng := RandomNumberGenerator.new()
	rng.seed = SimConfig.SEED
	var g := Genome.new()
	for i in range(200):
		g = PhenotypeCompiler.mutate(g, rng)
	var bounds_ok := true
	for key in SimConfig.GENE_BOUNDS:
		var b: Array = SimConfig.GENE_BOUNDS[key]
		if g.scalars[key] < b[0] or g.scalars[key] > b[1]:
			bounds_ok = false
	_check("mutation stays within GENE_BOUNDS after 200 generations", bounds_ok)
	_check("mutation never adds trait_ids", g.trait_ids.is_empty())
	_check("mutation increments generation", g.generation == 200, str(g.generation))
	print("")


# --- M2: environment grid ----------------------------------------------------
func _test_environment_grid() -> void:
	print("-- EnvironmentGrid (M2) --")
	var grid := EnvironmentGrid.new()

	var light_top := grid.sample_light(SimConfig.TANK_W * 0.5, 0.0)
	var light_bottom := grid.sample_light(SimConfig.TANK_W * 0.5, SimConfig.TANK_H - 1.0)
	_check("light bright at surface (y=0)", light_top > 0.9, str(light_top))
	_check("light dim at floor", light_bottom < 0.1, str(light_bottom))

	var pressure_top := grid.sample_pressure(SimConfig.TANK_W * 0.5, 0.0)
	var pressure_bottom := grid.sample_pressure(SimConfig.TANK_W * 0.5, SimConfig.TANK_H - 1.0)
	_check("pressure low at surface", pressure_top < 0.1, str(pressure_top))
	_check("pressure high at floor", pressure_bottom > 0.9, str(pressure_bottom))

	# Default phenotype is optimum-tuned to the tank midpoint (0.5,0.5,0.5) —
	# comfort/stress should be near-ideal there.
	var catalog := TraitCatalog.load_from("res://data/traits")
	var p := PhenotypeCompiler.compile_genome(Genome.new(), catalog)
	var mid_x := SimConfig.TANK_W * 0.5
	var mid_y := SimConfig.TANK_H * 0.5
	var stress_mid := grid.stress(p, mid_x, mid_y)
	_check("stress ~= 1.0 at comfort optimum", _almost(stress_mid, 1.0, 0.05), str(stress_mid))

	var stress_edge := grid.stress(p, mid_x, 0.0)  # far from pressure/temp/light optimum
	_check("stress > 1.0 away from optimum", stress_edge > 1.0, str(stress_edge))

	grid.eat_at(mid_x, mid_y, 100.0)  # drain a cell fully
	var eaten := grid.eat_at(mid_x, mid_y, 1.0)
	_check("depleted cell yields no more food", _almost(eaten, 0.0), str(eaten))
	grid.regen_food(1000.0)
	var regrown := grid.sample_food(mid_x, mid_y)
	_check("food regenerates over time (logistic)", regrown > 0.0, str(regrown))
	print("")


# --- M3: live sim tick loop ---------------------------------------------------
func _test_live_sim_life_cycle() -> void:
	print("-- LiveSim tick loop (M3) --")
	var catalog := TraitCatalog.load_from("res://data/traits")
	var sim := LiveSim.new(catalog, SimConfig.SEED)
	sim.seed_species(Genome.new(), 1)
	_check("one organism seeded", sim.organisms.size() == 1)

	var births := 0
	var deaths := 0
	var reached_maturity := false
	for i in range(3000):
		var before := sim.organisms.size()
		sim.tick(1.0)
		var after := sim.organisms.size()
		if after > before:
			births += 1
		if sim.log.counts.get("DEATH", 0) > deaths:
			deaths = sim.log.counts.get("DEATH", 0)
		if sim.organisms.is_empty():
			break

	_check("a full life cycle occurred (birth or death recorded)",
		births > 0 or deaths > 0,
		"births=%d deaths=%d" % [births, deaths])
	print("  (births=%d, deaths=%d over up to 3000 ticks)" % [births, deaths])
	print("")


# --- extinction FSM ------------------------------------------------------------
func _test_extinction_fsm() -> void:
	print("-- ExtinctionController FSM --")
	var ctrl := ExtinctionController.new()
	_check("5 -> RUNNING", ctrl.evaluate(5) == ExtinctionController.SimState.RUNNING)
	_check("1 -> LAST_CHANCE", ctrl.evaluate(1) == ExtinctionController.SimState.LAST_CHANCE)
	var revived := ctrl.apply_revive()
	_check("revive succeeds from LAST_CHANCE", revived)
	_check("0 -> GAME_OVER", ctrl.evaluate(0) == ExtinctionController.SimState.GAME_OVER)
	_check("GAME_OVER is terminal", ctrl.evaluate(10) == ExtinctionController.SimState.GAME_OVER)
	print("")
