"""Extinction & rescue state machine (DESIGN §8).

Pure population-count logic, decoupled from the sim so it can be unit-tested and
reused by both the live loop and the idle resume path.
"""

from __future__ import annotations

from enum import Enum


class SimState(Enum):
    RUNNING = "running"
    LAST_CHANCE = "last_chance"   # population == 1: pause + offer revive
    GAME_OVER = "game_over"       # population == 0: finalize Evo Points


class ExtinctionController:
    def __init__(self):
        self.state = SimState.RUNNING
        self.revive_offered = False

    def evaluate(self, population: int) -> SimState:
        """Called every tick and immediately after idle inflate()."""
        if population <= 0:
            self.state = SimState.GAME_OVER
        elif population == 1:
            if self.state != SimState.GAME_OVER:
                self.state = SimState.LAST_CHANCE
                self.revive_offered = True
        else:
            if self.state != SimState.GAME_OVER:
                self.state = SimState.RUNNING
        return self.state

    def apply_revive(self) -> bool:
        """Consume the last-chance offer (premium currency / rewarded ad)."""
        if self.state == SimState.LAST_CHANCE and self.revive_offered:
            self.revive_offered = False
            self.state = SimState.RUNNING
            return True
        return False
