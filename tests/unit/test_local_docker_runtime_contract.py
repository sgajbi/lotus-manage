import json
from pathlib import Path

import pytest
import yaml

from scripts.ci_local_compose_project import compose_project_name

COMPOSITE_SETTINGS = (
    "DPM_COMPOSITE_SOURCES_JSON",
    "DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON",
    "DPM_COMPOSITE_ATTESTATION_VERIFICATION_JSON",
)
COMPOSITE_CREDENTIALS = (
    "MANAGE_COMPOSITE_SOURCE_AUTH",
    "MANAGE_HISTORICAL_PROVIDER_AUTH",
    "MANAGE_COMPOSITE_ATTESTATION_AUTH",
)


@pytest.mark.parametrize(
    "filename,service",
    [
        ("docker-compose.yml", "lotus-manage"),
        ("docker-compose.production.yml", "lotus-manage"),
        ("docker-compose.ci-local.yml", "ci-local"),
    ],
)
def test_compose_composite_settings_are_operator_supplied_only(filename, service) -> None:
    model = yaml.safe_load(Path(filename).read_text(encoding="utf-8"))
    environment = model["services"][service]["environment"]
    if isinstance(environment, list):
        environment = dict(entry.split("=", 1) for entry in environment)
    for setting in COMPOSITE_SETTINGS + COMPOSITE_CREDENTIALS:
        assert environment[setting] == "${" + setting + ":-}"
    # Provider authority must never be forwarded to the database service.
    database = model["services"].get("postgres", {}).get("environment", {})
    assert not any(
        setting in str(database) for setting in COMPOSITE_SETTINGS + COMPOSITE_CREDENTIALS
    )


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_absent_composite_configuration_keeps_all_channels_unavailable(monkeypatch, raw) -> None:
    from src.api.composition.composite_source_service import build_composite_subject_service
    from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository

    for setting in COMPOSITE_SETTINGS:
        if raw is None:
            monkeypatch.delenv(setting, raising=False)
        else:
            monkeypatch.setenv(setting, raw)
    service = build_composite_subject_service(InMemoryDpmCompositeRepository())
    assert type(service.candidates).__name__ == "UnavailableCandidateUniverseSource"
    assert type(service.historical_admission).__name__ == "UnavailableHistoricalPolicyAdmission"
    assert type(service.attestations).__name__ == "UnavailableInstitutionalEvidenceVerifier"


@pytest.mark.parametrize("setting", COMPOSITE_SETTINGS)
@pytest.mark.parametrize("raw", ["{", "{}", '{"unsupported_activation":true}'])
def test_composite_configuration_rejects_malformed_or_unsupported_input(
    monkeypatch, setting, raw
) -> None:
    from src.api.composition.composite_source_service import build_composite_subject_service
    from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository

    for name in COMPOSITE_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(setting, raw)
    with pytest.raises(ValueError):
        build_composite_subject_service(InMemoryDpmCompositeRepository())


