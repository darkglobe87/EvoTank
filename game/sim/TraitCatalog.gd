class_name TraitCatalog
extends RefCounted
## Loads and indexes all TraitDefinition assets from JSON (DESIGN §5.1).
## Ported from prototype/evotank_sim/genetics.py TraitCatalog.

var _traits: Dictionary = {}  # id -> TraitDefinition


static func load_from(directory: String) -> TraitCatalog:
	var catalog := TraitCatalog.new()
	var dir := DirAccess.open(directory)
	if dir == null:
		push_error("TraitCatalog: no trait assets found in %s" % directory)
		return catalog
	var names: Array = []
	dir.list_dir_begin()
	var fname := dir.get_next()
	while fname != "":
		if not dir.current_is_dir() and fname.ends_with(".json"):
			names.append(fname)
		fname = dir.get_next()
	dir.list_dir_end()
	names.sort()  # deterministic load order, matches prototype's sorted glob()

	for n in names:
		var path := directory.path_join(n)
		var text := FileAccess.get_file_as_string(path)
		var parsed = JSON.parse_string(text)
		if parsed == null:
			push_error("TraitCatalog: failed to parse %s" % path)
			continue
		var td := TraitDefinition.from_json(parsed)
		catalog._traits[td.id] = td

	if catalog._traits.is_empty():
		push_error("TraitCatalog: no trait assets found in %s" % directory)
	return catalog


func get_trait(trait_id: String) -> TraitDefinition:
	return _traits.get(trait_id)


func has_trait(trait_id: String) -> bool:
	return _traits.has(trait_id)


func ids() -> Array:
	return _traits.keys()


func size() -> int:
	return _traits.size()
