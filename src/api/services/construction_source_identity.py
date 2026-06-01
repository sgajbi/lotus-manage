from typing import Any, TypeAlias

from pydantic import BaseModel

from src.core.common.canonical import hash_canonical_payload

JsonPayload: TypeAlias = dict[str, Any]


def source_payload(response: BaseModel) -> JsonPayload:
    return response.model_dump(mode="json", exclude_none=True)


def source_hash(payload: JsonPayload) -> str:
    return hash_canonical_payload(payload)


def response_source_id(response: BaseModel, fallback_hash: str) -> str:
    source_batch_fingerprint = getattr(response, "source_batch_fingerprint", None)
    if isinstance(source_batch_fingerprint, str) and source_batch_fingerprint:
        return source_batch_fingerprint
    lineage = getattr(response, "lineage", {})
    if isinstance(lineage, dict):
        lineage_fingerprint = lineage.get("source_batch_fingerprint")
        if isinstance(lineage_fingerprint, str) and lineage_fingerprint:
            return lineage_fingerprint
    return fallback_hash


__all__ = ["JsonPayload", "response_source_id", "source_hash", "source_payload"]
