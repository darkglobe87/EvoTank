# EvoTank — Core Simulation Design & Technical Outline

## Context

EvoTank is a greenfield project (the repo is currently empty — no code to reuse or
extend). This document is the **design deliverable itself**: a systems-level blueprint
for the core simulation of a mobile, slow-burn hybrid active/idle evolution auto-battler
for Android. It deliberately stays out of engine/rendering architecture and focuses on
simulation logic, data structures, systems integration, and the idle math.

Two foundational decisions are confirmed by the user and drive everything below:

- **Idle progression = Statistical Cohort Model** (O(1) closed-form, not a fast-forward
  of the live sim). Live sim is agent-based; idle collapses the tank into cohorts.
- **Genetics = Data-Driven Trait Modules** (traits defined in external data, not a
  hardcoded enum). Adding a trait = adding a data asset, no code change.

The rest of this document is the design. Because there is no codebase, there are no files
to modify yet; the final section proposes the initial file/module layout to create when
implementation begins.

---

## 1. Simulation Model Overview (two coupled representations)

The core architectural idea: the tank has **one truth, two representations**, and the
game swaps between them at the app-lifecycle boundary.

| | **Live (app open)** | **Idle (app closed)** |
|---|---|---|
| Representation | Agent-based — every organism is a discrete entity | Population cohorts — organisms grouped by genotype |
| Update | Fixed-timestep tick, per-entity AI/physics | Closed-form equations advanced once on resume |
| Cost | O(N) per tick, N = 50–150 | O(C) once, C = number of cohorts (small) |
| Purpose | Watchable, per-individual event log | Accurate aggregate progression over hours |

**Boundary transforms** (the glue that keeps them consistent):

- `Deflate()` on app-pause: bucket all live entities into cohorts keyed by genotype
  signature; store aggregate stats (count, mean energy, mean age, food stock, env state,
  RNG seed, `pauseTimestamp`).
- `Inflate()` on app-resume: run the idle math for `elapsed = now − pauseTimestamp`,
  producing new cohort counts and a summarized event digest; then **re-spawn discrete
  entities** sampled from the resulting cohort distributions to repopulate the live tank.

This is why the cohort model must be *calibrated to* the live rules (Section 5): the
whole point is that 8 hours idle lands the player roughly where 8 hours of watching would.

---

## 2. The Core Loop (live, per-tick logic)

Fixed timestep. Recommend **simulation tick = 100 ms (10 Hz)** decoupled from render
frame rate; use an accumulator so physics/AI are deterministic and rendering interpolates.
"Game time" is scaled (e.g. 1 real minute = 1 simulated "cycle") so sessions span hours.

Per tick, for the whole tank, in this order:

1. **Environment update**
   - Advance slow global cycles (day/night light, temperature drift, current direction).
   - Spawn flora/organic compounds probabilistically per zone (see §4 spawn rule).

2. **Per-organism sense → decide → act** (agent AI, one pass over all entities)
   - **Sense:** sample the environment grid at the organism's position (light, temp,
     pressure, food density) plus nearby entities (food, mates, predators/rivals).
   - **Decide (utility AI / behavior tree):** score drives — *Forage, Flee, Seek Mate,
     Seek Comfort Zone, Wander* — and pick the highest. Drive weights are modulated by
     the organism's own traits (e.g. eyespots raise sense radius; fins raise flee/chase
     effectiveness; armor lowers flee urgency).
   - **Act:** move toward the target on the 2D plane (speed = trait-derived, drag from
     size/armor), and attempt interactions (eat, attack, mate) when in range.

3. **Metabolism & energy resolution** (see §3)
   - `energy -= metabolicDrain(dt)` for every organism (the "cost of existing + traits").
   - On successful feed: `energy += min(foodValue, maxIntake)`, deduct from food source.
   - Apply environmental stress: if outside the organism's tolerance band for
     temp/pressure/light, add a stress multiplier to drain (§4).

4. **State transitions** (evaluate flags per organism)
   - **Death:** `energy <= 0` → starvation; `age > lifespan` → old age; `hp <= 0` →
     predation/combat. Remove entity, emit `DEATH` event.
   - **Reproduction eligibility:** `energy >= reproThreshold` AND
     `age >= maturity` AND `timeSinceLastBirth >= cooldown` AND local population under
     carrying cap → spawn offspring (§ genetics/mutation), deduct `reproCost` from parent,
     emit `BIRTH` event.

5. **Combat / interaction resolution** (once rivals exist, §7)
   - Resolve attack events: `damage = attackerPower − defenderArmor` (floored ≥ 0);
     predator gains energy from kills.

