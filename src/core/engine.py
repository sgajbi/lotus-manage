"""
FILE: src/core/engine.py
Compatibility shim for stable discretionary mandate imports.
"""

import warnings

from src.core.rebalance.engine import run_simulation

warnings.warn(
    "src.core.engine is deprecated; import from src.core.rebalance.engine.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["run_simulation"]
