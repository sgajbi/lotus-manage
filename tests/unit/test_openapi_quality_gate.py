from scripts.openapi_quality_gate import evaluate_schema


def _minimal_schema(operation: dict) -> dict:
    return {
        "paths": {"/api/v1/example": {"post": operation}},
        "components": {"schemas": {}},
    }


def test_openapi_quality_gate_requires_json_request_examples() -> None:
    schema = _minimal_schema(
        {
            "summary": "Create example",
            "description": "Creates an example resource.",
            "tags": ["Example"],
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"type": "object"},
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Created.",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                            "examples": {"default": {"value": {}}},
                        }
                    },
                },
                "default": {"description": "Unexpected error."},
            },
        }
    )

    assert "  - POST /api/v1/example: missing request example" in evaluate_schema(
        schema,
        service_name="lotus-manage",
    )


def test_openapi_quality_gate_requires_json_response_examples() -> None:
    schema = _minimal_schema(
        {
            "summary": "Create example",
            "description": "Creates an example resource.",
            "tags": ["Example"],
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"type": "object"},
                        "examples": {"default": {"value": {}}},
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Created.",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        }
                    },
                },
                "default": {"description": "Unexpected error."},
            },
        }
    )

    assert "  - POST /api/v1/example: missing 200 response example" in evaluate_schema(
        schema,
        service_name="lotus-manage",
    )
