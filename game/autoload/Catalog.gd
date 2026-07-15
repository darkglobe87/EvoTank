extends Node
## Autoload singleton: the one global. Wraps TraitCatalog, loaded once at boot.
## DESIGN §5.1: traits are external data — this is where they enter the game.

var catalog: TraitCatalog


func _ready() -> void:
	catalog = TraitCatalog.load_from("res://data/traits")
	print("Catalog: loaded %d trait(s): %s" % [catalog.size(), catalog.ids()])
