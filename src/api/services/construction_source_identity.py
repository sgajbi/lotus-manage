from dataclasses import dataclass
from typing import Any, TypeAlias

from pydantic import BaseModel

from src.core.common.canonical import hash_canonical_payload

JsonPayload: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class SourceProductIdentity:
    source_product_name: str
    source_product_version: str
    source_system: str
    source_id: str
    content_hash: str


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


def _required_str_attr(response: BaseModel, attr_name: str) -> str:
    value = getattr(response, attr_name)
    if not isinstance(value, str):
        raise TypeError(f"{attr_name} must be a string source-product field")
    return value


def source_product_identity(
    response: BaseModel,
    *,
    source_system: str = "lotus-core",
) -> SourceProductIdentity:
    payload = source_payload(response)
    content_hash = source_hash(payload)
    return SourceProductIdentity(
        source_product_name=_required_str_attr(response, "product_name"),
        source_product_version=_required_str_attr(response, "product_version"),
        source_system=source_system,
        source_id=response_source_id(response, content_hash),
        content_hash=content_hash,
    )


__all__ = [
    "JsonPayload",
    "SourceProductIdentity",
    "response_source_id",
    "source_hash",
    "source_payload",
    "source_product_identity",
]
