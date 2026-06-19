from src.core.common.ai_guardrails import forbidden_field_names, sanitize_for_ai


def test_forbidden_field_names_detects_nested_dicts_and_lists() -> None:
    payload = {
        "allowed": "kept",
        "client_name": "Sensitive Name",
        "sections": [
            {"raw_payload": {"account_number": "123"}},
            {"metrics": {"token": "secret-token"}},
        ],
    }

    assert forbidden_field_names(payload) == {
        "account_number",
        "client_name",
        "raw_payload",
        "token",
    }


def test_sanitize_for_ai_removes_forbidden_fields_and_preserves_allowed_values() -> None:
    removed: set[str] = set()
    payload = {
        "summary": "Allowed",
        "raw_response": {"secret": "hidden", "allowed_nested": "removed with parent"},
        "items": [
            {"email": "client@example.invalid", "metric": "kept"},
            {"phone": "123", "allowed": {"score": "kept"}},
        ],
    }

    sanitized = sanitize_for_ai(payload, removed)

    assert sanitized == {
        "summary": "Allowed",
        "items": [
            {"metric": "kept"},
            {"allowed": {"score": "kept"}},
        ],
    }
    assert removed == {"email", "phone", "raw_response"}
    assert forbidden_field_names(sanitized) == set()


def test_ai_guardrails_ignore_non_string_keys() -> None:
    removed: set[str] = set()
    payload = {1: {"secret": "removed"}, ("token",): "not-a-field-name"}

    assert sanitize_for_ai(payload, removed) == {1: {}, ("token",): "not-a-field-name"}
    assert removed == {"secret"}
    assert forbidden_field_names({("token",): "not-a-field-name"}) == set()
