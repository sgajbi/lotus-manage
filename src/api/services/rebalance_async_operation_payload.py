from dataclasses import dataclass
from typing import Any, Optional

from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import BatchRebalanceRequest


@dataclass(frozen=True)
class AnalyzeAsyncExecutionPayload:
    request: BatchRebalanceRequest
    source_context: Optional[DpmResolvedSourceContext]
    request_policy_pack_id: Optional[str]
    tenant_default_policy_pack_id: Optional[str]
    tenant_id: Optional[str]


def resolve_analyze_async_execution_payload(
    request_json: Any,
) -> AnalyzeAsyncExecutionPayload:
    if isinstance(request_json, dict) and "batch_request" in request_json:
        batch_payload = request_json.get("batch_request") or {}
        policy_context = request_json.get("policy_context") or {}
        source_context_payload = request_json.get("source_context")
        request_policy_pack_id = policy_context.get("request_policy_pack_id")
        tenant_default_policy_pack_id = policy_context.get("tenant_default_policy_pack_id")
        tenant_id = policy_context.get("tenant_id")
    else:
        batch_payload = request_json
        source_context_payload = None
        request_policy_pack_id = None
        tenant_default_policy_pack_id = None
        tenant_id = None

    source_context = (
        DpmResolvedSourceContext.model_validate(source_context_payload)
        if source_context_payload
        else None
    )
    return AnalyzeAsyncExecutionPayload(
        request=BatchRebalanceRequest.model_validate(batch_payload),
        source_context=source_context,
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )


__all__ = [
    "AnalyzeAsyncExecutionPayload",
    "resolve_analyze_async_execution_payload",
]
