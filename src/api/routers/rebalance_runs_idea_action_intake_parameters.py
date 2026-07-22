from __future__ import annotations

from typing import Annotated

from fastapi import Header

IdeaActionIntakeCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional source-safe correlation id supplied by lotus-idea.",
        max_length=128,
        examples=["corr-idea-action-001"],
    ),
]

IdeaActionIntakeIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description=(
            "Required replay-safe key for lotus-idea conversion-intent action intake. "
            "Replays with the same source request return the original receipt posture; "
            "conflicting payloads with the same key are rejected."
        ),
        min_length=1,
        max_length=160,
        examples=["idea-action-intake-idem-001"],
    ),
]
