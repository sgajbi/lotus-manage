# lotus-manage Refactor Health Report

- Generated at: `2026-06-01T23:17:06+00:00`

- Baseline ref: `origin/main`

- Current ref: `6bffc2e`

- Scope: Python code under `src/`, `tests/`, and `scripts/`; current OpenAPI schema.

## Scorecard

| Metric | origin/main | current branch | Delta |
| --- | --- | --- | --- |
| Python files | 754 | 767 | +13 |
| Total Python LOC | 144347 | 145857 | +1510 |
| Test functions | 1834 | 1856 | +22 |
| Service boundary findings | 0 | 0 | +0 |
| Router infrastructure imports | 18 | 18 | +0 |

## Current OpenAPI Completeness

| Metric | Current |
| --- | --- |
| Operations | 135 |
| Missing summary | 0 |
| Missing description | 0 |
| Missing tags | 0 |
| Missing 4xx/5xx response | 3 |
| Missing examples marker | 0 |

## Largest Files

### origin/main

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 6399 |
| 2 | tests/unit/dpm/api/test_api_rebalance.py | 3318 |
| 3 | tests/unit/test_documentation_current_state.py | 2721 |
| 4 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2600 |
| 5 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2461 |
| 6 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 2099 |
| 7 | tests/unit/dpm/waves/test_campaign_discovery.py | 1887 |
| 8 | src/core/dpm_source_context.py | 1878 |
| 9 | tests/unit/dpm/api/test_construction_api.py | 1667 |
| 10 | src/infrastructure/core_sourcing/client.py | 1639 |

### current branch

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 6402 |
| 2 | tests/unit/dpm/api/test_api_rebalance.py | 3318 |
| 3 | tests/unit/test_documentation_current_state.py | 2721 |
| 4 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2600 |
| 5 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2461 |
| 6 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 2099 |
| 7 | tests/unit/dpm/waves/test_campaign_discovery.py | 1887 |
| 8 | src/core/dpm_source_context.py | 1878 |
| 9 | tests/unit/dpm/api/test_construction_api.py | 1667 |
| 10 | src/infrastructure/core_sourcing/client.py | 1639 |

## Largest Functions

### origin/main

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 754 |
| 3 | _section_payload | src/core/proof_packs/builder.py | 465 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 382 |
| 5 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 376 |
| 6 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 7 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 8 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 328 |
| 9 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 10 | generate_intents | src/core/rebalance/intents.py | 236 |

### current branch

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 754 |
| 3 | _section_payload | src/core/proof_packs/builder.py | 465 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 382 |
| 5 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 376 |
| 6 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 7 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 8 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 328 |
| 9 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 10 | generate_intents | src/core/rebalance/intents.py | 236 |

## Boundary Findings

### Service boundary findings (origin/main)

No findings.


### Service boundary findings (current branch)

No findings.


### Router infrastructure imports (origin/main)

- `src/api/routers/construction_generate_routes.py:25: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/mandate_refresh_routes.py:24: from src.infrastructure.core_sourcing import DpmCoreResolverClient`
- `src/api/routers/mandates.py:7: from src.infrastructure.core_sourcing import DpmCoreResolverClient`
- `src/api/routers/monitoring.py:7: from src.infrastructure.core_sourcing import DpmCoreResolverClient`
- `src/api/routers/monitoring_http.py:7: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/monitoring_run_once_routes.py:25: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/pm_operating_quality_book_scope_builder.py:24: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/pm_operating_quality_http.py:13: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/wave_core_portfolio_universe_resolution.py:19: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/wave_core_source_resolution.py:22: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/wave_create_preview_http.py:12: from src.infrastructure.advise_authority import LotusAdviseAuthorityClient`
- `src/api/routers/wave_create_preview_http.py:13: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/wave_create_preview_routes.py:28: from src.infrastructure.advise_authority import LotusAdviseAuthorityClient`
- `src/api/routers/wave_create_preview_routes.py:29: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/wave_portfolio_resolution.py:38: from src.infrastructure.advise_authority import (`
- `src/api/routers/wave_portfolio_resolution.py:42: from src.infrastructure.risk_authority import (`
- `src/api/routers/wave_simulation_http.py:14: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/wave_simulation_routes.py:18: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`


### Router infrastructure imports (current branch)

- `src/api/routers/construction_generate_routes.py:25: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/mandate_refresh_routes.py:24: from src.infrastructure.core_sourcing import DpmCoreResolverClient`
- `src/api/routers/mandates.py:7: from src.infrastructure.core_sourcing import DpmCoreResolverClient`
- `src/api/routers/monitoring.py:7: from src.infrastructure.core_sourcing import DpmCoreResolverClient`
- `src/api/routers/monitoring_http.py:7: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/monitoring_run_once_routes.py:25: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/pm_operating_quality_book_scope_builder.py:24: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/pm_operating_quality_http.py:13: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/wave_core_portfolio_universe_resolution.py:19: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/wave_core_source_resolution.py:22: from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError`
- `src/api/routers/wave_create_preview_http.py:12: from src.infrastructure.advise_authority import LotusAdviseAuthorityClient`
- `src/api/routers/wave_create_preview_http.py:13: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/wave_create_preview_routes.py:28: from src.infrastructure.advise_authority import LotusAdviseAuthorityClient`
- `src/api/routers/wave_create_preview_routes.py:29: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/wave_portfolio_resolution.py:38: from src.infrastructure.advise_authority import (`
- `src/api/routers/wave_portfolio_resolution.py:42: from src.infrastructure.risk_authority import (`
- `src/api/routers/wave_simulation_http.py:14: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`
- `src/api/routers/wave_simulation_routes.py:18: from src.infrastructure.risk_authority import LotusRiskAuthorityClient`


## Notes

- This report is intentionally dependency-free and repeatable in local and CI environments.

- It is a first measurable baseline; future phases can add radon, vulture, deptry, bandit, pip-audit, Spectral, import-linter, and coverage thresholds.
