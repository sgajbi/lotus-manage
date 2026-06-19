"""Semantic field metadata inference for generated OpenAPI schemas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_EXAMPLE_BY_KEY: dict[str, Any] = {
    "portfolio_id": "DEMO_DPM_EUR_001",
    "rebalance_run_id": "rr_001",
    "operation_id": "dop_001",
    "consumer_system": "lotus-gateway",
    "tenant_id": "default",
    "policy_pack_id": "dpm_standard_v1",
    "currency": "USD",
    "base_currency": "USD",
    "as_of_date": "2026-03-02",
    "generated_at": "2026-03-02T10:30:00Z",
    "created_at": "2026-03-02T10:30:00Z",
    "status": "READY",
    "contract_version": "v1",
    "source_service": "lotus-manage",
    "correlation_id": "corr_1234abcd",
    "idempotency_key": "idem_001",
    "request_hash": "sha256:abc123",
}


@dataclass(frozen=True)
class _DescriptionContext:
    key: str
    text: str
    schema_format: Any


@dataclass(frozen=True)
class _SemanticDescriptionRule:
    keyword_terms: tuple[str, ...]
    schema_formats: tuple[Any, ...]
    template: str
    require_keyword_and_format: bool = False

    def matches(self, context: _DescriptionContext) -> bool:
        key_matches = any(term in context.key for term in self.keyword_terms)
        format_matches = context.schema_format in self.schema_formats
        if self.require_keyword_and_format:
            return key_matches and format_matches
        return key_matches or format_matches

    def render(self, context: _DescriptionContext) -> str:
        return self.template.format(text=context.text)


@dataclass(frozen=True)
class _SemanticStringExampleRule:
    keyword_terms: tuple[str, ...]
    example: str

    def matches(self, key: str) -> bool:
        return any(term in key for term in self.keyword_terms)


_SEMANTIC_DESCRIPTION_RULES = (
    _SemanticDescriptionRule(
        ("date",),
        ("date",),
        "Business date for {text}.",
        require_keyword_and_format=True,
    ),
    _SemanticDescriptionRule(("time",), ("date-time",), "Timestamp for {text}."),
    _SemanticDescriptionRule(("currency",), (), "ISO currency code for {text}."),
    _SemanticDescriptionRule(("amount", "value"), (), "Monetary value for {text}."),
    _SemanticDescriptionRule(("quantity",), (), "Quantity value for {text}."),
    _SemanticDescriptionRule(("rate", "price"), (), "Rate/price value for {text}."),
    _SemanticDescriptionRule(("status",), (), "Current status for {text}."),
)

_SEMANTIC_STRING_EXAMPLE_RULES = (
    _SemanticStringExampleRule(("currency",), "USD"),
    _SemanticStringExampleRule(("time", "timestamp"), "2026-03-02T10:30:00Z"),
    _SemanticStringExampleRule(("date",), "2026-03-02"),
    _SemanticStringExampleRule(("status",), "READY"),
)


def infer_openapi_example(prop_name: str, prop_schema: dict[str, Any]) -> Any:
    key = _to_snake_case(prop_name)
    if key in _EXAMPLE_BY_KEY:
        return _EXAMPLE_BY_KEY[key]

    for matched, example in (
        _enum_example(prop_schema),
        _schema_type_example(prop_name, key=key, prop_schema=prop_schema),
        _schema_format_example(prop_schema),
    ):
        if matched:
            return example

    schema_type = prop_schema.get("type")
    semantic_string = _semantic_string_example_for_key(key, schema_type)
    if semantic_string is not None:
        return semantic_string
    return f"{key}_example"


def infer_openapi_description(model_name: str, prop_name: str, prop_schema: dict[str, Any]) -> str:
    context = _description_context(prop_name=prop_name, prop_schema=prop_schema)
    semantic_description = _semantic_description_for_context(context)
    if semantic_description is not None:
        return semantic_description
    return f"{_humanize(model_name)} field: {context.text}."


def _to_snake_case(value: str) -> str:
    transformed = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    transformed = transformed.replace("-", "_").replace(" ", "_")
    return transformed.lower()


def _humanize(key: str) -> str:
    return _to_snake_case(key).replace("_", " ").strip()


def _number_example_for_key(key: str) -> float:
    if "weight" in key:
        return 0.125
    if "price" in key or "rate" in key:
        return 1.2345
    if "quantity" in key:
        return 100.0
    return 10.5


def _semantic_string_example_for_key(key: str, schema_type: Any) -> str | None:
    identifier_example = _semantic_identifier_example(key)
    if identifier_example is not None:
        return identifier_example

    rule_example = _semantic_string_rule_example(key)
    if rule_example is not None:
        return rule_example

    if schema_type == "string":
        return f"sample_{key}"
    return None


def _semantic_identifier_example(key: str) -> str | None:
    if not key.endswith("_id"):
        return None
    entity = key[: -len("_id")]
    return f"{entity.upper()}_001"


def _semantic_string_rule_example(key: str) -> str | None:
    matching_rule = next(
        (rule for rule in _SEMANTIC_STRING_EXAMPLE_RULES if rule.matches(key)),
        None,
    )
    return matching_rule.example if matching_rule is not None else None


def _enum_example(prop_schema: dict[str, Any]) -> tuple[bool, Any]:
    enum_values = prop_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return True, enum_values[0]
    return False, None


def _schema_type_example(
    prop_name: str,
    *,
    key: str,
    prop_schema: dict[str, Any],
) -> tuple[bool, Any]:
    schema_type = prop_schema.get("type")
    example = _schema_type_example_value(
        schema_type=schema_type,
        prop_name=prop_name,
        key=key,
        prop_schema=prop_schema,
    )
    return (example is not None, example)


def _schema_type_example_value(
    *,
    schema_type: Any,
    prop_name: str,
    key: str,
    prop_schema: dict[str, Any],
) -> Any | None:
    if schema_type == "array":
        return _array_type_example(prop_name=prop_name, prop_schema=prop_schema)
    scalar_example = _scalar_type_example(schema_type=schema_type, key=key)
    if scalar_example is not None:
        return scalar_example
    return None


def _array_type_example(*, prop_name: str, prop_schema: dict[str, Any]) -> list[Any]:
    item_schema = prop_schema.get("items", {})
    return [infer_openapi_example(f"{prop_name}_item", item_schema)]


def _scalar_type_example(*, schema_type: Any, key: str) -> Any | None:
    if schema_type == "object":
        return {"sample_key": "sample_value"}
    if schema_type == "boolean":
        return True
    if schema_type == "integer":
        return 10
    if schema_type == "number":
        return _number_example_for_key(key)
    return None


def _schema_format_example(prop_schema: dict[str, Any]) -> tuple[bool, Any]:
    schema_format = prop_schema.get("format")
    if schema_format == "date":
        return True, "2026-03-02"
    if schema_format == "date-time":
        return True, "2026-03-02T10:30:00Z"
    return False, None


def _description_context(prop_name: str, prop_schema: dict[str, Any]) -> _DescriptionContext:
    return _DescriptionContext(
        key=_to_snake_case(prop_name),
        text=_humanize(prop_name),
        schema_format=prop_schema.get("format"),
    )


def _semantic_description_for_context(context: _DescriptionContext) -> str | None:
    if context.key.endswith("_id"):
        entity = context.key[: -len("_id")].replace("_", " ")
        return f"Unique {entity} identifier."
    matching_rule = next(
        (rule for rule in _SEMANTIC_DESCRIPTION_RULES if rule.matches(context)),
        None,
    )
    return matching_rule.render(context) if matching_rule is not None else None
