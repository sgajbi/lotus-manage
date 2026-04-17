"""
FILE: src/core/engine.py
Compatibility shim for stable imports.
"""

import warnings

from src.core.advisory_engine import run_proposal_simulation
from src.core.rebalance.engine import run_simulation

warnings.warn(
    "src.core.engine is deprecated; import from src.core.rebalance.engine or src.core.advisory_engine.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["run_simulation", "run_proposal_simulation"]
