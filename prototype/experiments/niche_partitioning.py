"""DESIGN §11.3 — niche partitioning.

Seed two species with different temperature optima into one tank. If the
trait-driven comfort/stress field works, they should settle at different depths
without any pathfinding — proving §4 navigation and setting up the resource
competition that rivals will later exploit.
"""

import _util
import numpy as np

from evotank_sim import config
from evotank_sim.live_sim import LiveSimulation

DURATION = 500.0
SEP_THRESHOLD = 25.0     # world units of mean-depth separation to count as partitioned


def mean_depth(sim, prefix):
    ys = [o.y for o in sim.organisms if o.genome.lineageId.startswith(prefix)]
    return float(np.mean(ys)) if ys else float("nan")


def main():
    cat = _util.catalog()
    sim = LiveSimulation(cat, seed=config.SEED)
    # Temperature field is warm (1.0) at the surface, cold (0.0) at depth.
    warm = _util.species("WARM", scalars={"tempOptimum": 0.85})   # -> surface
    cold = _util.species("COLD", scalars={"tempOptimum": 0.15})   # -> deep
    sim.seed_species(warm, 10)
    sim.seed_species(cold, 10)

    sim.run(DURATION, record_every=DURATION)   # run, only final state needed

    dy_warm = mean_depth(sim, "WARM")
    dy_cold = mean_depth(sim, "COLD")
    sep = abs(dy_cold - dy_warm)

    print("\n=== Niche partitioning (DESIGN §11.3) ===")
    print(f"WARM-optimum species mean depth y = {dy_warm:.1f} (expect near surface, small y)")
    print(f"COLD-optimum species mean depth y = {dy_cold:.1f} (expect near floor, large y)")
    print(f"separation = {sep:.1f} world units (threshold {SEP_THRESHOLD:.0f})")

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 5))
    for prefix, color, label in (("WARM", "tab:red", "warm-optimum"),
                                 ("COLD", "tab:blue", "cold-optimum")):
        xs = [o.x for o in sim.organisms if o.genome.lineageId.startswith(prefix)]
        ys = [o.y for o in sim.organisms if o.genome.lineageId.startswith(prefix)]
        ax.scatter(xs, ys, s=18, c=color, label=label, alpha=0.7)
    ax.set_xlim(0, config.TANK_W)
    ax.set_ylim(config.TANK_H, 0)   # y=0 at top (surface)
    ax.set_xlabel("x")
    ax.set_ylabel("depth (y)")
    ax.set_title("Niche partitioning by temperature optimum")
    ax.legend()
    fig.tight_layout()
    fig.savefig(_util.out("niche_partitioning.png"), dpi=110)

    # Warm species should sit above (smaller y) the cold species, well separated.
    ok = sep >= SEP_THRESHOLD and dy_warm < dy_cold
    print(f"[{'PASS' if ok else 'FAIL'}] niche_partitioning -> out/niche_partitioning.png")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
