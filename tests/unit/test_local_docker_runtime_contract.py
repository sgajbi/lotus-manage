from pathlib import Path


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
    assert "python scripts/postgres_migrate.py --target all" in compose_text
    assert "urllib.request.urlopen('http://127.0.0.1:8000/health/ready'" in compose_text
    assert "COPY scripts/ ./scripts/" in dockerfile_text
    assert "psycopg[binary]" in pyproject_text


def test_ci_local_docker_compose_does_not_publish_internal_postgres_port() -> None:
    compose_text = Path("docker-compose.ci-local.yml").read_text(encoding="utf-8")

    assert "postgres:17.6" in compose_text
    assert '"5432:5432"' not in compose_text


def test_readme_documents_internal_postgres_port_stays_unpublished() -> None:
    readme_text = Path("README.md").read_text(encoding="utf-8")

    assert "does not publish the internal PostgreSQL port by default" in readme_text
    assert "`postgres:5432` remains internal to the Compose network" in readme_text
