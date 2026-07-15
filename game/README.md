# EvoTank — Godot 4 Vertical Slice

The first rendered milestone: a Godot 4 (GDScript) port of the validated
headless Python prototype (`../prototype/`), proving the core simulation loop
works in a real, watchable engine. Full design context: `../docs/DESIGN.md`
(especially §12) and `../prototype/FINDINGS.md`.

**Engine: Godot 4.7+. Language: GDScript** — chosen specifically for a light,
no-activation toolchain (see `../docs/DESIGN.md` §12 / this phase's plan for
the reasoning). Do not add C#/.NET dependencies without revisiting that decision.

## Setup

1. Download Godot 4 (Standard build, **not** the .NET/Mono build) from
   [godotengine.org/download](https://godotengine.org/download) — a single
   ~100MB binary, no install, no account, no activation.
2. Open `game/project.godot` in the Godot editor, or run headlessly (see below).

## What's here vs. what's deferred

This is a **vertical slice**, not the full game — per the approved plan, it
proves the pipeline works end-to-end with intentionally minimal scope:

- ✅ Ported: genetics/traits (`sim/Genome.gd`, `TraitCatalog.gd`,
  `PhenotypeCompiler.gd`), environment grid (`sim/EnvironmentGrid.gd`),
  metabolism (`sim/Metabolism.gd`), the utility-AI organism brain
  (`sim/OrganismAgent.gd`), the full tick loop (`sim/LiveSim.gd`), and the
  extinction FSM (`sim/ExtinctionController.gd`) — all ported **verbatim**
  from `prototype/evotank_sim/`, same formulas, same tuned constants.
- ✅ Rendering: one organism (founder carries the `dorsal_fin` trait) navigates
  a 2.5D tank via placeholder capsule meshes, feeds, and reproduces or dies —
  see `view/Main.gd`, `view/OrganismView.gd`.
- ❌ Not yet: idle/cohort math (`cohort.py` was deliberately not ported this
  phase), the gene editor UI, monetization, milestones/rivals, the last-chance
  revive UI (the FSM states exist, just no UI), final art, Android export.

## Running the headless test suite (logic verification)

No GPU, window, or Android needed — this is the cheapest verification loop,
same role as the prototype's `pytest` suite:

```bash
cd game
godot --headless --path . --script res://test/test_runner.gd
```

Expect `27 passed, 0 failed`. This asserts the ported GDScript produces numbers
traceable to the Python prototype's validated outputs — e.g. the exact
`baseDrain`/`maxSpeed`/`traitDrain` values a `protoblob` vs.
`protoblob+dorsal_fin` compile to, matched against the prototype's own
`compile_genome()` output. It also regression-tests FINDINGS.md bug #1 (the
compile-order bug where traits could get silently clobbered by scalars).

**First-time note:** if you add or rename any script with a `class_name`, the
editor needs one scan pass to register it before `--script` runs can see it:
`godot --headless --editor --quit-after 2`. Not needed for normal edits to
existing files.

## Visual verification (do this — headless can't)

Open `game/Main.tscn` in the Godot editor and press Play (or F5). You should
see, per the plan's exit criteria:

1. One organism swimming in the tank, visibly steering toward food/its comfort
   zone (not random drift) — driven by the same utility-AI blend as the
   prototype (forage vector + comfort gradient + hunger-weighted wander).
2. A small fin-shaped attachment on its back (the `dorsal_fin` trait) — and
   the startup console line confirms it's *also* faster:
   `founder maxSpeed=5.00 (baseline 4.0 + dorsal_fin)`.
3. Energy rising when it's over food, draining faster when it strays from its
   comfort band.
4. Over time (the sim runs at `SimConfig.SIM_SPEED` = 10 ticks/sec, so a life
   cycle plays out in tens of seconds, not hours): either a mutated offspring
   is born (a second capsule appears) or the organism dies — both show up in
   the on-screen debug readout's event log.
5. The top-left debug readout continuously showing energy/age/state and recent
   birth/death lines.

If something looks wrong (e.g. the organism doesn't move, or looks stuck),
check the editor's Output/Debugger panel for script errors first — the
headless test suite passing means the *sim* math is right, but only the
editor run exercises the *view* binding end-to-end.

## Android export (later, not required for "slice done")

Not configured yet. Once the desktop slice above looks right, add an Android
export preset from the editor (Project → Export). Requires the Android SDK/
build tools — a separate, later step, deliberately deferred so this phase
doesn't need any of the Unity-style local-build weight that ruled out Unity in
the first place.
