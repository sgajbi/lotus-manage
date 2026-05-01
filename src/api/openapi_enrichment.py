"""OpenAPI enrichment utilities for lotus-manage."""

from __future__ import annotations

import re
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

_JSON_MEDIA_TYPE = "application/json"
_PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4"


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


def _schema_ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _example_from_schema(
    prop_name: str,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str] | None = None,
) -> Any:
    seen_refs = seen_refs or set()

    if "example" in prop_schema:
        return prop_schema["example"]
    examples = prop_schema.get("examples")
    if isinstance(examples, list) and examples:
        return examples[0]

    schema_ref = prop_schema.get("$ref")
    if isinstance(schema_ref, str):
        model_name = _schema_ref_name(schema_ref)
        if model_name in seen_refs:
            return {"sample_key": "sample_value"}
        resolved_schema = schemas.get(model_name)
        if isinstance(resolved_schema, dict):
            return _example_from_schema(
                model_name,
                resolved_schema,
                schemas,
                seen_refs | {model_name},
            )

    for composite_key in ("allOf", "oneOf", "anyOf"):
        options = prop_schema.get(composite_key)
        if not isinstance(options, list):
            continue
        for option in options:
            if isinstance(option, dict) and option.get("type") != "null":
                return _example_from_schema(prop_name, option, schemas, seen_refs)

    properties = prop_schema.get("properties")
    if isinstance(properties, dict):
        return {
            child_name: _example_from_schema(child_name, child_schema, schemas, seen_refs)
            for child_name, child_schema in properties.items()
            if isinstance(child_schema, dict)
        }

    schema_type = prop_schema.get("type")
    if schema_type == "array":
        item_schema = prop_schema.get("items", {})
        if isinstance(item_schema, dict):
            return [_example_from_schema(f"{prop_name}_item", item_schema, schemas, seen_refs)]
        return []
    if schema_type == "object":
        additional_properties = prop_schema.get("additionalProperties")
        if isinstance(additional_properties, dict):
            return {
                "sample_key": _example_from_schema(
                    f"{prop_name}_value",
                    additional_properties,
                    schemas,
                    seen_refs,
                )
            }
        return {"sample_key": "sample_value"}

    return _infer_example(prop_name, prop_schema)


def _ensure_json_content_example(
    *,
    content: dict[str, Any],
    schemas: dict[str, Any],
    name: str,
    summary: str,
) -> None:
    if "example" in content or "examples" in content:
        return
    content["examples"] = {
        "default": {
            "summary": summary,
            "value": _example_from_schema(name, content.get("schema", {}), schemas),
        }
    }


def _ensure_request_and_response_examples(schema: dict[str, Any]) -> None:
    schemas = schema.get("components", {}).get("schemas", {})
    if not isinstance(schemas, dict):
        schemas = {}

    paths = schema.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        if path == "/metrics":
            methods.get("get", {}).setdefault("responses", {}).setdefault("200", {})["content"] = {
                _PROMETHEUS_MEDIA_TYPE: {
                    "schema": {"type": "string"},
                    "examples": {
                        "prometheus": {
                            "summary": "Prometheus metrics exposition.",
                            "value": (
                                "# HELP http_requests_total Total HTTP requests.\n"
                                "# TYPE http_requests_total counter\n"
                                'http_requests_total{service="lotus-manage",method="GET",'
                                'path="/health",status="200"} 1\n'
                            ),
                        }
                    },
                }
            }
            continue
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue

            request_content = (
                operation.get("requestBody", {}).get("content", {}).get(_JSON_MEDIA_TYPE)
            )
            if isinstance(request_content, dict):
                _ensure_json_content_example(
                    content=request_content,
                    schemas=schemas,
                    name=f"{method}_{path}_request",
                    summary="Example request payload.",
                )

            for status_code, response in operation.get("responses", {}).items():
                if not isinstance(response, dict):
                    continue
                response_content = response.get("content", {}).get(_JSON_MEDIA_TYPE)
                if isinstance(response_content, dict):
                    _ensure_json_content_example(
                        content=response_content,
                        schemas=schemas,
                        name=f"{method}_{path}_{status_code}_response",
                        summary="Example response payload.",
                    )


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
    _ensure_request_and_response_examples(schema)
    return schema
