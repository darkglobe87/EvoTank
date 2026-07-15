"""Tunable constants for the EvoTank prototype (single source of truth).

All balance numbers live here so the experiment harnesses can sweep/fit them.
Section references point at docs/DESIGN.md.
"""

# --- Determinism / time -------------------------------------------------------
SEED = 12345
TICK_DT = 1.0                 # time units advanced per live tick (DESIGN §2)

# --- Tank & environment grid (DESIGN §4) --------------------------------------
TANK_W = 320.0
TANK_H = 160.0
GRID_W = 32
GRID_H = 16
FOOD_CAP_PER_CELL = 5.0       # max standing food per grid cell
FOOD_REGEN_RATE = 0.05        # food units regenerated per cell per time unit
FOOD_ENERGY = 1.5             # energy gained per food unit eaten
# Metabolic stress coefficient: stress = 1 + K*(1-comfort). Kept low (0.6) so a
# starving organism can forage across the whole tank instead of dying inside its
# comfort zone — high stress caused seed-dependent local-depletion collapse
# (see FINDINGS.md).
STRESS_K = 0.6

# --- Metabolism (DESIGN §3) ---------------------------------------------------
BODY_BASE = 0.15              # base resting drain for size 1.0
SIZE_EXP = 0.75               # Kleiber-style allometric exponent
MOVE_COST = 0.01              # extra drain per unit speed

# --- Base body plan phenotype (before traits/scalars) -------------------------
# Keys are the flat Phenotype fields the sim reads in its hot loop (DESIGN §5.3).
BASE_PLAN = dict(
    maxSpeed=4.0, turnRate=1.0, size=1.0, hp=10.0, armor=0.0,
    attackPower=1.0, senseRadius=40.0,
    tempOptimum=0.5, tempRange=0.28,
    lightOptimum=0.5, lightRange=0.28,
    pressureOptimum=0.5, pressureRange=0.38,
    maxIntake=0.6,                # food units eaten per time unit when on food
    reproThreshold=60.0, reproCost=35.0, maturity=20.0, lifespan=600.0,
)

# --- Reproduction / mutation (DESIGN §5.4) ------------------------------------
STARTING_ENERGY = 30.0
REPRO_COOLDOWN = 25.0
MUT_SIGMA = 0.03              # gaussian relative drift on continuous genes
POP_HARD_CAP = 250           # safety ceiling for the live sim

# Continuous-gene clamp bounds after mutation (DESIGN §5.2 scalars)
GENE_BOUNDS = {
    "size": (0.4, 3.0),
    "speedBias": (0.5, 2.0),
    "metabolicEfficiency": (0.6, 1.5),
    "tempOptimum": (0.0, 1.0),
    "lightOptimum": (0.0, 1.0),
    "pressureOptimum": (0.0, 1.0),
}

# Default continuous genes for a freshly designed organism
DEFAULT_SCALARS = dict(
    size=1.0, speedBias=1.0, metabolicEfficiency=1.0,
    tempOptimum=0.5, lightOptimum=0.5, pressureOptimum=0.5,
)

# --- Cohort idle model (DESIGN §6.2) — defaults, refined by calibrate_idle.py -
IDLE = dict(
    B0=0.020,        # birth-rate scale per unit net energy
    D0=0.0016,       # baseline (old-age/attrition) death rate ~ 1/lifespan
    S=0.010,         # starvation death coefficient
    K=65.0,          # carrying capacity (organisms) — see FINDINGS.md calibration
    substeps=48,     # integration sub-steps across the whole idle interval
)
