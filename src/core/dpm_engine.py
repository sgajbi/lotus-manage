"""
Backward-compatible shim for DPM engine module path.

Preferred import:
`from src.core.dpm.engine import run_simulation`
"""

import warnings

from src.core.dpm.engine import (
    _apply_group_constraints,
    _apply_turnover_limit,
    _calculate_turnover_score,
    _generate_fx_and_simulate,
    _generate_targets,
    run_simulation,
)

warnings.warn(
    "src.core.dpm_engine is deprecated; use src.core.dpm.engine instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "run_simulation",
    "_generate_targets",
    "_generate_fx_and_simulate",
    "_apply_turnover_limit",
    "_calculate_turnover_score",
    "_apply_group_constraints",
]
