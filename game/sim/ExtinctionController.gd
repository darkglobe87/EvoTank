class_name ExtinctionController
extends RefCounted
## Extinction & rescue state machine (DESIGN §8).
## Ported from prototype/evotank_sim/extinction.py.
## Pure population-count logic — no revive UI wired in the vertical slice,
## but the FSM states exist and are testable.

enum SimState { RUNNING, LAST_CHANCE, GAME_OVER }

var state: SimState = SimState.RUNNING
var revive_offered: bool = false


## Called every tick.
func evaluate(population: int) -> SimState:
	if population <= 0:
		state = SimState.GAME_OVER
	elif population == 1:
		if state != SimState.GAME_OVER:
			state = SimState.LAST_CHANCE
			revive_offered = true
	else:
		if state != SimState.GAME_OVER:
			state = SimState.RUNNING
	return state


## Consume the last-chance offer (premium currency / rewarded ad).
func apply_revive() -> bool:
	if state == SimState.LAST_CHANCE and revive_offered:
		revive_offered = false
		state = SimState.RUNNING
		return true
	return false
