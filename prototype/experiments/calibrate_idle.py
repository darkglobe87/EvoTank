"""DESIGN §11.2 — idle-vs-live calibration (THE critical gate).

Run the live agent sim headless from a fixed seed; fit the cohort model's
coefficients (B0, D0, K) to the live population curve; then report the drift.
If the fitted cohort model tracks the live sim within band, the whole
active/idle premise holds.
"""

import _util
import numpy as np

from evotank_sim import config
from evotank_sim.cohort import Cohort, CohortModel, deflate
from evotank_sim.genetics import compile_genome
from evotank_sim.live_sim import LiveSimulation

DURATION = 2500.0          # long enough for the live sim to reach its plateau
RECORD_EVERY = 50.0
SEED_POP = 8
WARMUP = 1000.0            # idle math predicts the long-run attractor, not the
                          # live-only transient; evaluate agreement past warmup.
DRIFT_TOLERANCE = 10.0     # percent, on final population
RMSE_TOLERANCE = 15.0      # percent, normalized RMSE across the SETTLED regime


def run_live():
    cat = _util.catalog()
    sim = LiveSimulation(cat, seed=config.SEED)
    founder = _util.species("solo")
    sim.seed_species(founder, SEED_POP)
    # Initial cohort snapshot BEFORE advancing (matches idle start state).
    cohorts0, food0 = deflate(sim)
    series = sim.run(DURATION, record_every=RECORD_EVERY)
    return cat, cohorts0, food0, series


def fit(cohorts0, food0, times, live_pop):
    keq = float(np.mean(live_pop[int(len(live_pop) * 0.75):]))  # measured carrying cap
    settled = times >= WARMUP                                   # evaluate on attractor
    best = None
    for K in np.linspace(keq * 0.8, keq * 1.3, 7):
        for B0 in np.linspace(0.008, 0.045, 8):
            for D0 in np.linspace(0.0008, 0.004, 6):
                model = CohortModel(dict(B0=B0, D0=D0, K=K))
                fresh = [Cohort(c.genome, c.phenotype, c.N, c.meanEnergy, c.meanAge)
                         for c in cohorts0]
                curve = model.curve_at(fresh, food0, times)
                rmse = float(np.sqrt(np.mean((curve[settled] - live_pop[settled]) ** 2)))
                if best is None or rmse < best[0]:
                    best = (rmse, dict(B0=B0, D0=D0, K=K), curve)
    return best, keq, settled


def main():
    cat, cohorts0, food0, series = run_live()
    times, live_pop = series["t"], series["pop"].astype(float)
    print("\n=== Idle-vs-live calibration (DESIGN §11.2) ===")
    print(f"live sim: {SEED_POP} founders -> {int(live_pop[-1])} after "
          f"{DURATION:.0f} ticks (peak {int(live_pop.max())})")

    (rmse, params, curve), keq, settled = fit(cohorts0, food0, times, live_pop)
    settled_mean = float(live_pop[settled].mean())
    settled_rmse = 100.0 * rmse / max(1.0, settled_mean)
    full_rmse = 100.0 * float(np.sqrt(np.mean((curve - live_pop) ** 2))) / max(1.0, live_pop.mean())
    final_drift = 100.0 * abs(curve[-1] - live_pop[-1]) / max(1.0, live_pop[-1])
    transient_min = int(live_pop[times < WARMUP].min())

    print(f"measured carrying capacity K_eq ~= {keq:.1f}")
    print(f"fitted params: B0={params['B0']:.4f}  D0={params['D0']:.4f}  "
          f"K={params['K']:.1f}")
    print(f"settled-regime RMSE (t>={WARMUP:.0f}): {settled_rmse:.1f}%")
    print(f"final-population drift:            {final_drift:.1f}%")
    print(f"full-curve RMSE (incl. transient): {full_rmse:.1f}%  "
          f"[live transient dips to {transient_min} — a spatial-clustering effect the "
          f"mean-field model intentionally abstracts away]")

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(times, live_pop, label="live agent sim", lw=2)
    ax.plot(times, curve, "--", label="fitted cohort model", lw=2)
    ax.axvline(WARMUP, color="gray", ls=":", lw=1, label="warmup / evaluation start")
    ax.set_xlabel("time (ticks)")
    ax.set_ylabel("population")
    ax.set_title("Idle cohort model vs live sim (DESIGN §6/§11.2)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(_util.out("calibrate_idle.png"), dpi=110)

    ok = final_drift <= DRIFT_TOLERANCE and settled_rmse <= RMSE_TOLERANCE
    print(f"[{'PASS' if ok else 'FAIL'}] calibrate_idle "
          f"(drift {final_drift:.1f}%<={DRIFT_TOLERANCE:.0f}%, "
          f"settled RMSE {settled_rmse:.1f}%<={RMSE_TOLERANCE:.0f}%) "
          f"-> out/calibrate_idle.png")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
