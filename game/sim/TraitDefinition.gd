class_name TraitDefinition
extends Resource
## A data-driven trait module (DESIGN §5.1). Declares BOTH visual and
## statistical effects from the same asset, so the two never diverge.
##
## Ported from prototype/evotank_sim/genetics.py TraitDefinition. Loaded from
## JSON (see prototype/data/traits/*.json / game/data/traits/*.json), not
## authored as a .tres — keeps "adding a trait = adding a data file" true.

var id: String = ""
var display_name: String = ""
var category: String = "misc"
var evo_cost: float = 0.0
var metabolic_cost: float = 0.0
var stat_modifiers: Dictionary = {}       # {stat: {"op": "add"|"mul", "value": float}}
var tolerance_modifiers: Dictionary = {}  # {axis: {"op": "add"|"mul", "value": float}}
var visual: Dictionary = {}               # {"mesh": String, "attachPoint": String, "scaleWithSize": bool}
var prerequisites: Array = []
var incompatible_with: Array = []


static func from_json(d: Dictionary) -> TraitDefinition:
	var td := TraitDefinition.new()
	td.id = d["id"]
	td.display_name = d.get("displayName", td.id)
	td.category = d.get("category", "misc")
	td.evo_cost = float(d.get("evoCost", 0))
	td.metabolic_cost = float(d.get("metabolicCost", 0.0))
	td.stat_modifiers = d.get("statModifiers", {})
	td.tolerance_modifiers = d.get("toleranceModifiers", {})
	td.visual = d.get("visual", {})
	td.prerequisites = d.get("prerequisites", [])
	td.incompatible_with = d.get("incompatibleWith", [])
	return td
