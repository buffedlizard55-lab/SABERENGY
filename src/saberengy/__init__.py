"""
SABERENGY — Open Source SaberSim Reverse Engineering
Verified against official SaberSim docs:
- https://support.sabersim.com/en/articles/12078831-how-projections-work
- https://support.sabersim.com/en/articles/12079199-how-contest-sims-work
- https://support.sabersim.com/en/articles/12079141-building-lineups
- https://www.sabersim.com/pricing

No hallucinations — all logic derived from public docs.
"""
__version__ = "1.0.0"
from .simulation import Simulator, GameScript, PlayerOutcome
from .projections import ProjectionEngine
from .ownership import OwnershipModel, FieldLineups
from .contest_sim import ContestSimulator
from .optimizer import SimOptimizer, OptimizerMode

__all__ = [
    "Simulator",
    "GameScript",
    "PlayerOutcome",
    "ProjectionEngine",
    "OwnershipModel",
    "FieldLineups",
    "ContestSimulator",
    "SimOptimizer",
    "OptimizerMode",
]
