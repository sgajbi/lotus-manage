from typing import Annotated

from fastapi import Query


SUPPORT_BUNDLE_QUERY_PARAMS = {
    "include_artifact",
    "include_async_operation",
    "include_idempotency_history",
}

IncludeArtifactQuery = Annotated[
    bool,
    Query(
        description="Whether to include deterministic run artifact payload in response.",
        examples=[True],
    ),
]
IncludeAsyncOperationQuery = Annotated[
    bool,
    Query(
        description="Whether to include async operation mapped by run correlation id.",
        examples=[True],
    ),
]
IncludeIdempotencyHistoryQuery = Annotated[
    bool,
    Query(
        description="Whether to include idempotency mapping history when run has idempotency key.",
        examples=[True],
    ),
]
