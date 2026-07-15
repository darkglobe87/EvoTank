class_name EnvironmentGrid
extends RefCounted
## Environment grid & trait-based navigation (DESIGN §4).
## Ported from prototype/evotank_sim/environment.py.
##
## A layered scalar field over a coarse grid. Static gradients (light/temp/
## pressure) are baked functions of position; the dynamic layer (food) evolves
## over time. Creatures navigate by climbing the trait-derived `comfort` field
## — no pathfinding needed.
##
## Perf note: fields are flat PackedFloat32Array (index y*w+x), not nested
## arrays/dictionaries — avoids GDScript's boxing/allocation cost in the hot
## path (comfort/stress run per-agent, per-tick, and will scale to 50-150
## agents later even though the vertical slice runs 1).

var w: int = SimConfig.GRID_W
var h: int = SimConfig.GRID_H
var light: PackedFloat32Array
var temp: PackedFloat32Array
var pressure: PackedFloat32Array
var food: PackedFloat32Array


func _init() -> void:
	light = PackedFloat32Array()
	temp = PackedFloat32Array()
	pressure = PackedFloat32Array()
	food = PackedFloat32Array()
	light.resize(w * h)
	temp.resize(w * h)
	pressure.resize(w * h)
	food.resize(w * h)

	# Baked static gradients, normalized 0..1. y=0 is the surface (top).
	# Matches np.linspace(0,1,h)[row] = row/(h-1); bright/warm at surface,
	# high pressure at depth.
	for row in range(h):
		var ys: float = float(row) / float(max(1, h - 1))
		var light_val := 1.0 - ys
		var pressure_val := ys
		for col in range(w):
			var idx := row * w + col
			light[idx] = light_val
			temp[idx] = light_val
			pressure[idx] = pressure_val
	# food starts at zero here; LiveSim seeds standing food on construction
	# (mirrors prototype/live_sim.py's warm-up behavior).


# --- indexing helpers ---------------------------------------------------------
func cell_of(x: float, y: float) -> Vector2i:
	var cx: int = clampi(int(x / SimConfig.TANK_W * w), 0, w - 1)
	var cy: int = clampi(int(y / SimConfig.TANK_H * h), 0, h - 1)
	return Vector2i(cx, cy)


func cell_center(cx: int, cy: int) -> Vector2:
	var x: float = (cx + 0.5) / float(w) * SimConfig.TANK_W
	var y: float = (cy + 0.5) / float(h) * SimConfig.TANK_H
	return Vector2(x, y)


## Bilinear sample of a flat scalar field at world (x, y) (DESIGN §4.1).
func _bilinear(field: PackedFloat32Array, x: float, y: float) -> float:
	var gx: float = x / SimConfig.TANK_W * w - 0.5
	var gy: float = y / SimConfig.TANK_H * h - 0.5
	var x0: int = clampi(int(floor(gx)), 0, w - 1)
	var y0: int = clampi(int(floor(gy)), 0, h - 1)
	var x1: int = mini(w - 1, x0 + 1)
	var y1: int = mini(h - 1, y0 + 1)
	var tx: float = clampf(gx - x0, 0.0, 1.0)
	var ty: float = clampf(gy - y0, 0.0, 1.0)
	var top: float = field[y0 * w + x0] * (1.0 - tx) + field[y0 * w + x1] * tx
	var bot: float = field[y1 * w + x0] * (1.0 - tx) + field[y1 * w + x1] * tx
	return top * (1.0 - ty) + bot * ty


func sample_light(x: float, y: float) -> float:
	return _bilinear(light, x, y)


func sample_temperature(x: float, y: float) -> float:
	return _bilinear(temp, x, y)


func sample_pressure(x: float, y: float) -> float:
	return _bilinear(pressure, x, y)


func sample_food(x: float, y: float) -> float:
	return _bilinear(food, x, y)


## Dictionary-returning sampler for non-hot-path callers only (debug overlay
## etc.) — avoid in the per-agent, per-tick hot path (allocates each call).
func sample(x: float, y: float) -> Dictionary:
	return {
		"light": sample_light(x, y),
		"temperature": sample_temperature(x, y),
		"pressure": sample_pressure(x, y),
		"foodDensity": sample_food(x, y),
	}


# --- comfort & stress (DESIGN §4.2) -------------------------------------------
## Product of per-axis Gaussians: ~1 in the ideal niche, ->0 in hostile.
## Returns a float directly (no Dictionary allocation) — hot path.
func comfort(phenotype: Dictionary, x: float, y: float) -> float:
	var c := 1.0

	var temp_range: float = maxf(1e-3, phenotype["tempRange"])
	var dt: float = sample_temperature(x, y) - phenotype["tempOptimum"]
	c *= exp(-(dt * dt) / (2.0 * temp_range * temp_range))

	var light_range: float = maxf(1e-3, phenotype["lightRange"])
	var dl: float = sample_light(x, y) - phenotype["lightOptimum"]
	c *= exp(-(dl * dl) / (2.0 * light_range * light_range))

	var pressure_range: float = maxf(1e-3, phenotype["pressureRange"])
	var dp: float = sample_pressure(x, y) - phenotype["pressureOptimum"]
	c *= exp(-(dp * dp) / (2.0 * pressure_range * pressure_range))

	return c


func stress(phenotype: Dictionary, x: float, y: float) -> float:
	return 1.0 + SimConfig.STRESS_K * (1.0 - comfort(phenotype, x, y))


# --- dynamic update (DESIGN §4.3) ----------------------------------------------
## Logistic self-limiting regrowth so food never piles up unbounded.
func regen_food(dt: float) -> void:
	var cap: float = SimConfig.FOOD_CAP_PER_CELL
	var rate: float = SimConfig.FOOD_REGEN_RATE
	for i in range(food.size()):
		var v: float = food[i] + rate * (1.0 - food[i] / cap) * dt
		food[i] = clampf(v, 0.0, cap)


func total_food() -> float:
	var total := 0.0
	for v in food:
		total += v
	return total


## Consume up to `amount` food units from the organism's cell.
func eat_at(x: float, y: float, amount: float) -> float:
	var cell := cell_of(x, y)
	var idx := cell.y * w + cell.x
	var available: float = food[idx]
	var eaten: float = minf(amount, available)
	food[idx] = available - eaten
	return eaten
