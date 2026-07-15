from evotank_sim.cohort import Cohort, CohortModel, deflate, inflate
from evotank_sim.genetics import Genome, TraitCatalog, compile_genome
from evotank_sim.live_sim import LiveSimulation


def _cohort(n, cat, mean_age=0.0):
    g = Genome(lineageId="t")
    ph = compile_genome(g, cat)
    return Cohort(g, ph, N=float(n), meanEnergy=30.0, meanAge=mean_age)


def test_deflate_groups_identical_genomes_into_one_cohort():
    cat = TraitCatalog.load()
    sim = LiveSimulation(cat, seed=3)
    sim.seed_species(Genome(lineageId="A"), 12)
    cohorts, food = deflate(sim)
    assert len(cohorts) == 1
    assert cohorts[0].N == 12
    assert food > 0


def test_population_grows_toward_K_when_well_fed():
    cat = TraitCatalog.load()
    model = CohortModel(dict(B0=0.03, D0=0.001, S=0.01, K=80.0))
    c = _cohort(5, cat)
    result = model.advance([c], food_stock=5000.0, elapsed=3000.0)
    final = sum(ch.N for ch in result.cohorts)
    assert 5 < final <= 80 * 1.05           # grows but capped near K
    assert result.births > result.deaths


def test_high_death_collapses_population():
    cat = TraitCatalog.load()
    model = CohortModel(dict(B0=0.0, D0=0.05, S=0.05, K=50.0))
    c = _cohort(10, cat, mean_age=500.0)
    result = model.advance([c], food_stock=0.0, elapsed=8 * 3600)
    assert round(sum(ch.N for ch in result.cohorts)) == 0


def test_inflate_repopulates_live_entities():
    cat = TraitCatalog.load()
    sim = LiveSimulation(cat, seed=7)
    model = CohortModel()
    c = _cohort(6, cat)
    result = model.advance([c], food_stock=2000.0, elapsed=1.0)
    inflate(result, sim, cat)
    assert len(sim.organisms) == int(round(result.cohorts[0].N))
