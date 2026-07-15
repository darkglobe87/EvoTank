"""Scrolling event log (DESIGN §2.7) + idle event digest (DESIGN §6.4)."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass


@dataclass
class Event:
    t: float
    kind: str          # BIRTH | DEATH | FEED | MILESTONE | RIVAL
    detail: str = ""


class EventLog:
    def __init__(self, capacity: int = 200):
        self._buf: deque[Event] = deque(maxlen=capacity)
        self.counts: Counter = Counter()

    def push(self, t: float, kind: str, detail: str = "") -> None:
        self._buf.append(Event(t, kind, detail))
        self.counts[kind] += 1

    def recent(self, n: int = 20):
        return list(self._buf)[-n:]

    def digest(self, elapsed: float) -> str:
        """One-line 'while you were away' summary for the idle path."""
        hrs = int(elapsed // 3600)
        mins = int((elapsed % 3600) // 60)
        return (
            f"While you were away ({hrs}h {mins}m): "
            f"+{self.counts['BIRTH']} births, -{self.counts['DEATH']} deaths"
        )
