class_name OrganismAgent
extends RefCounted
## Organism entity + utility-AI brain (DESIGN §2.2).
## Ported from prototype/evotank_sim/organism.py.
##
## Sense -> decide -> act. The brain scores a small set of drives and blends a
## heading from (a) the direction to nearby food and (b) the local comfort
## gradient. Weighting shifts toward foraging as energy falls. No pathfinding.

var genome: Genome
var phenotype: Dictionary
var x: float
var y: float
var vx: float = 0.0
var vy: float = 0.0
var energy: float
var age: float = 0.0
var hp: float
var last_birth_age: float = 0.0
var speed: float = 0.0


func _init(p_genome: Genome, p_phenotype: Dictionary, p_x: float, p_y: float, p_energy: float) -> void:
	genome = p_genome
	phenotype = p_phenotype
	x = p_x
	y = p_y
	energy = p_energy
	hp = phenotype["hp"]


# --- sense + decide + act -----------------------------------------------------
func step_movement(grid: EnvironmentGrid, rng: RandomNumberGenerator, dt: float) -> void:
	var p := phenotype
	var sense: float = p["senseRadius"]

	# (a) Forage vector: head toward the richest food cell within sense radius.
	var fx := 0.0
	var fy := 0.0
	var best := 0.0
	var cell := grid.cell_of(x, y)
	var reach: int = maxi(1, int(sense / (SimConfig.TANK_W / grid.w)))
	for dy in range(-reach, reach + 1):
		for dx in range(-reach, reach + 1):
			var gx: int = cell.x + dx
			var gy: int = cell.y + dy
			if gx >= 0 and gx < grid.w and gy >= 0 and gy < grid.h:
				var f: float = grid.food[gy * grid.w + gx]
				if f > best:
					var center := grid.cell_center(gx, gy)
					var ddx: float = center.x - x
					var ddy: float = center.y - y
					if ddx * ddx + ddy * ddy <= sense * sense:
						best = f
						fx = ddx
						fy = ddy
	var forage := _normalize(fx, fy)

	# (b) Comfort gradient: sample 4 neighbours, steer toward higher comfort.
	var step: float = SimConfig.TANK_W / grid.w
	var here: float = grid.comfort(p, x, y)
	var gxv: float = grid.comfort(p, x + step, y) - grid.comfort(p, x - step, y)
	var gyv: float = grid.comfort(p, x, y + step) - grid.comfort(p, x, y - step)
	var comfort_dir := _normalize(gxv, gyv)

	# Drive weighting: hungrier organisms prioritise food over comfort.
	var hunger: float = 1.0 - minf(1.0, energy / p["reproThreshold"])
	var w_food: float = 0.35 + 0.55 * hunger
	var w_comfort: float = 0.25 + 0.35 * (1.0 - here)
	var w_wander: float = 0.15
	var wander := _normalize(rng.randfn(0.0, 1.0), rng.randfn(0.0, 1.0))

	var dirx: float = w_food * forage.x + w_comfort * comfort_dir.x + w_wander * wander.x
	var diry: float = w_food * forage.y + w_comfort * comfort_dir.y + w_wander * wander.y
	var dir := _normalize(dirx, diry)

	vx = dir.x * p["maxSpeed"]
	vy = dir.y * p["maxSpeed"]
	x = clampf(x + vx * dt, 0.0, SimConfig.TANK_W)
	y = clampf(y + vy * dt, 0.0, SimConfig.TANK_H)
	speed = sqrt(vx * vx + vy * vy)


func can_reproduce() -> bool:
	var p := phenotype
	return (
		energy >= p["reproThreshold"]
		and age >= p["maturity"]
		and (age - last_birth_age) >= SimConfig.REPRO_COOLDOWN
	)


func is_dead() -> bool:
	return energy <= 0.0 or age >= phenotype["lifespan"] or hp <= 0.0


func death_cause() -> String:
	if energy <= 0.0:
		return "starvation"
	if hp <= 0.0:
		return "predation"
	return "old age"


static func _normalize(vx_in: float, vy_in: float) -> Vector2:
	var m: float = sqrt(vx_in * vx_in + vy_in * vy_in)
	if m < 1e-9:
		return Vector2.ZERO
	return Vector2(vx_in / m, vy_in / m)
