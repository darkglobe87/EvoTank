# EvoTank — Progress Audit & Development Plan for Remaining Phases

## Context

EvoTank is a slow-burn hybrid **active/idle** evolution auto-battler for Android:
a 2.5D tank of organisms whose bodies are built from data-driven trait modules,
watched live when the app is open and advanced by closed-form cohort math while
it is closed. Three phases are complete (design → headless de-risk prototype →
rendered vertical slice). This document audits what actually exists in the repo
today and lays out the remaining phases to get from "one organism swims in a
box" to a shipped mobile game.

The audit is based on reading every file in `docs/`, `prototype/`, and `game/`
at commit `577ef95` (both branches are identical at this commit).

---

## Part 1 — Where we are

### Completed

| Phase | Deliverable | State |
|---|---|---|
| 0. Design | `docs/DESIGN.md` (§1–§12) | ✅ Complete blueprint: dual live/idle representation, energy economy, environment grid, data-driven genetics, cohort idle math, milestones/rivals, extinction/rescue |
| 1. De-risk | `prototype/` — 10 Python modules, 4 experiment harnesses, 13 pytest cases, `FINDINGS.md` | ✅ Validated. Slow-burn pacing confirmed (plateau ~68–80), idle≈live within band (RMSE 14.1 %, final drift 8.6 %), niche partitioning confirmed, extinction FSM covered. Found and fixed 4 real bugs + 1 balance trap |
| 2. Vertical slice | `game/` — Godot 4 / GDScript, 11 sim scripts + 4 view scripts, 27-assertion headless test runner | ✅ Sim ported verbatim from Python (genetics, env grid, metabolism, utility-AI brain, tick loop, extinction FSM), 2.5D rendering, trait-driven visual attachment + stat modifiers, debug readout |

The port is genuinely faithful — `game/test/test_runner.gd` asserts GDScript
phenotype values against the Python prototype's ground-truth numbers
(`baseDrain=0.15`, `maxSpeed` 4.0→5.0 with `dorsal_fin`, `traitDrain=0.05`), and
regression-tests FINDINGS bug #1 (trait/scalar compile order) explicitly. The
tuned constants in `game/sim/Config.gd` match `prototype/evotank_sim/config.py`
line for line.

### Gaps found by inspection

**Structural — the game has no player and no memory**

1. **No persistence at all.** No `user://` save, no `FileAccess` write anywhere
   in `game/`. Close the app and the tank is gone. Everything idle depends on
   this.
2. **Idle/cohort math is not in the engine.** `prototype/evotank_sim/cohort.py`
   (205 lines: `deflate`, `CohortModel`, `inflate`) has **no GDScript
   counterpart**. `game/sim/Config.gd` deliberately omits the `IDLE` constants.
   The hybrid active/idle premise — the single most distinctive thing about the
   product — exists only in throwaway Python.
3. **No app-lifecycle hooks.** No `NOTIFICATION_APPLICATION_PAUSED` /
   `_RESUMED` handling in `game/view/Main.gd`, so there is no pause/resume
   boundary to hang Deflate/Inflate on.
4. **Evo Points do not exist.** DESIGN §8's accrual formula is implemented
   nowhere — not in the prototype, not in the game. `evoCost` is parsed off every
   trait JSON (`TraitDefinition.evo_cost`) and never read by anything.
5. **No gene editor, therefore no player agency.** Structural genes are by design
   changed *only* by the player (DESIGN §5.2), and there is no way to change
   them. `TraitDefinition.prerequisites` and `.incompatible_with` are parsed and
   never used. Today the build is a watch-only screensaver.
6. **No milestones, rivals, or combat (§7).** `LiveSim.tick()` has the literal
   comment `(5 combat: none pre-rivals)`. `hp`, `armor`, `attackPower` are
   compiled into every phenotype and nothing ever reads them;
   `OrganismAgent.death_cause()` can return `"predation"` but `hp` never drops.
   `cohort.py`'s rate model has no predation term either.
7. **Last-chance revive has no UI.** `ExtinctionController` FSM is complete and
   tested; nothing surfaces `LAST_CHANCE` to the player.

