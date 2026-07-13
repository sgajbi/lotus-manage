import pytest

import src.api.persistence_profile as profile


def _configure_valid_production_authz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv("ENTERPRISE_PRIMARY_KEY_ID", "manage-prod-kid")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        '{"POST /api/v1/rebalance/pm-operating-quality": "pm_quality.write"}',
    )


def test_profile_name_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_PERSISTENCE_PROFILE", raising=False)
    assert profile.app_persistence_profile_name() == "LOCAL"


def test_profile_name_normalizes_to_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", " production ")
    assert profile.app_persistence_profile_name() == "PRODUCTION"


def test_policy_pack_catalog_required_in_profile() -> None:
    assert profile.policy_pack_catalog_required_in_profile() is False


def test_policy_pack_catalog_required_when_runtime_or_admin_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    assert profile.policy_pack_catalog_required_in_profile() is True

    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "on")
    assert profile.policy_pack_catalog_required_in_profile() is True


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


def test_validate_persistence_profile_requires_dpm_postgres_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "")

    with pytest.raises(RuntimeError, match="PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN"):
        profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_requires_policy_pack_postgres_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    _configure_valid_production_authz(monkeypatch)
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")
    monkeypatch.setattr(profile, "policy_pack_catalog_backend_name", lambda: "ENV_JSON")

    with pytest.raises(RuntimeError, match="PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES"):
        profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_requires_policy_pack_postgres_dsn_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)
    _configure_valid_production_authz(monkeypatch)
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")
    monkeypatch.setattr(profile, "policy_pack_catalog_backend_name", lambda: "POSTGRES")

    with pytest.raises(
        RuntimeError,
        match="PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN",
    ):
        profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_requires_valid_postgres_access_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_POSTGRES_MAX_CONNECTIONS", "0")
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")

    with pytest.raises(
        RuntimeError,
        match="POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:DPM_POSTGRES_MAX_CONNECTIONS:1:100",
    ):
        profile.validate_persistence_profile_guardrails()


@pytest.mark.parametrize(
    ("env_updates", "expected"),
    [
        ({}, "PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_AUTHZ"),
        (
            {"ENTERPRISE_ENFORCE_AUTHZ": "true"},
            "PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_PRIMARY_KEY_ID",
        ),
        (
            {
                "ENTERPRISE_ENFORCE_AUTHZ": "true",
                "ENTERPRISE_PRIMARY_KEY_ID": "manage-prod-kid",
            },
            "PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_CAPABILITY_RULES",
        ),
    ],
)
def test_validate_persistence_profile_requires_production_authz_posture(
    monkeypatch: pytest.MonkeyPatch,
    env_updates: dict[str, str],
    expected: str,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.delenv("ENTERPRISE_ENFORCE_AUTHZ", raising=False)
    monkeypatch.delenv("ENTERPRISE_PRIMARY_KEY_ID", raising=False)
    monkeypatch.delenv("ENTERPRISE_CAPABILITY_RULES_JSON", raising=False)
    for name, value in env_updates.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")

    with pytest.raises(RuntimeError, match=expected):
        profile.validate_persistence_profile_guardrails()


def test_validate_persistence_profile_accepts_valid_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://policy")
    _configure_valid_production_authz(monkeypatch)
    monkeypatch.setattr(profile, "supportability_store_backend_name", lambda: "POSTGRES")
    monkeypatch.setattr(profile, "supportability_postgres_dsn", lambda: "postgresql://dpm")
    monkeypatch.setattr(profile, "policy_pack_catalog_backend_name", lambda: "POSTGRES")

    profile.validate_persistence_profile_guardrails()
