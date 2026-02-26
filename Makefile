.PHONY: install check check-all test test-unit test-integration test-e2e test-all test-fast test-all-fast test-all-no-cov test-all-parallel ci ci-local ci-local-docker ci-local-docker-down typecheck lint monetary-float-guard format clean run check-deps security-audit openapi-gate migration-smoke migration-apply pre-commit docker-up docker-down

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install pre-commit
	pre-commit install

pre-commit:
	pre-commit run --all-files

check: lint typecheck openapi-gate test

ci: lint typecheck openapi-gate migration-smoke test-all security-audit

test:
	$(MAKE) test-unit

test-unit:
	python -m pytest tests/unit

test-integration:
	python -m pytest tests/integration

test-e2e:
	python -m pytest tests/e2e

test-all:
	python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=99

# Fast local loop: unit tests only (no coverage)
test-fast:
	python -m pytest tests/unit -q

# Full suite with coverage gate, but without term-missing output overhead
test-all-fast:
	python -m pytest --cov=src --cov-report= --cov-fail-under=99

# Full suite without coverage for quickest full functional signal
test-all-no-cov:
	python -m pytest

# Full suite, optional parallel workers when pytest-xdist is installed
test-all-parallel:
	python -c "import importlib.util, subprocess, sys; args=[sys.executable,'-m','pytest','--cov=src','--cov-report=','--cov-fail-under=99']; args += (['-n','auto','--dist','loadscope'] if importlib.util.find_spec('xdist') else []); raise SystemExit(subprocess.call(args))"

# Local execution flow aligned with .github/workflows/ci.yml
ci-local: lint check-deps
	python -m pip check
	COVERAGE_FILE=.coverage.unit python -m pytest tests/unit --cov=src --cov-report=
	COVERAGE_FILE=.coverage.integration python -m pytest tests/integration --cov=src --cov-report=
	COVERAGE_FILE=.coverage.e2e python -m pytest tests/e2e --cov=src --cov-report=
	python -m coverage combine .coverage.unit .coverage.integration .coverage.e2e
	python -m coverage report --fail-under=99
	$(MAKE) typecheck

ci-local-docker:
	docker compose -f docker-compose.ci-local.yml up --build --abort-on-container-exit --exit-code-from ci-local ci-local

ci-local-docker-down:
	docker compose -f docker-compose.ci-local.yml down -v --remove-orphans

check-all: lint typecheck test-all

typecheck:
	mypy --config-file mypy.ini

openapi-gate:
	python -m pytest tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q

migration-smoke:
	python -m pytest tests/unit/shared/dependencies/test_postgres_migrations.py tests/unit/shared/dependencies/test_production_cutover_contract.py -q

migration-apply:
	python scripts/postgres_migrate.py --target all

lint:
	ruff check .
	ruff format --check .
	$(MAKE) monetary-float-guard

monetary-float-guard:
	python scripts/check_monetary_float_usage.py

format:
	ruff format .

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['__pycache__', '.pytest_cache', 'htmlcov', '.ruff_cache', '.mypy_cache']]; pathlib.Path('.coverage').unlink(missing_ok=True)"

run:
	uvicorn src.api.main:app --reload --port 8000

check-deps:
	python scripts/dependency_health_check.py --requirements requirements.txt

security-audit:
	python scripts/dependency_health_check.py --requirements requirements.txt

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down
