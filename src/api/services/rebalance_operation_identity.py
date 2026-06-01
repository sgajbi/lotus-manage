from __future__ import annotations

import uuid
from collections.abc import Callable


EntropyProvider = Callable[[], str]


def uuid_hex_entropy() -> str:
    return uuid.uuid4().hex


def resolve_rebalance_correlation_id(
    correlation_id: str | None,
    *,
    entropy_provider: EntropyProvider = uuid_hex_entropy,
) -> str:
    if correlation_id:
        return correlation_id
    return f"corr_{entropy_provider()[:12]}"


def create_batch_analysis_id(
    *,
    entropy_provider: EntropyProvider = uuid_hex_entropy,
) -> str:
    return f"batch_{entropy_provider()[:8]}"
