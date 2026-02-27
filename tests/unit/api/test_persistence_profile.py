import pytest

import src.api.persistence_profile as profile


def test_profile_name_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_PERSISTENCE_PROFILE", raising=False)
    assert profile.app_persistence_profile_name() == "LOCAL"


def test_profile_name_normalizes_to_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", " production ")
    assert profile.app_persistence_profile_name() == "PRODUCTION"


def test_policy_pack_catalog_required_in_profile() -> None:
    assert profile.policy_pack_catalog_required_in_profile() is False


def test_validate_persistence_profile_noop_for_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "LOCAL")
    profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_requires_dpm_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "INMEMORY")

    with pytest.raises(RuntimeError, match="PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES"):
        profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_requires_advisory_postgres_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")
    monkeypatch.setattr(profile, "proposal_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "proposal_postgres_dsn", lambda: "")

    with pytest.raises(RuntimeError, match="PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"):
        profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_requires_policy_pack_postgres_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")
    monkeypatch.setattr(profile, "proposal_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "proposal_postgres_dsn", lambda: "postgresql://proposal")
    monkeypatch.setattr(profile, "policy_pack_catalog_backend_name", lambda: "ENV_JSON")

    with pytest.raises(RuntimeError, match="PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES"):
        profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_accepts_valid_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://policy")
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")
    monkeypatch.setattr(profile, "proposal_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "proposal_postgres_dsn", lambda: "postgresql://proposal")
    monkeypatch.setattr(profile, "policy_pack_catalog_backend_name", lambda: "POSTGRES")

    profile.validate_persistence_profile_guardrails()