def test_supplied_composite_configuration_selects_existing_independent_channels(
    monkeypatch,
) -> None:
    from src.api.composition.composite_source_service import build_composite_subject_service
    from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
    from tests.composite_institutional_helpers import configuration_material

    institutional, _, _ = configuration_material()
    institutional = institutional.model_copy(
        update={
            "verifier": institutional.verifier.model_copy(
                update={"credential_env": COMPOSITE_CREDENTIALS[2]}
            )
        }
    )
    source = institutional.verifier.model_dump(mode="json")
    source["evidence_posture"] = "SYNTHETIC_NON_CERTIFYING"
    source["credential_env"] = COMPOSITE_CREDENTIALS[0]
    sources = {"bindings": [source]}
    historical = Path("docs/examples/composite-historical-provider-configuration.json").read_text(
        encoding="utf-8"
    )
    monkeypatch.setenv(COMPOSITE_SETTINGS[0], json.dumps(sources))
    monkeypatch.setenv(COMPOSITE_SETTINGS[1], historical)
    monkeypatch.setenv(COMPOSITE_SETTINGS[2], institutional.model_dump_json())
    service = build_composite_subject_service(InMemoryDpmCompositeRepository())
    assert service.candidates.transport.configuration.bindings[0].evidence_posture == (
        "SYNTHETIC_NON_CERTIFYING"
    )
    assert (
        service.historical_admission.configuration.credential_env
        == "MANAGE_HISTORICAL_PROVIDER_AUTH"
    )
    assert service.attestations.configuration == institutional
    assert (
        service.candidates.transport.configuration.bindings[0].credential_env
        == COMPOSITE_CREDENTIALS[0]
    )
    assert service.attestations.configuration.verifier.credential_env == COMPOSITE_CREDENTIALS[2]
    # The separate attestation channel cannot enable qualified financial sources.
    sources["bindings"][0]["evidence_posture"] = "QUALIFIED_RECEIPT"
    monkeypatch.setenv(COMPOSITE_SETTINGS[0], json.dumps(sources))
    with pytest.raises(ValueError, match="COMPOSITE_SOURCE_INSTITUTIONAL_CHANNEL_REQUIRED"):
        build_composite_subject_service(InMemoryDpmCompositeRepository())


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_missing_controlled_credentials_refuse_before_transport(monkeypatch, raw) -> None:
    import httpx

    from src.infrastructure.composites.configured_sources import CompositeSourceTransport
    from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration
    from src.infrastructure.composites.historical_verifier import ConfiguredHistoricalPolicyVerifier
    from src.infrastructure.composites.source_configuration import CompositeSourceConfiguration
    from tests.composite_historical_policy_helpers import historical_contract_material
    from tests.composite_institutional_helpers import configuration_material

    for name in COMPOSITE_CREDENTIALS:
        if raw is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, raw)
    institutional, _, _ = configuration_material()
    historical = historical_contract_material()

    def unexpected_transport(request):
        pytest.fail("Missing credential must refuse before transport")

    with httpx.Client(transport=httpx.MockTransport(unexpected_transport)) as client:
        # Both configured synthetic and institutional channels use this exact transport.
        for name in (COMPOSITE_CREDENTIALS[0], COMPOSITE_CREDENTIALS[2]):
            binding = institutional.verifier.model_copy(update={"credential_env": name})
            transport = CompositeSourceTransport(
                CompositeSourceConfiguration(bindings=(binding,)), client
            )
            assert (
                transport.resolve(tenant_id=binding.tenant_id, operation="verification", request={})
                is None
            )
        admission = ConfiguredHistoricalPolicyVerifier(
            HistoricalPolicyConfiguration(
                endpoint="https://independent.test/historical",
                credential_env=COMPOSITE_CREDENTIALS[1],
                trust=historical[0].trust,
            ),
            client,
        )
        assert admission.verify(historical[1].verification.request) is None


def test_compose_profile_default_preserves_explicit_blank() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "APP_PERSISTENCE_PROFILE=${APP_PERSISTENCE_PROFILE-PRODUCTION}" in compose_text
    assert "APP_PERSISTENCE_PROFILE=${APP_PERSISTENCE_PROFILE:-" not in compose_text


def test_migration_rollout_runbook_uses_supported_admission_and_ci_paths() -> None:
    runbook = Path("docs/documentation/postgres-migration-rollout-runbook.md").read_text(
        encoding="utf-8"
    )
    assert "production_cutover_check.py" not in runbook
    assert "nightly-postgres-full.yml" not in runbook
    assert "postgres-cutover-checklist-2026-02-20.md" not in runbook
    assert "GET /health/ready" in runbook
    assert "make migration-smoke" in runbook
    assert "make test-idea-management-action-postgres-coverage" in runbook


def test_local_docker_compose_does_not_publish_internal_postgres_port() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "postgres:17.6" in compose_text
    assert '"5432:5432"' not in compose_text
    assert "${LOTUS_MANAGE_HOST_PORT:-8000}:8000" in compose_text


def test_local_docker_runtime_applies_postgres_migrations_before_startup() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")
    dockerfile_text = Path("Dockerfile").read_text(encoding="utf-8")
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "depends_on:" in compose_text
    assert "condition: service_healthy" in compose_text
    assert "python scripts/postgres_migrate.py --target dpm" in compose_text
    assert "urllib.request.urlopen('http://127.0.0.1:8000/health/ready'" in compose_text
    assert "COPY scripts/ ./scripts/" in dockerfile_text
    assert "psycopg[binary]" in pyproject_text


def test_local_docker_runtime_exposes_async_execution_controls() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "DPM_ASYNC_EXECUTION_MODE=${DPM_ASYNC_EXECUTION_MODE:-INLINE}" in compose_text
    assert (
        "DPM_ASYNC_EXECUTION_LEASE_SECONDS=${DPM_ASYNC_EXECUTION_LEASE_SECONDS:-300}"
        in compose_text
    )
    assert (
        "DPM_ASYNC_MANUAL_EXECUTION_ENABLED=${DPM_ASYNC_MANUAL_EXECUTION_ENABLED:-true}"
        in compose_text
    )


def test_local_docker_runtime_exposes_lineage_feature_gate() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "DPM_LINEAGE_APIS_ENABLED=${DPM_LINEAGE_APIS_ENABLED:-false}" in compose_text


def test_local_docker_runtime_exposes_idempotency_history_feature_gate() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert (
        "DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=${DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED:-false}"
        in compose_text
    )


