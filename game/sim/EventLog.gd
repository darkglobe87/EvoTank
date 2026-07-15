class_name EventLog
extends RefCounted
## Scrolling event log (DESIGN §2.7). Ported from prototype/evotank_sim/events.py.
## digest()/idle summary omitted — cohort/idle path is out of scope this phase.

const CAPACITY := 200

var _buf: Array = []          # ring buffer of {t, kind, detail}
var counts: Dictionary = {}   # kind -> count


func push(t: float, kind: String, detail: String = "") -> void:
	_buf.append({"t": t, "kind": kind, "detail": detail})
	if _buf.size() > CAPACITY:
		_buf.pop_front()
	counts[kind] = counts.get(kind, 0) + 1


func recent(n: int = 20) -> Array:
	var start: int = maxi(0, _buf.size() - n)
	return _buf.slice(start)
