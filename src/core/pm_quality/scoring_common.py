"""Shared primitives for PM operating-quality scoring."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from src.core.outcomes import DpmOutcomeSourceRef


class DpmPmQualityValidationError(Exception):
    """Raised when a PM quality score run cannot be evaluated safely."""


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _dedupe_refs(refs: list[DpmOutcomeSourceRef]) -> list[DpmOutcomeSourceRef]:
    by_key: dict[tuple[str, str, str], DpmOutcomeSourceRef] = {}
    for ref in refs:
        by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    return [by_key[key] for key in sorted(by_key)]


def _optional_model_dump(model: Any | None) -> dict[str, Any] | None:
    return model.model_dump(mode="json") if model is not None else None


def _optional_decimal_as_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _content_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
