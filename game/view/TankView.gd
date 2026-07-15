extends Node3D
## Backdrop representing the tank bounds (2.5D fluid tank, DESIGN's brief).
## Purely visual — sized from SimConfig, no simulation state.


func _ready() -> void:
	var w: float = SimConfig.TANK_W * SimConfig.WORLD_SCALE
	var h: float = SimConfig.TANK_H * SimConfig.WORLD_SCALE

	var backdrop := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(w, h)
	plane.orientation = PlaneMesh.FACE_Z
	backdrop.mesh = plane
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.08, 0.25, 0.35, 0.9)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	backdrop.set_surface_override_material(0, mat)
	backdrop.position = Vector3(w * 0.5, h * 0.5, -0.5)
	add_child(backdrop)