6. **Population & milestone checks**
   - Recompute `populationCount`, `speciesSurvivalTime`.
   - Fire milestone triggers (introduce rivals, unlock zones — §7).
   - **Extinction hooks:** `count == 1` → pause + "last chance" prompt;
     `count == 0` → Game Over, award Evo Points (§8).

7. **Event log flush** — push queued events to the scrolling UI ring buffer.

8. **Evo Point accrual** — increment based on survival time × population-health factor (§8).

**Loop pseudocode (skeleton):**

```
fun tick(dt):
  environment.update(dt)                     # 1
  for org in entities:                        # 2
      ctx = environment.sampleAt(org.pos) + neighbors(org)
      org.intent = org.brain.decide(ctx, org.dna)
      org.applyMovement(org.intent, dt)
  for org in entities:                        # 3
      org.energy -= metabolicDrain(org.dna, environment.stressAt(org))*dt
      resolveFeeding(org)
  resolveCombat(entities)                     # 5
  for org in entities.snapshot():             # 4
      if org.isDead(): kill(org); log(DEATH)
      elif org.canReproduce(): spawn(offspring(org)); log(BIRTH)
  population.recount()                         # 6
  milestones.evaluate(population, survivalTime)
  extinction.check(population)
  eventLog.flush()                            # 7
  evoPoints.accrue(dt, population.health)     # 8
```

---

## 3. The Economy of Energy (Metabolism)

Single source of truth for "how expensive is this body," computed once per organism and
cached (recomputed only when DNA changes).

```
baseDrain      = BODY_BASE * (size ^ SIZE_EXP)        # allometric: bigger costs more
traitDrain     = Σ trait.metabolicCost  for each attached module
activityDrain  = MOVE_COST * currentSpeed             # moving costs extra
envStress      = stressMultiplier (≥ 1.0, from §4)

metabolicDrain(dt) = (baseDrain + traitDrain + activityDrain) * envStress * dt
```

- `SIZE_EXP ≈ 0.75` (Kleiber-style) so size scales sub-linearly but total upkeep still
  rises — keeps small scavengers viable and heavy tanks hungry, exactly your design goal.
- Every trait module carries its own `metabolicCost`, so "armored creature needs
  significantly more food" is emergent from data, not special-cased.
- **Design lever:** `reproThreshold` and `foodValue` are tuned against typical drain so
  that break-even foraging time is the main pacing knob.

---

## 4. The Environment Grid & Trait-Based Navigation

### 4.1 Representation

A **layered scalar field**, not per-pixel. Overlay a coarse grid on the tank
(e.g. 32×16 cells for a phone). Each cell holds a small struct:

```
Cell { light, temperature, pressure, currentX, currentY, foodDensity }
```

- **Static gradients** (temperature by depth, pressure by depth, light by depth+X) are
  cheap functions of position, baked once: `temperature = f(y)`, `light = g(x, y, timeOfDay)`.
  Store as the grid so AI can sample uniformly, but they're generated, not authored cell-by-cell.
- **Dynamic layer** (`foodDensity`, transient currents) updates over time.
- Sampling uses **bilinear interpolation** between the 4 nearest cell centers so movement
  reads as smooth despite the coarse grid.

### 4.2 How creatures "know where to go" (trait-driven preference)

Each organism carries **tolerance bands** derived from its DNA, e.g.
`tempOptimum, tempRange`, `lightOptimum, lightRange`, `pressureOptimum, pressureRange`.
These come from traits: gills shift `pressureOptimum` deeper, dark-pigment shifts
`lightOptimum` lower, etc.

Comfort at a cell is a product of per-axis Gaussians:

```
comfort(cell, dna) = Π_axis exp( -((cell.axis − dna.optimum_axis)^2) / (2 * dna.range_axis^2) )
```

- `comfort ≈ 1` at the organism's ideal zone, → 0 in hostile zones.
- **Stress multiplier** for metabolism (§3): `stressMultiplier = 1 + K*(1 − comfort)`.
  Being in the wrong zone literally burns energy faster → creatures are *pushed* toward
  their niche by survival pressure, not scripted.
- **Navigation:** the *Seek Comfort Zone* drive does cheap gradient ascent — sample
  `comfort` at a few candidate cells around the organism (or the 4 neighbors) and steer
  toward the highest, blended with the *Forage* target. No pathfinding needed; the field
  gives direction for free. This naturally creates **niche partitioning**: differently
  evolved species drift to different depths/zones, which sets up resource competition
  when rivals arrive.