**Ecology / balance — a known risk was deferred, not fixed**

8. **`FINDINGS.md`'s headline recommendation is unimplemented.** "Couple food
   spawning to comfort/favorable zones — food blooms where organisms want to
   live." `EnvironmentGrid.regen_food()` (both Python and GDScript) is still
   *uniform* logistic regrowth over every cell. The spatial-clustering
   local-depletion collapse was worked around by pinning `STRESS_K` to 0.6 with
   a "do not raise this" comment. The vertical slice runs **one** organism, so
   the workaround has never been stressed. This will resurface the moment
   population goes to 50–150.
9. **Founder transient dip unsmoothed.** FINDINGS notes a synchronized founder
   cohort causes an early dip to ~5–8 organisms before recovery. Mitigation
   (founder energy/age jitter, staggered maturity) not applied.

**Engineering — nothing is verifiable automatically**

10. **No CI.** There is no `.github/` directory. Both suites are manual-only.
11. **Neither suite runs in this container**: no `numpy`/`pytest` installed, no
    Godot binary. For a project whose central claim is "idle ≈ live stays
    calibrated across balance changes," an un-runnable calibration gate is the
    highest-leverage thing to fix.

**Performance — untested beyond N=1**

12. `OrganismAgent.step_movement()` scans a `(2·reach+1)²` = **81-cell** block
    per agent per tick for the forage vector, plus 5 `comfort()` calls each doing
    3 bilinear samples. At the design's 150 agents × 10 Hz that is ~120 k cell
    reads/s and ~2 250 comfort evaluations/s in GDScript, on a phone. Never
    measured.

13. **No Android export.** No export preset (deliberately git-ignored), never
    built or run on a device.

---

## Part 2 — Remaining phases

Ordering principle: **make it verifiable → make it persist → make it idle →
make it a game → make it a mobile product.** Each phase ends with a runnable
gate, mirroring the discipline that made phases 1–2 work.

---

### Phase 3 — Verification & persistence foundation

*Small, unblocking. Nothing after this is trustworthy without it.*

**3.1 CI** — add `.github/workflows/ci.yml` with two jobs:
- `prototype`: `pip install -r prototype/requirements.txt`, `python -m pytest`
  from `prototype/`, plus the four experiment harnesses (each already prints
  `PASS`/`FAIL` and should exit non-zero on failure — check
  `prototype/experiments/*.py` and add explicit `sys.exit(1)` where missing).
- `godot`: download the Godot 4 **Standard** headless binary, run the one-time
  class registration pass (`godot --headless --editor --quit-after 2`, per
  `game/README.md`), then
  `godot --headless --path game --script res://test/test_runner.gd`.
  `test_runner.gd` already `quit(1)`s on failure, so it gates correctly as-is.

**3.2 Save/load** — new `game/sim/SaveGame.gd`:
- JSON at `user://evotank.save` with a `schema_version` int (migrations will be
  needed the moment balance changes ship).
- Persists: RNG seed **and** stream state, every organism's genome/energy/age/
  position, the `EnvironmentGrid.food` `PackedFloat32Array`, event-log tail,
  Evo Points, `pauseTimestamp` (`Time.get_unix_time_from_system()`), and the
  `ExtinctionController` state.
- Atomic write (temp file + rename) so a kill mid-save can't corrupt the tank.
- Round-trip test in `test_runner.gd`: save → load → tick 100 → assert identical
  population and total food versus an unsaved reference sim.

**3.3 Lifecycle wiring** — in `game/view/Main.gd`, handle
`NOTIFICATION_APPLICATION_PAUSED` / `NOTIFICATION_APPLICATION_RESUMED` (Android)
and `NOTIFICATION_WM_CLOSE_REQUEST` (desktop) → save on pause, load on resume.
Leave the idle advance as a no-op stub here; Phase 4 fills it in.

**Gate:** CI green on both jobs; save round-trip test passes; app closed and
reopened resumes the same tank.

---

### Phase 4 — Idle / cohort math in the engine

*Delivers the product's actual premise.*

