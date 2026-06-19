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


@dataclass(frozen=True)
class _AnalyzeAsyncExecutionPayloadParts:
    batch_payload: Any
    source_context_payload: Any
    request_policy_pack_id: Optional[str]
    tenant_default_policy_pack_id: Optional[str]
    tenant_id: Optional[str]


def resolve_analyze_async_execution_payload(
    request_json: Any,
) -> AnalyzeAsyncExecutionPayload:
    payload_parts = _analyze_async_execution_payload_parts(request_json)
    source_context = _resolved_source_context(payload_parts.source_context_payload)
    return AnalyzeAsyncExecutionPayload(
        request=BatchRebalanceRequest.model_validate(payload_parts.batch_payload),
        source_context=source_context,
        request_policy_pack_id=payload_parts.request_policy_pack_id,
        tenant_default_policy_pack_id=payload_parts.tenant_default_policy_pack_id,
        tenant_id=payload_parts.tenant_id,
    )


def _analyze_async_execution_payload_parts(
    request_json: Any,
) -> _AnalyzeAsyncExecutionPayloadParts:
    if not _is_current_analyze_async_payload(request_json):
        return _legacy_analyze_async_execution_payload_parts(request_json)

    policy_context = _mapping(request_json.get("policy_context"))
    return _AnalyzeAsyncExecutionPayloadParts(
        batch_payload=request_json.get("batch_request") or {},
        source_context_payload=request_json.get("source_context"),
        request_policy_pack_id=policy_context.get("request_policy_pack_id"),
        tenant_default_policy_pack_id=policy_context.get("tenant_default_policy_pack_id"),
        tenant_id=policy_context.get("tenant_id"),
    )


def _legacy_analyze_async_execution_payload_parts(
    request_json: Any,
) -> _AnalyzeAsyncExecutionPayloadParts:
    return _AnalyzeAsyncExecutionPayloadParts(
        batch_payload=request_json,
        source_context_payload=None,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id=None,
        tenant_id=None,
    )


def _is_current_analyze_async_payload(request_json: Any) -> bool:
    return isinstance(request_json, dict) and "batch_request" in request_json


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _resolved_source_context(source_context_payload: Any) -> DpmResolvedSourceContext | None:
    return (
        DpmResolvedSourceContext.model_validate(source_context_payload)
        if source_context_payload
        else None
    )


__all__ = [
    "AnalyzeAsyncExecutionPayload",
    "resolve_analyze_async_execution_payload",
]
