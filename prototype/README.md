# EvoTank Prototype (headless simulation, de-risk phase)

Throwaway Python validation of the core simulation in [`../docs/DESIGN.md`](../docs/DESIGN.md).
**Not the shipping codebase** — it exists to answer two numeric questions before any
engine is chosen:

1. Does the metabolism/reproduction tuning produce a *slow burn*, not boom/bust?
2. Does the cohort **idle** model track the live agent sim?

Module seams mirror DESIGN §10 so validated logic maps cleanly into the real engine later.

## Run it

```bash
cd prototype
pip install -r requirements.txt

python experiments/pacing_sanity.py        # DESIGN §11.1 — metabolism / slow-burn
python experiments/calibrate_idle.py       # DESIGN §11.2 — idle-vs-live (critical gate)
python experiments/niche_partitioning.py   # DESIGN §11.3 — trait-driven navigation
python experiments/extinction_fsm.py       # DESIGN §11.4 — extinction / rescue FSM

python -m pytest                           # unit tests (genetics, cohort, FSM)
```

Each experiment prints a `PASS`/`FAIL` line against its threshold and writes a plot to
`out/` (git-ignored). Results and tuned constants are in [`FINDINGS.md`](./FINDINGS.md).

## Layout

```
evotank_sim/       core sim package
  config.py        all tunable constants (single source of truth)
  genetics.py      TraitCatalog, Genome, Phenotype, compile_genome, mutate   (§5)
  metabolism.py    metabolic_drain                                            (§3)
  environment.py   EnvironmentGrid, gradients, comfort, food                 (§4)
  organism.py      Organism + utility-AI brain                               (§2.2)
  live_sim.py      LiveSimulation.tick — fixed-timestep agent loop           (§2)
  cohort.py        deflate/inflate, CohortModel idle integrator              (§6)
  extinction.py    ExtinctionController FSM                                  (§8)
  events.py        event log + idle digest                                   (§2.7/§6.4)
data/traits/*.json seed TraitDefinition assets                               (§5.1)
experiments/       the four DESIGN §11 validation harnesses
tests/             pytest unit tests
```
