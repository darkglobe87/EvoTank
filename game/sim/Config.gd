class_name SimConfig
extends RefCounted
## Tunable constants for the EvoTank sim (single source of truth).
##
## Ported verbatim from prototype/evotank_sim/config.py — these values are
## validated (see prototype/FINDINGS.md), not arbitrary. Do not change without
## re-running the prototype's calibration experiments.
## Section references point at docs/DESIGN.md. IDLE/cohort constants are
## intentionally omitted — cohort.py is out of scope for the vertical slice.

# --- Determinism / time ------------------------------------------------------
const SEED: int = 12345
const TICK_DT: float = 1.0  # time units advanced per live tick (DESIGN §2)

# --- Tank & environment grid (DESIGN §4) -------------------------------------
const TANK_W: float = 320.0
const TANK_H: float = 160.0
const GRID_W: int = 32
const GRID_H: int = 16
const FOOD_CAP_PER_CELL: float = 5.0  # max standing food per grid cell
const FOOD_REGEN_RATE: float = 0.05  # food units regenerated per cell per time unit
const FOOD_ENERGY: float = 1.5  # energy gained per food unit eaten
## Metabolic stress coefficient: stress = 1 + K*(1-comfort). Kept low (0.6) so a
## starving organism can forage across the whole tank instead of dying inside its
## comfort zone — high stress caused seed-dependent local-depletion collapse
## (see prototype/FINDINGS.md). Do not raise this.
const STRESS_K: float = 0.6

# --- Metabolism (DESIGN §3) ---------------------------------------------------
const BODY_BASE: float = 0.15  # base resting drain for size 1.0
const SIZE_EXP: float = 0.75  # Kleiber-style allometric exponent
const MOVE_COST: float = 0.01  # extra drain per unit speed

# --- Base body plan phenotype (before traits/scalars) -------------------------
## Keys are the flat Phenotype fields the sim reads in its hot loop (DESIGN §5.3).
const BASE_PLAN: Dictionary = {
	"maxSpeed": 4.0, "turnRate": 1.0, "size": 1.0, "hp": 10.0, "armor": 0.0,
	"attackPower": 1.0, "senseRadius": 40.0,
	"tempOptimum": 0.5, "tempRange": 0.28,
	"lightOptimum": 0.5, "lightRange": 0.28,
	"pressureOptimum": 0.5, "pressureRange": 0.38,
	"maxIntake": 0.6,  # food units eaten per time unit when on food
	"reproThreshold": 60.0, "reproCost": 35.0, "maturity": 20.0, "lifespan": 600.0,
}

# --- Reproduction / mutation (DESIGN §5.4) ------------------------------------
const STARTING_ENERGY: float = 30.0
const REPRO_COOLDOWN: float = 25.0
const MUT_SIGMA: float = 0.03  # gaussian relative drift on continuous genes
const POP_HARD_CAP: int = 250  # safety ceiling for the live sim

## Continuous-gene clamp bounds after mutation (DESIGN §5.2 scalars).
## Value is [min, max].
const GENE_BOUNDS: Dictionary = {
	"size": [0.4, 3.0],
	"speedBias": [0.5, 2.0],
	"metabolicEfficiency": [0.6, 1.5],
	"tempOptimum": [0.0, 1.0],
	"lightOptimum": [0.0, 1.0],
	"pressureOptimum": [0.0, 1.0],
}

## Default continuous genes for a freshly designed organism.
const DEFAULT_SCALARS: Dictionary = {
	"size": 1.0, "speedBias": 1.0, "metabolicEfficiency": 1.0,
	"tempOptimum": 0.5, "lightOptimum": 0.5, "pressureOptimum": 0.5,
}

# --- View-only constants (new, not in the Python prototype) ------------------
## World units per sim-unit for rendering (sim space is TANK_W x TANK_H).
const WORLD_SCALE: float = 0.05
## Fixed sim steps per second the view's accumulator runs (DESIGN §2: 10 Hz).
const SIM_SPEED: float = 10.0
