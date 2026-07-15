"""DESIGN §11.1 — metabolism / pacing sanity.

Confirms two things with numbers:
  - a heavily built creature drains more energy than a fragile scavenger
    (the "armored creature needs significantly more food" design goal), and
  - time-to-first-reproduction lands in a *slow burn* band, not instantly.
"""

import _util
import matplotlib.pyplot as plt

from evotank_sim import config
from evotank_sim.genetics import compile_genome
from evotank_sim.metabolism import metabolic_drain

# Forage success fraction: what share of max intake an organism actually gets
# once spatial foraging inefficiency is accounted for. Conservative estimate.
FORAGE_PHI = 0.6
SLOW_MIN_TICKS = 30.0     # first repro should take at least this long (slow burn)
SLOW_MAX_TICKS = 400.0    # ...but be achievable within a session's worth of ticks


def profile(name, genome, cat):
    ph = compile_genome(genome, cat)
    cruise = ph["maxSpeed"] * 0.4
    drain = metabolic_drain(ph, cruise, stress=1.0)
    intake = ph["maxIntake"] * config.FOOD_ENERGY * FORAGE_PHI
    net = intake - drain
    ttr = (ph["reproThreshold"] - config.STARTING_ENERGY) / net if net > 0 else float("inf")
    return dict(name=name, drain=drain, intake=intake, net=net, ttr=ttr,
                repro=ph["reproThreshold"])


def main():
    cat = _util.catalog()
    scavenger = _util.species("scavenger")                       # small, no traits
    tank = _util.species("tank", traits=["armor_plate", "jaw"],  # heavy build
                          scalars={"size": 1.6})
    filt = _util.species("filter", traits=["filter_feeder", "eyespot"])

    rows = [profile("Fragile scavenger", scavenger, cat),
            profile("Armored predator (tank)", tank, cat),
            profile("Filter feeder", filt, cat)]

    print("\n=== Pacing / metabolism sanity (DESIGN §11.1) ===")
    print(f"{'phenotype':<26}{'drain/t':>9}{'intake/t':>10}{'net/t':>8}{'ttr(ticks)':>12}")
    for r in rows:
        ttr = f"{r['ttr']:.0f}" if r["ttr"] != float("inf") else "never"
        print(f"{r['name']:<26}{r['drain']:>9.3f}{r['intake']:>10.3f}"
              f"{r['net']:>8.3f}{ttr:>12}")

    scav, tankr = rows[0], rows[1]
    heavier_costs_more = tankr["drain"] > scav["drain"] * 1.3
    slow_burn = all(SLOW_MIN_TICKS <= r["ttr"] <= SLOW_MAX_TICKS
                    for r in rows if r["net"] > 0)

    # Plot the drain/intake/net comparison.
    fig, ax = plt.subplots(figsize=(7, 4))
    names = [r["name"] for r in rows]
    x = range(len(rows))
    ax.bar([i - 0.25 for i in x], [r["drain"] for r in rows], 0.25, label="drain/t")
    ax.bar([i for i in x], [r["intake"] for r in rows], 0.25, label="intake/t")
    ax.bar([i + 0.25 for i in x], [r["net"] for r in rows], 0.25, label="net/t")
    ax.set_xticks(list(x))
    ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=8)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_title("Energy economy by build (DESIGN §3)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(_util.out("pacing_sanity.png"), dpi=110)

    ok = heavier_costs_more and slow_burn
    print(f"\nheavier build costs more: {heavier_costs_more}")
    print(f"time-to-first-repro in slow-burn band [{SLOW_MIN_TICKS:.0f},"
          f"{SLOW_MAX_TICKS:.0f}]: {slow_burn}")
    print(f"[{'PASS' if ok else 'FAIL'}] pacing_sanity  -> out/pacing_sanity.png")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
