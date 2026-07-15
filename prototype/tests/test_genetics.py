import numpy as np

from evotank_sim import config
from evotank_sim.genetics import Genome, TraitCatalog, compile_genome, mutate


def test_catalog_loads_seed_traits():
    cat = TraitCatalog.load()
    for tid in ("dorsal_fin", "armor_plate", "eyespot", "gills",
                "dark_pigment", "jaw", "filter_feeder"):
        assert tid in cat


def test_compile_base_plan():
    cat = TraitCatalog.load()
    ph = compile_genome(Genome(), cat)
    assert ph["size"] == config.BASE_PLAN["size"]
    # baseDrain = BODY_BASE * size^SIZE_EXP; size 1 -> BODY_BASE
    assert abs(ph["baseDrain"] - config.BODY_BASE) < 1e-9
    assert ph["traitDrain"] == 0.0


def test_armor_makes_body_costlier_and_slower():
    cat = TraitCatalog.load()
    base = compile_genome(Genome(), cat)
    armored = compile_genome(Genome(traitIds=["armor_plate"]), cat)
    assert armored["traitDrain"] > base["traitDrain"]       # heavier -> hungrier
    assert armored["armor"] > base["armor"]
    assert armored["maxSpeed"] < base["maxSpeed"]           # armor slows you down


def test_tolerance_modifier_shifts_optimum():
    cat = TraitCatalog.load()
    base = compile_genome(Genome(), cat)
    dark = compile_genome(Genome(traitIds=["dark_pigment"]), cat)
    assert dark["lightOptimum"] < base["lightOptimum"]      # prefers darker water


def test_mutation_stays_in_bounds():
    cat = TraitCatalog.load()
    rng = np.random.default_rng(1)
    g = Genome()
    for _ in range(500):
        g = mutate(g, rng)
        for key, (lo, hi) in config.GENE_BOUNDS.items():
            assert lo <= g.scalars[key] <= hi
    assert g.generation == 500                              # structural genes untouched
    assert g.traitIds == []


def test_signature_is_stable_for_identical_genomes():
    a = Genome(traitIds=["gills"], scalars=dict(config.DEFAULT_SCALARS))
    b = Genome(traitIds=["gills"], scalars=dict(config.DEFAULT_SCALARS))
    assert a.signature() == b.signature()