### 4.3 Food spawning

Per zone per tick: `P(spawn) = baseRate * zoneFertility * (1 − foodDensity/foodCap)`
(logistic — food self-limits, preventing infinite pile-up). Flora spawns anchored;
free organic compounds drift with `currentX/currentY`.

---

## 5. Data Structures — Genetics / DNA (data-driven modules)

### 5.1 Trait definitions (external data — the catalog)

Traits are **assets** (JSON / ScriptableObjects), not code. One definition per trait:

```jsonc
// TraitDefinition (data asset)
{
  "id": "dorsal_fin",
  "displayName": "Dorsal Fin",
  "category": "locomotion",
  "evoCost": 120,                       // Evo Points to add via gene editor
  "metabolicCost": 0.8,                 // feeds into §3
  "statModifiers": {                    // additive/multiplicative deltas
    "speed":       { "op": "add", "value": 0.6 },
    "turnRate":    { "op": "mul", "value": 1.15 }
  },
  "toleranceModifiers": {               // shifts §4 comfort bands
    "pressureOptimum": { "op": "add", "value": 0.0 }
  },
  "visual": {                           // renderer only; sim ignores
    "mesh": "meshes/dorsal_fin",
    "attachPoint": "spine_mid",
    "scaleWithSize": true
  },
  "prerequisites": ["spine"],           // gating in the gene editor
  "incompatibleWith": ["jet_sac"]
}
```

This satisfies your explicit requirement — "translates to both visual modules AND
statistical modifiers" — by giving each trait *both* a `visual` block (consumed by the
render/attachment system) and `statModifiers`/`toleranceModifiers`/`metabolicCost`
(consumed by the sim). The two never diverge because they're the same asset.

### 5.2 The Genome (per-organism instance data)

```
Genome {
  coreBodyId: string                    // base plan
  traitIds:   List<string>              // attached modules (structural genes)
  scalars: {                            // continuous genes — mutate on reproduction
      size, speedBias, metabolicEfficiency,
      tempOptimum, lightOptimum, pressureOptimum, ...
  }
  generation: int
  lineageId:  string                    // for the event log / family tracking
}
```

Key separation, matching your reproduction rules:

- **`traitIds` = structural genes.** Changed *only* by player intervention in the gene
  editor spending Evo Points (major mutation). Never mutate on their own.
- **`scalars` = continuous genes.** Drift by small random deltas on reproduction (minor
  mutation).

### 5.3 Phenotype (computed, cached stat block)

Never read raw genes in the hot loop. Compile the genome → a flat `Phenotype` once on
birth / on edit:

```
Phenotype {
  maxSpeed, turnRate, size, hp, armor, attackPower, senseRadius,
  baseDrain, traitDrain,                // pre-summed for §3
  tempOptimum/Range, lightOptimum/Range, pressureOptimum/Range,
  reproThreshold, maturity, lifespan
}

fun compile(genome, catalog) -> Phenotype:
   p = basePlan(genome.coreBodyId)
   for id in genome.traitIds:
       apply(catalog[id].statModifiers, catalog[id].toleranceModifiers, p)
       p.traitDrain += catalog[id].metabolicCost
   applyScalars(genome.scalars, p)      # size, biases, efficiency
   return p
```

`compile()` is the single choke point where data-driven traits become live numbers —
the sim only ever touches `Phenotype`, keeping the tick cheap.

### 5.4 Reproduction & mutation (offspring genome)

```
fun offspring(parent):
  g = parent.genome.copy()
  g.generation += 1
  for k in g.scalars:                   # minor mutation only
      g.scalars[k] *= 1 + gauss(0, MUT_SIGMA)   # e.g. sigma ≈ 0.03
      g.scalars[k] = clamp(g.scalars[k], geneBounds[k])
  # traitIds copied verbatim — structural change requires player + Evo Points
  return Organism(g, compile(g, catalog), energy=STARTING_ENERGY)
```

---

## 6. Idle Math — Statistical Cohort Model

Goal: on resume after `Δt` (could be 8 h or 200 h), advance the population **once**,
in closed form, landing near where the live agent sim would have — without simulating
ticks. Chosen because pacing is "tens to hundreds of hours"; O(1) is mandatory.

### 6.1 State captured on `Deflate()`

For each **cohort** (organisms sharing a genotype signature):

```
Cohort { genomeSig, N, meanEnergy, meanAge, phenotype }
Global { foodStock, envState, evoPoints, pauseTimestamp, rngSeed }
```

