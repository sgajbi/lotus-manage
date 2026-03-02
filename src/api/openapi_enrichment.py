"""OpenAPI enrichment utilities for lotus-manage."""

from __future__ import annotations

import re
from typing import Any

_EXAMPLE_BY_KEY: dict[str, Any] = {
    "portfolio_id": "DEMO_DPM_EUR_001",
    "proposal_id": "pp_001",
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


def _to_snake_case(value: str) -> str:
    transformed = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    transformed = transformed.replace("-", "_").replace(" ", "_")
    return transformed.lower()


def _humanize(key: str) -> str:
    return _to_snake_case(key).replace("_", " ").strip()


def _infer_example(prop_name: str, prop_schema: dict[str, Any]) -> Any:
    key = _to_snake_case(prop_name)
    if key in _EXAMPLE_BY_KEY:
        return _EXAMPLE_BY_KEY[key]

    enum_values = prop_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    schema_type = prop_schema.get("type")
    schema_format = prop_schema.get("format")
    if schema_type == "array":
        item_schema = prop_schema.get("items", {})
        return [_infer_example(f"{prop_name}_item", item_schema)]
    if schema_type == "object":
        return {"sample_key": "sample_value"}
    if schema_type == "boolean":
        return True
    if schema_type == "integer":
        return 10
    if schema_type == "number":
        if "weight" in key:
            return 0.125
        if "price" in key or "rate" in key:
            return 1.2345
        if "quantity" in key:
            return 100.0
        return 10.5

    if schema_format == "date":
        return "2026-03-02"
    if schema_format == "date-time":
        return "2026-03-02T10:30:00Z"

    if key.endswith("_id"):
        entity = key[: -len("_id")]
        return f"{entity.upper()}_001"
    if "currency" in key:
        return "USD"
    if "date" in key:
        return "2026-03-02"
    if "time" in key or "timestamp" in key:
        return "2026-03-02T10:30:00Z"
    if "status" in key:
        return "READY"
    if schema_type == "string":
        return f"sample_{key}"
    return f"{key}_example"


def _infer_description(model_name: str, prop_name: str, prop_schema: dict[str, Any]) -> str:
    key = _to_snake_case(prop_name)
    text = _humanize(prop_name)
    if key.endswith("_id"):
        entity = key[: -len("_id")].replace("_", " ")
        return f"Unique {entity} identifier."
    if "date" in key and prop_schema.get("format") == "date":
        return f"Business date for {text}."
    if "time" in key or prop_schema.get("format") == "date-time":
        return f"Timestamp for {text}."
    if "currency" in key:
        return f"ISO currency code for {text}."
    if "amount" in key or "value" in key:
        return f"Monetary value for {text}."
    if "quantity" in key:
        return f"Quantity value for {text}."
    if "rate" in key or "price" in key:
        return f"Rate/price value for {text}."
    if "status" in key:
        return f"Current status for {text}."
    return f"{_humanize(model_name)} field: {text}."


def _ensure_operation_documentation(schema: dict[str, Any], service_name: str) -> None:
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue
            if not operation.get("summary"):
                operation["summary"] = f"{method.upper()} {path}"
            if not operation.get("description"):
                operation["description"] = (
                    f"{method.upper()} operation for {path} in {service_name}."
                )
            if not operation.get("tags"):
                if path.startswith("/health"):
                    operation["tags"] = ["Health"]
                elif path == "/metrics":
                    operation["tags"] = ["Monitoring"]
                else:
                    segment = path.strip("/").split("/", 1)[0] or "default"
                    operation["tags"] = [segment.replace("-", " ").title()]

            responses = operation.get("responses")
            if isinstance(responses, dict):
                has_error = any(
                    code.startswith("4") or code.startswith("5") or code == "default"
                    for code in responses
                )
                if not has_error:
                    responses["default"] = {"description": "Unexpected error response."}


def _ensure_schema_documentation(schema: dict[str, Any]) -> None:
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    for model_name, model_schema in schemas.items():
        if not isinstance(model_schema, dict):
            continue
        properties = model_schema.get("properties", {})
        if not isinstance(properties, dict):
            continue
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            if not prop_schema.get("description"):
                prop_schema["description"] = _infer_description(model_name, prop_name, prop_schema)
            if "example" not in prop_schema:
                prop_schema["example"] = _infer_example(prop_name, prop_schema)


def enrich_openapi_schema(schema: dict[str, Any], *, service_name: str) -> dict[str, Any]:
    _ensure_operation_documentation(schema, service_name=service_name)
    _ensure_schema_documentation(schema)
    return schema
