from __future__ import annotations

from typing import Annotated

from fastapi import Header


PmQualityCorrelationIdHeader = Annotated[
    str | None,
    Header(
        description=(
            "Optional correlation id for PM operating quality audit, supportability, and "
            "downstream governance traceability."
        ),
        examples=["corr-pmq-001"],
    ),
]
