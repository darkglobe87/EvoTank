"""DESIGN §11.4 — extinction / rescue state machine (live + idle-resume paths).

Drives the ExtinctionController through the population transitions it must
handle, including a species that goes extinct *while the app is closed* (the
idle-resume path), and confirms every transition.
"""

import _util  # noqa: F401  (path bootstrap)

from evotank_sim.cohort import Cohort, CohortModel
from evotank_sim.extinction import ExtinctionController, SimState
from evotank_sim.genetics import Genome, compile_genome
from evotank_sim.metabolism import metabolic_drain


def scripted_transitions():
    ctrl = ExtinctionController()
    checks = []

    def check(pop, expected):
        state = ctrl.evaluate(pop)
        ok = state == expected
        checks.append(ok)
        print(f"  pop={pop:>2} -> {state.value:<12} (expect {expected.value}) "
              f"{'ok' if ok else 'MISMATCH'}")
        return ok

    print("live transitions:")
    check(5, SimState.RUNNING)
    check(2, SimState.RUNNING)
    check(1, SimState.LAST_CHANCE)          # population == 1 -> pause + revive offer
    revived = ctrl.apply_revive()
    print(f"  apply_revive() -> {revived} (species rescued to 2)")
    check(2, SimState.RUNNING)
    check(1, SimState.LAST_CHANCE)
    check(0, SimState.GAME_OVER)            # population == 0 -> game over
    # Game over is terminal: further evaluates must not resurrect it.
    check(3, SimState.GAME_OVER)
    checks.append(revived)
    return all(checks)


def extinct_while_idle():
    """A cohort collapses to 0 during the idle interval; resume must detect it."""
    print("\nidle-resume extinction path:")
    cat = _util.catalog()
    g = Genome(lineageId="doomed")
    ph = compile_genome(g, cat)
    cohort = Cohort(g, ph, N=3.0, meanEnergy=5.0, meanAge=550.0)
    # Force a hostile regime: no births, heavy death.
    model = CohortModel(dict(B0=0.0, D0=0.05, S=0.05, K=50.0))
    result = model.advance([cohort], food_stock=0.0, elapsed=8 * 3600)
    survivors = int(round(sum(c.N for c in result.cohorts)))
    ctrl = ExtinctionController()
    state = ctrl.evaluate(survivors)
    ok = survivors == 0 and state == SimState.GAME_OVER
    print(f"  cohort N: 3 -> {survivors} after 8h idle; resume state = {state.value} "
          f"{'ok' if ok else 'MISMATCH'}")
    return ok


def main():
    print("\n=== Extinction / rescue FSM (DESIGN §11.4) ===")
    ok = scripted_transitions()
    ok = extinct_while_idle() and ok
    print(f"[{'PASS' if ok else 'FAIL'}] extinction_fsm")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
