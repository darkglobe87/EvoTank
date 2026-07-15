# EvoTank Prototype — Findings

De-risk phase result. Headless Python validation of the `docs/DESIGN.md` core
simulation. **Bottom line: the core loop is worth building on.** The slow-burn
pacing and the active/idle premise both hold once tuned — but only after fixing
four real bugs and one balance trap the paper design did not anticipate. All four
experiment harnesses and all 13 unit tests pass.

Run it yourself: `pip install -r requirements.txt`, then
`python experiments/<name>.py` and `python -m pytest`.

---

## Verdict against the phase exit criteria

| Criterion | Result |
|---|---|
| Slow-burn confirmed | ✅ population rises to a stable plateau (~68–80) in the game's target 50–150 band; robust across 5 seeds |
| Idle ≈ live (critical gate) | ✅ settled-regime RMSE **14.1 %**, final-population drift **8.6 %** (both within band) |
| Niche partitioning | ✅ warm/cold species separate by **~90** world units, no pathfinding |
| Extinction / rescue FSM | ✅ all transitions incl. the went-extinct-while-idle resume path |

---

## Bugs found & fixed (this is what the prototype was for)

1. **Trait tolerance modifiers were silently clobbered** (`genetics.compile_genome`).
   Scalars were assigned *after* trait modifiers, overwriting them, so e.g. dark
   pigment never actually shifted `lightOptimum`. Fixed by applying continuous genes
   first, then trait modules on top.

2. **Idle integrator was Euler-unstable at large step sizes** (`cohort.step`).
   For long idle intervals `rate*h > 1` drove population negative → clamped to 0 →
   spurious extinction. Replaced with a semi-analytic **exponential** update (`N *=
   exp(g*h)`), which is unconditionally stable and non-negative, plus a sub-step-size
   cap `H_MAX`.

3. **Cohort mean-age grew unbounded** (`cohort.step`). The cohort aged by `h` every
   step with no accounting for age-0 newborns, so a *reproducing* cohort still "aged
   to death" and collapsed over long intervals. Added birth-fraction age dilution:
   `meanAge = (1-β)*(meanAge+h)`.

4. **Calibration gate could pass spuriously.** The first gate checked only final-
   population drift; a boom-bust that ended low "passed" against a live curve that
   also ended low. Now gates on **settled-regime RMSE** (idle math's actual job:
   predicting the long-run attractor) *and* final drift.

## The balance trap the paper design missed

**Spatial-clustering local-depletion collapse.** With the original constants the live
sim was seed-fragile: on some seeds the population crashed to ~2 (near extinction)
even though the tank was globally full of food. Cause: every organism of one species
shares a comfort optimum, so they **pile into the same zone**, deplete food locally,
and — because the metabolic **stress** penalty for leaving the comfort zone was high —
they'd rather **starve in place** than forage across the full tank.

This is a genuine design risk, not a code bug, and it is the single most important
finding for the next phases. Mitigations applied (see tuned constants); the durable
recommendation is below.

---

## Tuned constants (folded into `evotank_sim/config.py`)

| Constant | Was | Now | Why |
|---|---|---|---|
| `STRESS_K` | 1.5 | **0.6** | let a starving organism forage tank-wide instead of dying in its comfort zone |
| `FOOD_REGEN_RATE` | 0.02 | **0.05** | support a target-band carrying capacity (~68–80) |
| initial standing food | 0.5·cap | **0.25·cap** | stop founders gorging and over-breeding into a boom-bust |
| `REPRO_COOLDOWN` | 15 | **25** | slow reproduction, damp overshoot |
| cohort default `K` | — | **65** | matches measured carrying capacity |

Fitted idle-model coefficients (from `calibrate_idle.py`, one calibration run):
`B0 ≈ 0.019`, `D0 ≈ 0.0008`, `K ≈ 100`. Re-fit after any balance change.

---

## Known limitations / open items for later phases

- **Residual early transient dip.** A synchronized founder cohort still causes a brief
  early dip (~5–8) before recovering to the plateau. Robust (no collapse across seeds)
  but worth smoothing with founder energy/age jitter or staggered maturity.
- **Mean-field can't see local crashes.** The cohort model tracks the long-run
  attractor (its job) but not the live transient spatial dip (full-curve RMSE ~67 %).
  If reflecting local crashes *while idle* ever matters, move to **per-zone spatial
  cohorts**.
- **Logistic growth shape imperfect.** Fitted `K` (~100) overshoots measured `K_eq`
  (~79) — the mean-field approach-to-K is shaped slightly differently from live.
  Within tolerance, but a candidate for a better growth term.

## Recommendation to carry into the design

**Couple food spawning to comfort/favorable zones** ("food blooms where organisms
want to live"). This removes the starve-in-comfort-vs-eat-in-discomfort conflict at
the source, is ecologically coherent, and would let metabolic stress be a meaningful
pressure again without risking collapse. Consider it before the vertical-slice phase;
fold the result back into `docs/DESIGN.md §4`.
