from typing import Optional

from src.api.services.rebalance_source_lineage import source_input_mode
from src.core.dpm_source_context import DpmResolvedSourceContext


def alternative_set_lineage_fields(
    *,
    request_hash: str,
    source_context: Optional[DpmResolvedSourceContext],
) -> dict[str, object]:
    return {
        "request_hash": request_hash,
        "input_mode": source_input_mode(source_context),
        "source_supportability_state": source_supportability_state(source_context),
    }


def source_supportability_state(
    source_context: Optional[DpmResolvedSourceContext],
) -> str | None:
    return source_context.context.supportability.state if source_context is not None else None


__all__ = [
    "alternative_set_lineage_fields",
    "source_supportability_state",
]