**4.1 Port `cohort.py` → `game/sim/CohortModel.gd`** (+ `Cohort` as a small
`RefCounted`). Port must preserve all three FINDINGS fixes verbatim — they are
the whole reason the model works:
- semi-analytic exponential update `N *= exp(g*h)` (never Euler),
- sub-step cap `H_MAX = 25.0` via `_nsub()`,
- birth-fraction age dilution `meanAge = (1-β)*(meanAge+h)`.
Replace numpy with plain loops/`PackedFloat32Array`. Add the `IDLE` block
(`B0=0.020, D0=0.0016, S=0.010, K=65.0, substeps=48`) to `SimConfig` — note
`FINDINGS.md` also quotes fitted `B0≈0.019, D0≈0.0008, K≈100` from one
calibration run; pick one source of truth and say which in a comment.

**4.2 Deflate/Inflate** — `deflate()` buckets by the existing
`Genome.signature()` (already ported for exactly this purpose);
`inflate()` resamples discrete `OrganismAgent`s around cohort means and
redistributes food over the grid.

**4.3 Resume experience** — `EventLog.digest()` ("+47 births, −31 deaths, food
−18 %"), a "while you were away" panel, Evo Point accrual over the idle window
using the *same* formula as live (Phase 5), and an **extinction check
immediately after `inflate()`** (DESIGN §8: a species can die while away).

**4.4 Real-clock hardening** (not in the prototype, mandatory on mobile):
clamp `elapsed` to a maximum idle window (e.g. 48 h) so a 6-month absence
doesn't produce a nonsense tank; clamp negative `elapsed` (clock rollback /
timezone change) to 0.

**4.5 Cross-implementation parity test** — export golden vectors from the Python
model (`test/golden/idle_vectors.json`: cohort fixtures + expected `N`, food
stock, births/deaths at several `elapsed` values) and assert the GDScript port
matches within ~1e-4 in `test_runner.gd`. This is the cheap way to keep the two
implementations honest without porting numpy/scipy fitting into Godot.

**Gate:** parity test passes; pausing for a simulated 8 h and resuming lands the
tank in the same band the live sim would reach, with a coherent digest.

---

### Phase 5 — Ecology fix & full population

*Do this **before** rivals — the balance trap is a population-scale phenomenon.*