def test_local_docker_runtime_exposes_stateful_core_sourcing_gates() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert (
        "DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED=${DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED:-false}"
        in compose_text
    )
    assert (
        "DPM_STATEFUL_CORE_SOURCING_ENABLED=${DPM_STATEFUL_CORE_SOURCING_ENABLED:-false}"
        in compose_text
    )
    assert "DPM_CORE_BASE_URL=${DPM_CORE_BASE_URL:-}" in compose_text
    assert "DPM_CORE_QUERY_BASE_URL=${DPM_CORE_QUERY_BASE_URL:-}" in compose_text


def test_ci_local_docker_compose_does_not_publish_internal_postgres_port() -> None:
    compose_text = Path("docker-compose.ci-local.yml").read_text(encoding="utf-8")
    dockerfile_text = Path("Dockerfile.ci-local").read_text(encoding="utf-8")

    assert "postgres:17.6" in compose_text
    assert '"5432:5432"' not in compose_text
    assert "apt-get install --no-install-recommends --yes git make" in dockerfile_text
    assert "git config --system --add safe.directory /workspace" in dockerfile_text
    assert 'pip install -e ".[dev,quality]"' in dockerfile_text
    assert 'command: ["sh", "-lc", "make ci-local"]' in compose_text
    assert "../lotus-platform:/lotus-platform:ro" in compose_text
    for repository in (
        "lotus-core",
        "lotus-performance",
        "lotus-risk",
        "lotus-advise",
        "lotus-report",
        "lotus-gateway",
        "lotus-idea",
    ):
        assert (
            f"../{repository}/contracts/domain-data-products:/{repository}/contracts/"
            "domain-data-products:ro"
        ) in compose_text
    assert (
        "./contracts/domain-data-products:/lotus-manage/contracts/domain-data-products:ro"
        in compose_text
    )


def test_ci_local_compose_cleanup_uses_an_isolated_project_identity() -> None:
    makefile_text = Path("Makefile").read_text(encoding="utf-8")

    assert (
        "CI_LOCAL_COMPOSE_PROJECT ?= $(shell python scripts/ci_local_compose_project.py)"
        in makefile_text
    )
    assert (
        'docker compose --project-name "$(CI_LOCAL_COMPOSE_PROJECT)" '
        "-f docker-compose.ci-local.yml "
        "up --build --abort-on-container-exit --exit-code-from ci-local ci-local"
    ) in makefile_text
    assert (
        'docker compose --project-name "$(CI_LOCAL_COMPOSE_PROJECT)" '
        "-f docker-compose.ci-local.yml down -v --remove-orphans"
    ) in makefile_text
    assert "docker compose -f docker-compose.ci-local.yml down" not in makefile_text


def test_ci_local_compose_project_name_is_stable_and_checkout_specific(tmp_path: Path) -> None:
    first_checkout = tmp_path / "first" / "lotus-manage"
    second_checkout = tmp_path / "second" / "lotus-manage"

    first_name = compose_project_name(first_checkout)

    assert first_name == compose_project_name(first_checkout)
    assert first_name != compose_project_name(second_checkout)
    assert first_name.startswith("lotus-manage-ci-local-lotus-manage-")
    assert first_name.replace("-", "").isalnum()


def test_readme_documents_internal_postgres_port_stays_unpublished() -> None:
    readme_text = Path("README.md").read_text(encoding="utf-8")

    assert "does not publish the internal PostgreSQL port by default" in readme_text
    assert "`postgres:5432` remains internal to the Compose network" in readme_text


def test_manage_core_live_validation_has_repo_native_command_and_docs() -> None:
    makefile_text = Path("Makefile").read_text(encoding="utf-8")
    readme_text = Path("README.md").read_text(encoding="utf-8")
    validation_wiki_text = Path("wiki/Validation-and-CI.md").read_text(encoding="utf-8")

    assert "live-api-validate-core:" in makefile_text
    assert "demo-certify:" in makefile_text
    assert "--core-base-url $${LOTUS_CORE_CONTROL_BASE_URL:-http://core-control.dev.lotus}" in (
        makefile_text
    )
    assert "--expect-core-dpm-route $${LOTUS_MANAGE_EXPECT_CORE_DPM_ROUTE:-absent}" in (
        makefile_text
    )
    assert (
        "--expect-stateful-core-sourcing $${LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING:-available}"
    ) in makefile_text
    assert "LOTUS_MANAGE_DEMO_CERT_OUTPUT" in makefile_text
    assert "`make live-api-validate-core`" in readme_text
    assert "`make demo-certify`" in readme_text
    assert "RFC-087 certified source-data" in readme_text
    assert "products and canonical data is seeded" in readme_text
    assert "non-source-ready local runtime" in readme_text
    assert "make live-api-validate-core" in validation_wiki_text
    assert "make demo-certify" in validation_wiki_text
    assert "RFC-087 certified composed DPM source-data products" in validation_wiki_text
    assert "canonical source-ready stack defaults" in validation_wiki_text
