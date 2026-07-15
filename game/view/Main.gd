extends Node3D
## Root scene. Owns the LiveSim and drives the fixed-timestep accumulator
## (DESIGN §2: 10 Hz sim, render interpolates). The view layer only OBSERVES
## sim state via LiveSim's signals + OrganismAgent fields — it never mutates
## the sim directly.

const ORGANISM_VIEW_SCENE: PackedScene = preload("res://view/OrganismView.tscn")

@onready var tank_view: Node3D = $TankView
@onready var debug_readout: CanvasLayer = $DebugUI

var live_sim: LiveSim
var extinction: ExtinctionController
var _views: Dictionary = {}  # OrganismAgent -> OrganismView
var _tracked: OrganismAgent
var _accum: float = 0.0


func _ready() -> void:
	live_sim = LiveSim.new(Catalog.catalog, SimConfig.SEED)
	extinction = ExtinctionController.new()

	live_sim.organism_born.connect(_on_born)
	live_sim.organism_died.connect(_on_died)

	# Founder carries dorsal_fin — proves traits are simultaneously visual
	# modules and stat modifiers (DESIGN §5.1 / vertical slice exit criterion 5).
	var founder_genome := Genome.new("protoblob", ["dorsal_fin"], {}, 0, "founder")
	live_sim.seed_species(founder_genome, 1)
	for org in live_sim.organisms:
		_spawn_view(org)
	if not live_sim.organisms.is_empty():
		_tracked = live_sim.organisms[0]

	print("EvoTank vertical slice ready. founder maxSpeed=%.2f (baseline 4.0 + dorsal_fin)" %
		live_sim.organisms[0].phenotype["maxSpeed"])


func _process(delta: float) -> void:
	if live_sim == null:
		return
	_accum += delta
	var step: float = 1.0 / SimConfig.SIM_SPEED
	while _accum >= step:
		_accum -= step
		live_sim.tick(SimConfig.TICK_DT)
		extinction.evaluate(live_sim.population())
		if _tracked != null and not live_sim.organisms.has(_tracked):
			_tracked = live_sim.organisms[0] if not live_sim.organisms.is_empty() else null

	for org in _views:
		_views[org].sync_transform()

	if debug_readout:
		debug_readout.update_readout(
			_tracked, live_sim.population(), live_sim.log,
			ExtinctionController.SimState.keys()[extinction.state]
		)


func _spawn_view(org: OrganismAgent) -> void:
	var view: Node3D = ORGANISM_VIEW_SCENE.instantiate()
	tank_view.add_child(view)
	view.bind(org)
	_views[org] = view


func _on_born(org: OrganismAgent) -> void:
	_spawn_view(org)


func _on_died(org: OrganismAgent, _cause: String) -> void:
	if _views.has(org):
		_views[org].queue_free()
		_views.erase(org)
