extends CanvasLayer
## Minimal debug UI: energy/age/state of the tracked organism + recent events.
## Echoes the event-log concept from DESIGN §2.7 without the full scrolling UI.

var label: Label


func _ready() -> void:
	label = Label.new()
	label.position = Vector2(12, 12)
	label.add_theme_font_size_override("font_size", 16)
	label.add_theme_color_override("font_color", Color.WHITE)
	label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	label.add_theme_constant_override("shadow_offset_x", 1)
	label.add_theme_constant_override("shadow_offset_y", 1)
	add_child(label)


func update_readout(tracked: OrganismAgent, population: int, log: EventLog, state_name: String) -> void:
	var lines: Array[String] = []
	lines.append("EvoTank vertical slice — population: %d — state: %s" % [population, state_name])
	if tracked:
		lines.append("tracked organism — energy: %.1f  age: %.1f  speed: %.2f  gen: %d" % [
			tracked.energy, tracked.age, tracked.speed, tracked.genome.generation,
		])
		lines.append("traits: %s" % (", ".join(tracked.genome.trait_ids) if not tracked.genome.trait_ids.is_empty() else "(none)"))
	else:
		lines.append("(no organism to track — extinct)")
	lines.append("")
	lines.append("recent events:")
	for ev in log.recent(6):
		lines.append("  t=%.0f  %s  %s" % [ev["t"], ev["kind"], ev["detail"]])
	label.text = "\n".join(lines)
