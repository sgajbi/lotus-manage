.PHONY: architecture-gate complexity-gate duplicate-implementation-gate dead-code-gate dependency-hygiene-gate workflow-policy-gate quality-report-gate test-family-inventory coverage-gate static-quality-gates install install-ci check check-all test test-unit test-integration test-e2e test-unit-coverage test-integration-coverage test-e2e-coverage test-all test-fast test-all-fast test-all-no-cov test-all-parallel ci ci-local ci-local-docker ci-local-docker-down typecheck typecheck-tests-critical lint monetary-float-guard domain-product-validate trust-telemetry-validate observability-contract-validate mesh-contract-validate no-alias-gate openapi-gate api-vocabulary-gate service-boundary-gate router-infrastructure-gate live-api-validate live-api-validate-core demo-certify format clean run check-deps security-audit migration-smoke migration-apply pre-commit docker-build docker-image-evidence docker-up docker-down

COVERAGE_FAIL_UNDER ?= 99
IMAGE_NAME ?= lotus-manage
IMAGE_REF ?= $(IMAGE_NAME):$(IMAGE_TAG)
REPO_URL ?= https://github.com/sgajbi/lotus-manage
CI_PIPELINE_ID ?= local
UNIT_TESTS ?= tests/unit
INTEGRATION_TESTS ?= tests/integration
E2E_TESTS ?= tests/e2e

ifeq ($(origin GIT_SHA), undefined)
GIT_SHA := $(shell git rev-parse HEAD)
endif
ifeq ($(origin GIT_BRANCH), undefined)
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
endif
ifeq ($(origin IMAGE_TAG), undefined)
IMAGE_TAG := $(shell git rev-parse --short HEAD)
endif
ifeq ($(origin BUILD_TIMESTAMP), undefined)
BUILD_TIMESTAMP := $(shell python -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))")
endif

install:
	python -m pip install --upgrade pip
	pip install -e ".[dev,quality]"
	pre-commit install

install-ci:
	python -m pip install --upgrade pip
	pip install -e ".[dev,quality]"

pre-commit:
	pre-commit run --all-files

static-quality-gates: lint no-alias-gate typecheck typecheck-tests-critical openapi-gate api-vocabulary-gate \
	service-boundary-gate router-infrastructure-gate mesh-contract-validate architecture-gate complexity-gate \
	duplicate-implementation-gate dependency-hygiene-gate dead-code-gate workflow-policy-gate quality-report-gate \
	test-family-inventory

check: static-quality-gates test

ci: static-quality-gates migration-smoke test-all security-audit

test:
	$(MAKE) test-unit

test-unit:
	python -m pytest $(UNIT_TESTS)

test-integration:
	python -m pytest $(INTEGRATION_TESTS)

test-e2e:
	python -m pytest $(E2E_TESTS)

test-unit-coverage:
	python -m pytest $(UNIT_TESTS) --cov=src --cov-report=

test-integration-coverage:
	python -m pytest $(INTEGRATION_TESTS) --cov=src --cov-report=

test-e2e-coverage:
	python -m pytest $(E2E_TESTS) --cov=src --cov-report=

test-all:
	python -m pytest --cov=src --cov-report=term-missing
	python scripts/coverage_gate.py --coverage-file .coverage --fail-under $(COVERAGE_FAIL_UNDER)

# Fast local loop: unit tests only (no coverage)
test-fast:
	python -m pytest tests/unit -q

# Full suite with coverage gate, but without term-missing output overhead
test-all-fast:
	python -m pytest --cov=src --cov-report=
	python scripts/coverage_gate.py --coverage-file .coverage --fail-under $(COVERAGE_FAIL_UNDER)

# Full suite without coverage for quickest full functional signal
test-all-no-cov:
	python -m pytest

# Full suite, optional parallel workers when pytest-xdist is installed
test-all-parallel:
	python -c "import importlib.util, subprocess, sys; args=[sys.executable,'-m','pytest','--cov=src','--cov-report=']; args += (['-n','auto','--dist','loadscope'] if importlib.util.find_spec('xdist') else []); raise SystemExit(subprocess.call(args))"
	python scripts/coverage_gate.py --coverage-file .coverage --fail-under $(COVERAGE_FAIL_UNDER)

# Local execution flow aligned with the Pull Request Merge Gate workflow
ci-local: static-quality-gates check-deps
	COVERAGE_FILE=.coverage.unit $(MAKE) test-unit-coverage
	COVERAGE_FILE=.coverage.integration $(MAKE) test-integration-coverage
	COVERAGE_FILE=.coverage.e2e $(MAKE) test-e2e-coverage
	$(MAKE) coverage-gate

ci-local-docker:
	docker compose -f docker-compose.ci-local.yml up --build --abort-on-container-exit --exit-code-from ci-local ci-local

ci-local-docker-down:
	docker compose -f docker-compose.ci-local.yml down -v --remove-orphans

check-all: lint typecheck test-all

typecheck:
	python -m mypy --config-file mypy.ini

typecheck-tests-critical:
	python -m mypy tests/unit/core/test_capabilities.py tests/unit/dpm/engine/test_engine_workflow_gates.py

openapi-gate:
	python scripts/openapi_quality_gate.py

no-alias-gate:
	python scripts/no_alias_contract_guard.py

api-vocabulary-gate:
	python scripts/api_vocabulary_inventory.py --validate-only

