"""Shared bootstrap for experiment scripts: path setup, species factory, output dir."""

import os
import sys

# Make the prototype root importable (so `import evotank_sim` works) regardless
# of the current working directory.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import matplotlib                     # noqa: E402
matplotlib.use("Agg")                 # headless plotting

from evotank_sim.genetics import Genome, TraitCatalog  # noqa: E402

OUT_DIR = os.path.join(_ROOT, "out")
os.makedirs(OUT_DIR, exist_ok=True)


def catalog() -> TraitCatalog:
    return TraitCatalog.load()


def species(lineage: str, traits=None, scalars=None) -> Genome:
    """Build a designed founder genome."""
    from evotank_sim import config
    g = Genome(lineageId=lineage, traitIds=list(traits or []))
    g.scalars = dict(config.DEFAULT_SCALARS)
    if scalars:
        g.scalars.update(scalars)
    return g


def out(name: str) -> str:
    return os.path.join(OUT_DIR, name)
