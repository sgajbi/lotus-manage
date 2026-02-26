"""Advisory engine package-path shim."""

import warnings

from src.core.advisory_engine import (
    build_reconciliation,
    derive_status_from_rules,
    run_proposal_simulation,
)

warnings.warn(
    "src.core.advisory.engine is deprecated; use src.core.advisory_engine instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["run_proposal_simulation", "build_reconciliation", "derive_status_from_rules"]