service-boundary-gate:
	python scripts/service_boundary_gate.py

router-infrastructure-gate:
	python scripts/router_infrastructure_gate.py

live-api-validate:
	python scripts/validate_live_api.py --base-url $${LOTUS_MANAGE_BASE_URL:-http://127.0.0.1:8001}

live-api-validate-core:
	python scripts/validate_live_api.py --base-url $${LOTUS_MANAGE_BASE_URL:-http://manage.dev.lotus} --skip-demo-pack --core-base-url $${LOTUS_CORE_CONTROL_BASE_URL:-http://core-control.dev.lotus} --core-base-url $${LOTUS_CORE_QUERY_BASE_URL:-http://core-query.dev.lotus} --expect-core-dpm-route $${LOTUS_MANAGE_EXPECT_CORE_DPM_ROUTE:-absent} --expect-stateful-core-sourcing $${LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING:-available} --portfolio-id $${LOTUS_MANAGE_CANONICAL_PORTFOLIO_ID:-PB_SG_GLOBAL_BAL_001} --as-of $${LOTUS_MANAGE_CANONICAL_AS_OF:-2026-04-10}

demo-certify:
	python scripts/validate_live_api.py --base-url $${LOTUS_MANAGE_BASE_URL:-http://manage.dev.lotus} --skip-demo-pack --core-base-url $${LOTUS_CORE_CONTROL_BASE_URL:-http://core-control.dev.lotus} --core-base-url $${LOTUS_CORE_QUERY_BASE_URL:-http://core-query.dev.lotus} --expect-core-dpm-route $${LOTUS_MANAGE_EXPECT_CORE_DPM_ROUTE:-absent} --expect-stateful-core-sourcing $${LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING:-available} --portfolio-id $${LOTUS_MANAGE_CANONICAL_PORTFOLIO_ID:-PB_SG_GLOBAL_BAL_001} --as-of $${LOTUS_MANAGE_CANONICAL_AS_OF:-2026-04-10} --json-output $${LOTUS_MANAGE_DEMO_CERT_OUTPUT:-output/live-api/demo-certification/summary.json}

migration-smoke:
	python -m pytest tests/unit/shared/dependencies/test_postgres_migrations.py tests/unit/shared/dependencies/test_production_cutover_contract.py -q

migration-apply:
	python scripts/postgres_migrate.py --target dpm

lint:
	python -m ruff check .
	python -m ruff format --check .
	$(MAKE) monetary-float-guard

architecture-gate:
	python -m importlinter.cli import-linter lint --config .importlinter
complexity-gate:
	python -m radon cc src -s -n C
	python -m radon mi src -s

duplicate-implementation-gate:
	python scripts/duplicate_implementation_gate.py

dependency-hygiene-gate:
	python -m deptry src tests

dead-code-gate:
	python -m vulture src tests --min-confidence 80

workflow-policy-gate:
	python scripts/workflow_policy_gate.py

quality-report-gate:
	python scripts/engineering_health_report.py --check

test-family-inventory:
	python scripts/test_family_inventory.py --check

coverage-gate:
	python scripts/coverage_gate.py --fail-under $(COVERAGE_FAIL_UNDER)


monetary-float-guard:
	python scripts/check_monetary_float_usage.py

domain-product-validate:
	python scripts/validate_domain_data_product_contracts.py

trust-telemetry-validate:
	python scripts/validate_trust_telemetry_contracts.py

observability-contract-validate:
	python scripts/validate_observability_contracts.py

mesh-contract-validate: domain-product-validate trust-telemetry-validate observability-contract-validate

format:
	python -m ruff format .

clean:
	python scripts/clean_generated_artifacts.py

run:
	uvicorn src.api.main:app --reload --port 8000

run-canonical:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001

check-deps:
	python -m pip check

security-audit:
	# PYSEC-2024-277 / CVE-2024-34997 is a disputed joblib trusted-cache
	# deserialization advisory with no fixed release in the current audit feed.
	# PYSEC-2022-42969 / py<1.11.1 has a CVSS 8.2 vulnerability in py package APIs.
	# py is pulled transitively by test dependencies and currently has no direct fix path.
	python -m bandit -q -r src -c pyproject.toml --severity-level high
	python -m pip_audit . --ignore-vuln PYSEC-2024-277 --ignore-vuln PYSEC-2022-42969

docker-build:
	docker build \
		--build-arg GIT_SHA=$(GIT_SHA) \
		--build-arg GIT_BRANCH=$(GIT_BRANCH) \
		--build-arg BUILD_TIMESTAMP=$(BUILD_TIMESTAMP) \
		--build-arg REPO_URL=$(REPO_URL) \
		--build-arg IMAGE_DIGEST=local-build-pending-push \
		--build-arg CI_PIPELINE_ID=$(CI_PIPELINE_ID) \
		--build-arg APP_VERSION=0.1.0 \
		-t $(IMAGE_REF) \
		-t lotus-manage:ci .

docker-image-evidence: docker-build
	python scripts/docker_image_evidence.py \
		--image $(IMAGE_REF) \
		--git-sha $(GIT_SHA) \
		--git-branch $(GIT_BRANCH) \
		--build-timestamp $(BUILD_TIMESTAMP) \
		--repo-url $(REPO_URL) \
		--ci-pipeline-id $(CI_PIPELINE_ID)

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