### 6.2 The model — logistic population dynamics with resource coupling

Treat each cohort's count `N` as continuous and integrate a coupled system over `Δt`.
Per cohort:

**Effective per-capita food intake** (resource-limited, shared across cohorts):
```
demand_i   = N_i * intakeRate(phenotype_i)
totalDemand= Σ demand_i
supply     = foodRegenRate * Δt + foodStock
fedFrac    = min(1, supply / totalDemand)          # scarcity → competition
```

**Per-capita net energy rate** (food in − metabolism out):
```
netEnergy_i = fedFrac * intakeRate_i − metabolicDrain_i
```

**Birth & death rates** derived directly from the live rules so they stay calibrated:
```
birthRate_i = B0 * max(0, netEnergy_i) * survivorFactor      # only well-fed cohorts breed
deathRate_i = D0 + starvation(netEnergy_i) + oldAge(meanAge_i) + predation_i
```
- `starvation(x) = S * max(0, −x)` — negative energy budget kills.
- `predation_i` = 0 pre-rivals; once rivals exist it's a Lotka–Volterra term
  `p * N_predator` (§7).

**Carrying capacity** `K` from environment fertility caps growth (logistic):
```
dN_i/dt = N_i * ( birthRate_i * (1 − Ntot/K) − deathRate_i )
```

### 6.3 Integration strategy (accuracy without ticking)

- For a **single cohort with constant rates**, this is the logistic equation with a
  closed-form solution:
  `N(t) = K / (1 + ((K − N0)/N0) * e^(−r t))`, `r = birthRate*(…) − deathRate`.
- For **multiple coupled cohorts** (shared food, predation), rates aren't constant, so
  use a handful of **large fixed sub-steps** (e.g. 12–48 RK4 or even Euler steps across
  the *entire* `Δt`, not per game-tick). This is still O(cohorts × constant) — 200 hours
  costs the same as 8 hours. Sub-stepping recomputes `fedFrac` and `predation` a few times
  so competition dynamics don't run away.

### 6.4 Producing the resume experience

- Round cohort `N` back to integers; distribute leftover fractional births/deaths via
  the seeded RNG so it's deterministic and replayable.
- **Event digest** instead of thousands of individual log lines:
  "While you were away (8h 12m): +47 births, −31 deaths, 2 cohorts reached a new
  comfort zone, food stock −18%." Optionally synthesize a few representative BIRTH/DEATH
  entries for flavor.
- Update `evoPoints += survivalTime(Δt) * healthFactor` using the same accrual formula
  as live (§8) so idle and active reward identically.
- `Inflate()`: sample discrete organisms from each resulting cohort (energy/age drawn
  around cohort means) to rebuild the 50–150 live entities.

### 6.5 Calibration (keeping idle ≈ live)

The constants `B0, D0, S, intakeRate, K` are **derived from the live rules**, then tuned
by running the live sim headless for, say, 1 simulated hour and fitting the cohort model's
`Δt = 1h` output to it. Do this once per major balance change. Small drift is acceptable
and expected — the design goal is "feels consistent," not bit-exact (that's why we didn't
pick deterministic fast-forward).

---

## 7. Milestones, Rivals & Combat

- **Milestone triggers** are data-defined thresholds checked in loop step 6, e.g.
  `speciesSurvivalTime > T` or `peakPopulation > P` → spawn a **procedural rival species**.
