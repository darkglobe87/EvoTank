extends Node3D
## View-layer representation of one OrganismAgent (DESIGN §1 "view observes sim").
## Owns no simulation state — every frame it just reads the bound agent and
## updates its transform + attached trait meshes. Never writes back to the sim.

@onready var body: MeshInstance3D = $Body
@onready var energy_bar: MeshInstance3D = $EnergyBar

var agent: OrganismAgent
var _attach_points: Dictionary = {}  # attachPoint name -> Marker3D
var _traits_applied: bool = false


func _ready() -> void:
	for child in get_children():
		if child is Marker3D:
			_attach_points[child.name] = child


func bind(p_agent: OrganismAgent) -> void:
	agent = p_agent
	sync_transform()
	if not _traits_applied:
		apply_traits(agent.genome)
		_traits_applied = true


## Maps sim space (x, y with y=0 at the surface) to the render plane.
## Y is flipped so depth renders downward; Z is locked to 0 for the
## "3D model on a 2D plane" 2.5D look (DESIGN's 2.5D side-scrolling brief).
func sync_transform() -> void:
	if agent == null:
		return
	position = Vector3(
		agent.x * SimConfig.WORLD_SCALE,
		(SimConfig.TANK_H - agent.y) * SimConfig.WORLD_SCALE,
		0.0
	)
	var base_scale: float = agent.phenotype.get("size", 1.0)
	scale = Vector3.ONE * base_scale
	# Face the direction of travel (rotate around Y using vx/vz-as-x mapping).
	if agent.vx * agent.vx + agent.vy * agent.vy > 1e-6:
		var heading := atan2(agent.vx, agent.vy)
		rotation.y = heading

	var energy_frac: float = clampf(agent.energy / agent.phenotype.get("reproThreshold", 60.0), 0.0, 1.5)
	if energy_bar:
		energy_bar.scale.x = maxf(0.05, energy_frac)
		var mat := energy_bar.get_surface_override_material(0) as StandardMaterial3D
		if mat:
			mat.albedo_color = Color(1.0 - clampf(energy_frac, 0.0, 1.0), clampf(energy_frac, 0.0, 1.0), 0.2)


## Attaches a placeholder mesh at each trait's declared attachPoint AND
## records the stat effect is already baked into agent.phenotype (compiled
## before this view was bound) — proving traits are simultaneously visual
## modules and stat modifiers (DESIGN §5.1).
func apply_traits(genome: Genome) -> void:
	if Catalog.catalog == null:
		return
	for trait_id in genome.trait_ids:
		var td: TraitDefinition = Catalog.catalog.get_trait(trait_id)
		if td == null:
			continue
		var attach_name: String = td.visual.get("attachPoint", "")
		var marker: Marker3D = _attach_points.get(attach_name)
		if marker == null:
			push_warning("OrganismView: no attach point '%s' for trait '%s'" % [attach_name, trait_id])
			continue
		var mesh_inst := MeshInstance3D.new()
		mesh_inst.name = "Trait_%s" % trait_id
		mesh_inst.mesh = _placeholder_mesh_for(td.category)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = _placeholder_color_for(td.category)
		mesh_inst.set_surface_override_material(0, mat)
		if td.visual.get("scaleWithSize", false):
			mesh_inst.scale = Vector3.ONE * agent.phenotype.get("size", 1.0)
		marker.add_child(mesh_inst)


## Placeholder geometry only — final art loads td.visual["mesh"] by path once
## real assets exist. Distinct primitive per category keeps traits visually
## distinguishable during the vertical slice.
func _placeholder_mesh_for(category: String) -> Mesh:
	match category:
		"locomotion":
			var m := PrismMesh.new()
			m.size = Vector3(0.15, 0.3, 0.05)
			return m
		"defense":
			var m := BoxMesh.new()
			m.size = Vector3(0.3, 0.3, 0.3)
			return m
		_:
			var m := SphereMesh.new()
			m.radius = 0.08
			m.height = 0.16
			return m


func _placeholder_color_for(category: String) -> Color:
	match category:
		"locomotion": return Color(0.3, 0.7, 1.0)
		"defense": return Color(0.6, 0.6, 0.65)
		"sensory": return Color(1.0, 0.9, 0.3)
		"metabolic": return Color(0.4, 1.0, 0.5)
		"offense": return Color(1.0, 0.3, 0.3)
		"adaptation": return Color(0.5, 0.2, 0.6)
		_: return Color(0.8, 0.8, 0.8)