**5.1 Comfort-coupled food spawning** (FINDINGS' durable recommendation).
Change `regen_food()` in **the Python prototype first** to weight per-cell
regen by a zone-favourability field, re-run `pacing_sanity.py` and
`calibrate_idle.py`, re-fit `B0/D0/S/K`, update `FINDINGS.md` and
`docs/DESIGN.md §4.3`, *then* port the new `regen_food()` and constants to
`game/sim/EnvironmentGrid.gd` + `Config.gd`. With the conflict removed at the
source, re-test whether `STRESS_K` can rise above 0.6 and become a meaningful
selective pressure again.

**5.2 Founder jitter** — seed 20–30 founders with randomized starting
energy/age (and optionally staggered `maturity`) in `LiveSim.seed_species()` to
smooth the early transient dip.

**5.3 Scale to 50–150 agents + perf pass.** Profile first, then optimize the two
known hot spots in `OrganismAgent.step_movement()`:
- replace the 81-cell forage scan with a coarse "richest cell" summary refreshed
  every few ticks, or a per-cell food max maintained incrementally by
  `EnvironmentGrid`;
- cache `comfort()` per (grid cell × phenotype bucket) — organisms of the same
  cohort share optima, which is exactly what `Genome.signature()` already
  buckets.
Target: 150 agents at 10 Hz within a mid-tier phone's frame budget.

**5.4 Population regression test** in `test_runner.gd`: run N seeds for M ticks
headless, assert the plateau lands in the 50–150 band and never collapses —
the GDScript equivalent of `pacing_sanity.py`, and the guard that stops the
collapse from silently returning.

**Gate:** stable plateau across ≥5 seeds in the Godot build; no seed-dependent
collapse; perf budget met.

---

### Phase 6 — Player agency: Evo Points + gene editor

*This is the phase that turns the simulation into a game.*

**6.1 `game/meta/EvoPoints.gd`** — DESIGN §8:
`evoPoints += dt * RATE * healthFactor`, `healthFactor = f(population,
avgEnergy, generationCount)`. Must be called from **both** the live tick and
the idle digest so watching and idling reward identically. Add the same formula
to the Python prototype so it can be pacing-tuned there (how many hours to
afford a 120-point `dorsal_fin`?).

**6.2 Gene editor UI** — `game/ui/GeneEditor.tscn`. Lists the catalog
(`Catalog.catalog.ids()`), shows each trait's `evoCost`, `metabolicCost`, stat
and tolerance modifiers, enforces `prerequisites` / `incompatibleWith` (both
already parsed onto `TraitDefinition`, currently dead fields), spends Evo
Points, and writes the resulting trait set to the **species blueprint**.

**Decided:** an edit applies to **newborns only**. Living organisms keep the
genome they were born with; the blueprint's `trait_ids` are copied into each
offspring at reproduction, so a player edit spreads as a visible generational
wave. This preserves DESIGN §5.2's structural-vs-continuous split and stops the
editor from being an instant rescue button for a dying tank.

Implementation seam: `LiveSim` gains a `blueprint: Genome` field; the child
genome built in `LiveSim.tick()` (line 87) takes `trait_ids` from the blueprint
and `scalars` from the parent's mutated genes. Everything downstream is
unchanged — the new trait set still flows through the existing
`PhenotypeCompiler.compile_genome()`, the single choke point, so no other system
needs to know an edit happened. Cohort bucketing (`Genome.signature()`) already
keys on `trait_ids`, so an edit naturally splits the population into old and new
cohorts for the idle model too. Blueprint must be persisted by `SaveGame` (Phase
3.2).

**6.3 Last-chance revive UI** — wire `ExtinctionController.LAST_CHANCE` to a
modal that calls the existing `apply_revive()` and spawns a clone-plus-mutation
of the survivor. Game-over screen finalizes the Evo Point total.

**Gate:** a player can earn points, add a trait, and see both the mesh appear
and the stat change in the same run; extinction and revive are playable.

---

### Phase 7 — Milestones, rivals & combat (DESIGN §7)

- **`game/meta/Milestones.gd`** — data-defined thresholds (`survivalTime > T`,
  `peakPopulation > P`) evaluated in tick step 6, kept in a JSON asset alongside
  the traits so tuning stays data-driven.
- **`RivalGenerator`** — builds rival genomes through the *same* `Genome` +
  `TraitCatalog` system, optionally counter-seeded against the player's build
  (armored+slow player → fast harassers).
- **Combat resolution** in `LiveSim.tick()` step 5:
  `damage = attackerPower − defenderArmor` floored at 0, predator gains energy
  from kills. Makes `hp`/`armor`/`attackPower` live and `death_cause()`'s
  `"predation"` branch reachable.
- **Predation in the idle model** — add the Lotka–Volterra `predation_i =
  p·N_predator` term to `CohortModel._rates` (**and to `cohort.py`**, which
  never had it) so combat behaves consistently watched or idle. Re-run the idle
  calibration afterwards; multi-cohort predation is exactly the regime where the
  mean-field model is most likely to drift.

**Gate:** a rival species spawns at a milestone, competes for the same food
field, and the idle model reproduces predator/prey outcomes within the same
tolerance band as the single-species gate.

---

### Phase 8 — Mobile product

- Android export preset + build (Godot 4 Standard, no .NET — see
  `game/README.md`'s toolchain constraint); first on-device run.
- Touch UX: pinch-zoom / pan camera, tap-to-inspect an organism, mobile-sized
  event log and gene editor replacing `DebugReadout.gd`.
- Battery/thermal: throttle or suspend rendering when backgrounded, keep the sim
  at 10 Hz, verify `NOTIFICATION_APPLICATION_PAUSED` fires the Phase 3 save
  reliably on real Android (including force-kill).
- On-device perf measurement at full population; APK size and adaptive icon.

**Gate:** installable APK, runs at target framerate on a mid-tier device,
survives background/kill/resume with the tank intact.

---

### Phase 9 — Content, art & release

**Decided: full ship** — this phase carries through to a store release.

**9.1 Content & art**
- Real meshes replacing `OrganismView._placeholder_mesh_for()` — the
  `visual.mesh` path is already in every trait JSON, so this is asset work, not
  code work.
- Expand the trait catalog well beyond the seed 7 (adding a trait is a data
  file, by design — the payoff of the §5.1 architecture).
- Water shader / tank presentation, audio, onboarding, gene-editor art pass.

**9.2 Monetization**
- Rewarded-ad revive wired to `ExtinctionController.apply_revive()` — the FSM
  was written assuming this path, so the hook already exists.
- Premium currency: instant revive, and optionally the paid-retrofit variant of
  a gene edit (deferred in 6.2 — revisit here now that blueprint-only edits are
  shipping and their pacing is known).
- Ad SDK on Godot 4 Android means a third-party plugin; budget real time for it
  and keep it behind an interface so the sim never depends on it.
- Tune Evo Point accrual (6.1) against real IAP pricing before launch.

**9.3 Release engineering**
- Save-schema migration path (`schema_version` from 3.2 earns its keep here).
- Balance telemetry: population plateau, extinction rate, time-to-first-trait —
  the live counterpart to `pacing_sanity.py`.
- Play Store listing, privacy policy (ads + analytics), staged rollout.

---

## Critical files

| Area | Files |
|---|---|
| Idle port target | `prototype/evotank_sim/cohort.py` → new `game/sim/CohortModel.gd` |
| Constants (both must stay in sync) | `prototype/evotank_sim/config.py`, `game/sim/Config.gd` |
| Ecology change | `EnvironmentGrid.regen_food()` in `prototype/evotank_sim/environment.py` **and** `game/sim/EnvironmentGrid.gd` |
| Tick loop / combat hook | `game/sim/LiveSim.gd:56` (`tick`), step 5 comment at line 81 |
| Perf hot spot | `game/sim/OrganismAgent.gd:33` (`step_movement`) |
| Lifecycle + save wiring | `game/view/Main.gd` |
| Reuse, don't rewrite | `PhenotypeCompiler.compile_genome()` (the one choke point for gene→stat), `Genome.signature()` (already built for cohort bucketing), `ExtinctionController` (complete FSM, just needs UI), `EventLog` (needs `digest()` added) |
| Test gates | `game/test/test_runner.gd`, `prototype/tests/`, `prototype/experiments/` |

---

## Verification

Every phase is gated by something runnable, not by inspection:

```bash
# Python prototype (balance / calibration authority)
cd prototype && pip install -r requirements.txt
python -m pytest
python experiments/pacing_sanity.py        # slow-burn plateau
python experiments/calibrate_idle.py       # idle-vs-live, the critical gate
python experiments/niche_partitioning.py
python experiments/extinction_fsm.py

# Godot logic suite (no GPU/window/Android needed)
godot --headless --editor --quit-after 2   # once, after adding any class_name
godot --headless --path game --script res://test/test_runner.gd
# currently: 27 passed, 0 failed

# Visual / device
# Open game/view/Main.tscn in the editor, F5 — per game/README.md's checklist
```

After Phase 3, both suites run in CI on every push, which is the point: the
idle-vs-live calibration is a **regression gate that must be re-run after every
balance change**, and today nothing enforces that.

Caveat on this audit: it was produced in an environment with neither Godot nor
`numpy`/`pytest` available, so **no suite was executed** — Part 1's state is
from reading the code, not from a run. The `27 passed` figure above is quoted
from `game/README.md`, not re-verified. Phase 3.1 removes that blind spot
permanently.

---

## Decisions taken

| Question | Decision |
|---|---|
| Phase order | As listed: **Phase 3 (CI + persistence) starts next**, then idle, ecology/population, gene editor, rivals, Android, release |
| Gene-edit semantics | **Newborns only** — edits update the species blueprint and propagate by reproduction (see 6.2) |
| Roadmap scope | **Full ship** — includes monetization and Play Store release (see 9.2/9.3) |

## Immediate next step

Phase 3.1 + 3.2 + 3.3 as one unit of work: CI workflow, `SaveGame.gd` with an
atomic versioned save (including the species blueprint), lifecycle hooks in
`Main.gd`, and a save round-trip assertion added to `test_runner.gd`.
