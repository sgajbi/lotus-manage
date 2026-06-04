from __future__ import annotations

from pytest import MonkeyPatch

from src.api.services import service_config


def test_service_config_env_flag_parsing(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DPM_TEST_FLAG", "true")
    assert service_config.env_flag("DPM_TEST_FLAG", False) is True

    monkeypatch.setenv("DPM_TEST_FLAG", "0")
    assert service_config.env_flag("DPM_TEST_FLAG", True) is False

    monkeypatch.delenv("DPM_TEST_FLAG", raising=False)
    assert service_config.env_flag("DPM_TEST_FLAG", True) is True


def test_service_config_env_int_prefers_valid_positive_values_and_defaults_invalid_or_negative(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DPM_TEST_INT", "9")
    assert service_config.env_int("DPM_TEST_INT", 5) == 9

    monkeypatch.setenv("DPM_TEST_INT", "-1")
    assert service_config.env_int("DPM_TEST_INT", 5) == 5

    monkeypatch.setenv("DPM_TEST_INT", "bad")
    assert service_config.env_int("DPM_TEST_INT", 5) == 5

    monkeypatch.delenv("DPM_TEST_INT", raising=False)
    assert service_config.env_int("DPM_TEST_INT", 5) == 5


def test_service_config_env_float_parses_positive_values_and_defaults_non_positive_or_invalid(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DPM_TEST_FLOAT", "3.5")
    assert service_config.env_float("DPM_TEST_FLOAT", 2.5) == 3.5

    monkeypatch.setenv("DPM_TEST_FLOAT", "0")
    assert service_config.env_float("DPM_TEST_FLOAT", 2.5) == 2.5

    monkeypatch.setenv("DPM_TEST_FLOAT", "bad")
    assert service_config.env_float("DPM_TEST_FLOAT", 2.5) == 2.5

    monkeypatch.delenv("DPM_TEST_FLOAT", raising=False)
    assert service_config.env_float("DPM_TEST_FLOAT", 2.5) == 2.5


def test_service_config_env_non_negative_int_handles_zero_and_negative(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DPM_TEST_NON_NEGATIVE", "0")
    assert service_config.env_non_negative_int("DPM_TEST_NON_NEGATIVE", 5) == 0

    monkeypatch.setenv("DPM_TEST_NON_NEGATIVE", "-1")
    assert service_config.env_non_negative_int("DPM_TEST_NON_NEGATIVE", 5) == 5

    monkeypatch.setenv("DPM_TEST_NON_NEGATIVE", "bad")
    assert service_config.env_non_negative_int("DPM_TEST_NON_NEGATIVE", 5) == 5

    monkeypatch.delenv("DPM_TEST_NON_NEGATIVE", raising=False)
    assert service_config.env_non_negative_int("DPM_TEST_NON_NEGATIVE", 5) == 5


def test_service_config_env_csv_set_parses_tokens_and_fallback_default(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DPM_TEST_CSV", "A, B ,,C")
    assert service_config.env_csv_set("DPM_TEST_CSV", {"X"}) == {"A", "B", "C"}

    monkeypatch.delenv("DPM_TEST_CSV", raising=False)
    assert service_config.env_csv_set("DPM_TEST_CSV", {"X"}) == {"X"}
