"""OpenAPI enrichment utilities for lotus-manage."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from src.api.openapi_semantics import infer_openapi_description, infer_openapi_example

_JSON_MEDIA_TYPE = "application/json"
_PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4"
_HTTP_OPERATION_METHODS = frozenset({"get", "post", "put", "patch", "delete"})


def _schema_ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _schema_declared_example(prop_schema: dict[str, Any]) -> tuple[bool, Any]:
    if "example" in prop_schema:
        return True, prop_schema["example"]
    examples = prop_schema.get("examples")
    if isinstance(examples, list) and examples:
        return True, examples[0]
    return False, None


def _collection_example_from_schema(
    prop_name: str,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str],
) -> tuple[bool, Any]:
    for matched, example in (
        _properties_example_from_schema(
            prop_schema=prop_schema,
            schemas=schemas,
            seen_refs=seen_refs,
        ),
        _array_example_from_schema(
            prop_name=prop_name,
            prop_schema=prop_schema,
            schemas=schemas,
            seen_refs=seen_refs,
        ),
        _object_example_from_schema(
            prop_name=prop_name,
            prop_schema=prop_schema,
            schemas=schemas,
            seen_refs=seen_refs,
        ),
    ):
        if matched:
            return True, example
    return False, None


def _properties_example_from_schema(
    *,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str],
) -> tuple[bool, Any]:
    properties = prop_schema.get("properties")
    if isinstance(properties, dict):
        return True, {
            child_name: _example_from_schema(
                child_name,
                child_schema,
                schemas,
                seen_refs,
            )
            for child_name, child_schema in properties.items()
            if isinstance(child_schema, dict)
        }
    return False, None


def _array_example_from_schema(
    *,
    prop_name: str,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str],
) -> tuple[bool, Any]:
    schema_type = prop_schema.get("type")
    if schema_type == "array":
        item_schema = prop_schema.get("items", {})
        if isinstance(item_schema, dict):
            return True, [
                _example_from_schema(f"{prop_name}_item", item_schema, schemas, seen_refs)
            ]
        return True, []
    return False, None


def _object_example_from_schema(
    *,
    prop_name: str,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str],
) -> tuple[bool, Any]:
    schema_type = prop_schema.get("type")
    if schema_type == "object":
        additional_properties = prop_schema.get("additionalProperties")
        if isinstance(additional_properties, dict):
            return True, {
                "sample_key": _example_from_schema(
                    f"{prop_name}_value",
                    additional_properties,
                    schemas,
                    seen_refs,
                )
            }
        return True, {"sample_key": "sample_value"}

    return False, None


def _ref_example_from_schema(
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str],
) -> tuple[bool, Any]:
    schema_ref = prop_schema.get("$ref")
    if not isinstance(schema_ref, str):
        return False, None

    model_name = _schema_ref_name(schema_ref)
    if model_name in seen_refs:
        return True, {"sample_key": "sample_value"}
    resolved_schema = schemas.get(model_name)
    if isinstance(resolved_schema, dict):
        return True, _example_from_schema(
            model_name,
            resolved_schema,
            schemas,
            seen_refs | {model_name},
        )
    return False, None


def _composite_example_from_schema(
    prop_name: str,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str],
) -> tuple[bool, Any]:
    option = _first_composite_example_option(prop_schema)
    if option is not None:
        return True, _example_from_schema(prop_name, option, schemas, seen_refs)
    return False, None


def _first_composite_example_option(prop_schema: dict[str, Any]) -> dict[str, Any] | None:
    for options in _composite_schema_options(prop_schema):
        option = _first_non_null_schema_option(options)
        if option is not None:
            return option
    return None


def _composite_schema_options(prop_schema: dict[str, Any]) -> list[list[Any]]:
    return [
        options
        for composite_key in ("allOf", "oneOf", "anyOf")
        if isinstance(options := prop_schema.get(composite_key), list)
    ]


def _first_non_null_schema_option(options: list[Any]) -> dict[str, Any] | None:
    for option in options:
        if isinstance(option, dict) and option.get("type") != "null":
            return option
    return None


def _example_from_schema(
    prop_name: str,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str] | None = None,
) -> Any:
    seen_refs = seen_refs or set()
    if not isinstance(prop_schema, dict):
        return infer_openapi_example(prop_name, {})

    has_declared_example, declared_example = _schema_declared_example(prop_schema)
    if has_declared_example:
        return declared_example

    has_schema_example, schema_example = _resolved_schema_example(
        prop_name=prop_name,
        prop_schema=prop_schema,
        schemas=schemas,
        seen_refs=seen_refs,
    )
    if has_schema_example:
        return schema_example

    return infer_openapi_example(prop_name, prop_schema)


def _resolved_schema_example(
    *,
    prop_name: str,
    prop_schema: dict[str, Any],
    schemas: dict[str, Any],
    seen_refs: set[str],
) -> tuple[bool, Any]:
    for matched, example in (
        _ref_example_from_schema(prop_schema, schemas, seen_refs),
        _composite_example_from_schema(prop_name, prop_schema, schemas, seen_refs),
        _collection_example_from_schema(
            prop_name=prop_name,
            prop_schema=prop_schema,
            schemas=schemas,
            seen_refs=seen_refs,
        ),
    ):
        if matched:
            return True, example
    return False, None


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


def _error_title(status_code: str) -> str:
    return {
        "400": "Bad Request",
        "401": "Unauthorized",
        "403": "Forbidden",
        "404": "Not Found",
        "409": "Conflict",
        "422": "Validation Error",
        "424": "Failed Dependency",
        "500": "Internal Server Error",
        "503": "Service Unavailable",
        "default": "Unexpected Error",
    }.get(status_code, "Error")


def _error_status(status_code: str) -> int:
    if status_code.isdigit():
        return int(status_code)
    return 500


def _ensure_error_response_content(
    *,
    response: dict[str, Any],
    status_code: str,
) -> None:
    content = response.setdefault("content", {})
    json_content = content.setdefault(
        _JSON_MEDIA_TYPE,
        {
            "schema": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "example": "about:blank"},
                    "title": {"type": "string", "example": _error_title(status_code)},
                    "status": {"type": "integer", "example": _error_status(status_code)},
                    "detail": {
                        "type": "string",
                        "example": response.get("description") or "Request failed.",
                    },
                    "correlation_id": {"type": "string", "example": "corr_1234abcd"},
                },
            }
        },
    )
    if isinstance(json_content, dict):
        _ensure_json_content_example(
            content=json_content,
            schemas={},
            name=f"error_{status_code}",
            summary="Example error response.",
        )


def _ensure_request_body_example(
    *,
    operation: dict[str, Any],
    schemas: dict[str, Any],
    example_name: str,
) -> None:
    request_content = operation.get("requestBody", {}).get("content", {}).get(_JSON_MEDIA_TYPE)
    if not isinstance(request_content, dict):
        return
    _ensure_json_content_example(
        content=request_content,
        schemas=schemas,
        name=example_name,
        summary="Example request payload.",
    )


def _ensure_response_body_example(
    *,
    response: dict[str, Any],
    status_code: str,
    schemas: dict[str, Any],
    example_name: str,
) -> None:
    normalized_status_code = str(status_code)
    if _is_error_status_code(normalized_status_code):
        _ensure_error_response_content(
            response=response,
            status_code=normalized_status_code,
        )
    response_content = response.get("content", {}).get(_JSON_MEDIA_TYPE)
    if not isinstance(response_content, dict):
        return
    _ensure_json_content_example(
        content=response_content,
        schemas=schemas,
        name=example_name,
        summary="Example response payload.",
    )


def _ensure_operation_examples(
    *,
    method: str,
    path: str,
    operation: dict[str, Any],
    schemas: dict[str, Any],
) -> None:
    _ensure_request_body_example(
        operation=operation,
        schemas=schemas,
        example_name=f"{method}_{path}_request",
    )

    for status_code, response in operation.get("responses", {}).items():
        if not isinstance(response, dict):
            continue
        _ensure_response_body_example(
            response=response,
            status_code=str(status_code),
            schemas=schemas,
            example_name=f"{method}_{path}_{status_code}_response",
        )


def _is_http_operation_method(method: str) -> bool:
    return method.lower() in _HTTP_OPERATION_METHODS


def _ensure_metrics_path_examples(methods: dict[str, Any]) -> None:
    responses = methods.get("get", {}).setdefault("responses", {})
    responses.setdefault("200", {})["content"] = {
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
    for status_code, response in responses.items():
        if not isinstance(response, dict):
            continue
        normalized_status_code = str(status_code)
        if _is_error_status_code(normalized_status_code):
            _ensure_error_response_content(
                response=response,
                status_code=normalized_status_code,
            )


def _is_error_status_code(status_code: str) -> bool:
    return status_code.startswith(("4", "5")) or status_code == "default"


def _ensure_request_and_response_examples(schema: dict[str, Any]) -> None:
    schemas = _schema_example_schemas(schema)
    _ensure_metrics_paths_examples(schema)

    for path, method, operation in _schema_non_metrics_http_operations(schema):
        _ensure_operation_examples(
            method=method,
            path=path,
            operation=operation,
            schemas=schemas,
        )


def _schema_example_schemas(schema: dict[str, Any]) -> dict[str, Any]:
    return _schema_component_schemas(schema) or {}


def _ensure_metrics_paths_examples(schema: dict[str, Any]) -> None:
    for path, methods in _schema_path_methods(schema):
        if path == "/metrics":
            _ensure_metrics_path_examples(methods)


def _schema_non_metrics_http_operations(
    schema: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, methods in _schema_path_methods(schema):
        if path == "/metrics":
            continue
        yield from _path_http_operations(path=path, methods=methods)


def _ensure_operation_documentation(schema: dict[str, Any], service_name: str) -> None:
    for path, method, operation in _schema_http_operations(schema):
        _ensure_operation_default_docs(
            operation=operation,
            method=method,
            path=path,
            service_name=service_name,
        )
        _ensure_operation_default_error_response(operation)


def _schema_http_operations(
    schema: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, methods in _schema_path_methods(schema):
        yield from _path_http_operations(path=path, methods=methods)


def _schema_path_methods(schema: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return
    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue
        yield path, methods


def _path_http_operations(
    *, path: str, methods: dict[str, Any]
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for method, operation in methods.items():
        if (
            isinstance(method, str)
            and _is_http_operation_method(method)
            and isinstance(operation, dict)
        ):
            yield path, method, operation


def _ensure_operation_default_docs(
    *,
    operation: dict[str, Any],
    method: str,
    path: str,
    service_name: str,
) -> None:
    if not operation.get("summary"):
        operation["summary"] = f"{method.upper()} {path}"
    if not operation.get("description"):
        operation["description"] = f"{method.upper()} operation for {path} in {service_name}."
    if not operation.get("tags"):
        operation["tags"] = [_operation_tag_for_path(path)]


def _ensure_operation_default_error_response(operation: dict[str, Any]) -> None:
    responses = operation.get("responses")
    if isinstance(responses, dict) and not _operation_has_error_response(responses):
        responses["default"] = {"description": "Unexpected error response."}


def _operation_tag_for_path(path: str) -> str:
    if path.startswith("/health"):
        return "Health"
    if path == "/metrics":
        return "Monitoring"
    segment = path.strip("/").split("/", 1)[0] or "default"
    return segment.replace("-", " ").title()


def _operation_has_error_response(responses: dict[str, Any]) -> bool:
    return any(
        code.startswith("4") or code.startswith("5") or code == "default" for code in responses
    )


def _ensure_schema_documentation(schema: dict[str, Any]) -> None:
    for model_name, prop_name, prop_schema in _schema_documentable_properties(schema):
        _ensure_property_documentation(
            model_name=model_name,
            prop_name=prop_name,
            prop_schema=prop_schema,
        )


def _schema_documentable_properties(
    schema: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    schemas = _schema_component_schemas(schema)
    if schemas is None:
        return
    for model_name, model_schema in schemas.items():
        yield from _model_documentable_properties(model_name=model_name, model_schema=model_schema)


def _schema_component_schemas(schema: dict[str, Any]) -> dict[str, Any] | None:
    components = schema.get("components", {})
    if not isinstance(components, dict):
        return None
    schemas = components.get("schemas", {})
    return schemas if isinstance(schemas, dict) else None


def _model_documentable_properties(
    *, model_name: Any, model_schema: Any
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    if not isinstance(model_name, str):
        return
    for prop_name, prop_schema in _model_property_schemas(model_schema):
        yield model_name, prop_name, prop_schema


def _model_property_schemas(model_schema: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    if not isinstance(model_schema, dict):
        return
    properties = model_schema.get("properties", {})
    if not isinstance(properties, dict):
        return
    for prop_name, prop_schema in properties.items():
        property_schema = _documentable_property_schema(prop_name, prop_schema)
        if property_schema is not None:
            yield property_schema


def _documentable_property_schema(
    prop_name: Any,
    prop_schema: Any,
) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(prop_name, str):
        return None
    if not isinstance(prop_schema, dict):
        return None
    return prop_name, prop_schema


def _ensure_property_documentation(
    *, model_name: str, prop_name: str, prop_schema: dict[str, Any]
) -> None:
    if not prop_schema.get("description"):
        prop_schema["description"] = infer_openapi_description(model_name, prop_name, prop_schema)
    if "example" not in prop_schema:
        prop_schema["example"] = infer_openapi_example(prop_name, prop_schema)


def enrich_openapi_schema(schema: dict[str, Any], *, service_name: str) -> dict[str, Any]:
    _ensure_operation_documentation(schema, service_name=service_name)
    _ensure_schema_documentation(schema)
    _ensure_request_and_response_examples(schema)
    return schema
