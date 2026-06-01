from typing import Optional

from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import BatchRebalanceRequest


def build_analyze_async_request_json(
    *,
    request: BatchRebalanceRequest,
    policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str],
    tenant_id: Optional[str],
    source_context: Optional[DpmResolvedSourceContext],
) -> dict[str, object]:
    return {
        "batch_request": request.model_dump(mode="json"),
        "policy_context": {
            "request_policy_pack_id": policy_pack_id,
            "tenant_default_policy_pack_id": tenant_default_policy_pack_id,
            "tenant_id": tenant_id,
        },
        "source_context": (
            source_context.model_dump(mode="json") if source_context is not None else None
        ),
    }


__all__ = ["build_analyze_async_request_json"]
