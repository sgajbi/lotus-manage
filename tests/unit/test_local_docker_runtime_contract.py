from pathlib import Path

from scripts.ci_local_compose_project import compose_project_name


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