- Rival genomes are generated by the **same** `Genome`/trait system (possibly seeded to
  counter the player's build — e.g. if player is armored+slow, spawn fast harassers).
- Rivals occupy the environment grid and compete for the same food field → natural
  resource competition emerges from §4 niche overlap.
- **Predation** couples into both representations: live via combat resolution (§2 step 5),
  idle via the `predation_i` Lotka–Volterra term (§6.2), so it behaves consistently
  whether watched or not.

---

## 8. Evo Points, Extinction & Rescue

- **Evo Point accrual:** `evoPoints += dt * RATE * healthFactor`, where
  `healthFactor = f(population, avgEnergy, generationCount)` — rewards a thriving,
  evolving species, not just a barely-alive one. Same formula in live and idle (§6.4).
- **Extinction hooks** (loop step 6):
  - `population == 1` → set `paused = true`, raise `LastChancePrompt` (revive via premium
    currency / rewarded ad → spawn a second organism cloned+mutated from the survivor).
  - `population == 0` → `GameOver`: finalize Evo Point total, tear down sim, return to menu.
- Both are simple state-machine transitions on the population count, checked every tick
  and immediately after `Inflate()` (a species can go extinct *while away* — handle it on
  resume with a "your species died N hours ago" screen).

---

## 9. Systems Integration Map (how it all wires together)

```
                 ┌───────────────┐
   TraitCatalog ─┤   Genome      ├─ compile() ─► Phenotype ─┐
   (data assets) └───────────────┘                          │ (cached stats)
                                                             ▼
 EnvironmentGrid ──sample()──► Organism.brain.decide() ──► Movement/Actions
        │                                   │                     │
        │ stressAt() ──► Metabolism ◄───────┘                     │
        │                    │                                    ▼
        └────► FoodField ◄── Feeding ──► Energy ──► Repro/Death ──► EventLog
                                                        │
                            Population/Milestones ◄──────┤──► EvoPoints
                                    │                            ▲
                                Rivals/Combat                    │
                                                                 │
  App lifecycle:  Deflate() ─► [Cohort Idle Math] ─► Inflate() ──┘
```

---

## 10. Proposed Initial Module Layout (to create at implementation time)

No files exist yet; when we start coding, scaffold along these seams (engine-agnostic
names — map to Unity/Godot/native as chosen later):

- `sim/` — `SimulationLoop`, `Organism`, `Phenotype`, `Metabolism`, `Reproduction`
- `genetics/` — `Genome`, `TraitDefinition`, `TraitCatalog`, `PhenotypeCompiler`
- `environment/` — `EnvironmentGrid`, `Gradients`, `FoodField`, `ComfortField`
- `ai/` — `UtilityBrain` (drives), `Navigation`
- `idle/` — `Deflate`/`Inflate`, `CohortModel`, `IdleIntegrator`, `EventDigest`
- `meta/` — `EvoPoints`, `Milestones`, `RivalGenerator`, `ExtinctionController`
- `data/traits/*.json` — the trait catalog assets
- `ui/` — `EventLog` ring buffer, `GeneEditor`, `LastChancePrompt`

---

## 11. Verification / How to prove the design works

Since this is design-stage, "verification" = the experiments that validate the model
before/alongside first implementation:

1. **Metabolism/pacing sanity:** spreadsheet or tiny script — plug representative
   phenotypes into §3 and confirm break-even foraging time and repro cadence land in the
   intended "slow burn" range. Tune `SIZE_EXP`, `foodValue`, `reproThreshold`.
2. **Idle-vs-live calibration harness (the critical test):** run the live agent sim
   headless for 1 simulated hour from a known seed; run the §6 cohort model over the same
   `Δt`; compare final population, food stock, cohort mix. Fit `B0/D0/S/K` until drift is
   within an acceptable band (e.g. <10%). Repeat after any balance change.
3. **Niche partitioning check:** seed two species with different tolerance bands; confirm
   §4 comfort/stress pushes them to different zones in the live sim (proves navigation
   works without pathfinding).
4. **Extinction/rescue state machine:** unit-test the count==1 and count==0 transitions,
   including the "went extinct while idle" resume path.

---

## 12. Prototype validation results (de-risk phase — DONE)

A headless Python prototype (`prototype/`) implemented §2–§8 and ran all four §11
experiments. Full write-up: `prototype/FINDINGS.md`. Summary of what the design got
right and what had to change:

- **Slow-burn pacing (§3, §11.1): confirmed.** Heavier builds cost ~2.5× a scavenger and
  take ~3× longer to reproduce; population settles at a stable ~68–80 (in the 50–150
  target band), robust across seeds.
- **Idle ≈ live (§6, §11.2): confirmed within band** — settled-regime RMSE ~14 %,
  final-population drift ~9 %. The mean-field cohort model predicts the long-run
  attractor (its job) but *cannot* reproduce live spatial transients — acceptable per §6.5.
- **Niche partitioning (§4, §11.3): confirmed** — species separate cleanly by depth with
  no pathfinding.
- **Fixes folded back into this design:**
  - Metabolic stress (§4.2) must stay **modest** — a high stress penalty caused a
    seed-dependent *starve-in-your-comfort-zone* collapse while the tank was globally
    full of food. **Recommended design change: spawn food preferentially in favorable
    zones (§4.3) so "food blooms where organisms live,"** removing the conflict at the
    source.
  - Idle integration (§6.3) must use a **stable exponential update with a capped
    sub-step**, not naive Euler, and cohorts must **dilute mean-age by births** or they
    spuriously age to extinction.
  - Trait tolerance modifiers (§5.1) apply **on top of** continuous genes, not before.
