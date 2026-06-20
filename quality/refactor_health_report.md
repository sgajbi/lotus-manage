# lotus-manage Refactor Health Report

- Generated at: `2026-06-20T01:18:12+00:00`

- Baseline ref: `origin/main`

- Report source snapshot: `2643af7b+worktree`

- Scope: Python code under `src/`, `tests/`, and `scripts/`; current OpenAPI schema.

## Scorecard

| Metric | origin/main | current branch | Delta |
| --- | --- | --- | --- |
| Python files | 878 | 878 | +0 |
| Total Python LOC | 185387 | 185475 | +88 |
| Test functions | 2745 | 2748 | +3 |
| Service boundary findings | 0 | 0 | +0 |
| Router infrastructure imports | 0 | 0 | +0 |

## Current OpenAPI Completeness

| Metric | Current |
| --- | --- |
| Operations | 135 |
| Missing summary | 0 |
| Missing description | 0 |
| Missing tags | 0 |
| Missing 4xx/5xx response | 0 |
| Missing examples marker | 0 |

## Largest Files

### origin/main

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 6408 |
| 2 | tests/unit/dpm/api/test_api_rebalance.py | 3318 |
| 3 | tests/unit/dpm/proof_packs/test_proof_pack_builder.py | 3289 |
| 4 | tests/unit/dpm/waves/test_campaign_discovery.py | 2960 |
| 5 | tests/unit/test_documentation_current_state.py | 2721 |
| 6 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2600 |
| 7 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2531 |
| 8 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 2489 |
| 9 | tests/unit/core/test_risk_realized_outcome_sources.py | 1811 |
| 10 | tests/unit/api/test_pm_operating_quality_api.py | 1745 |

### current branch

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 6408 |
| 2 | tests/unit/dpm/api/test_api_rebalance.py | 3318 |
| 3 | tests/unit/dpm/proof_packs/test_proof_pack_builder.py | 3289 |
| 4 | tests/unit/dpm/waves/test_campaign_discovery.py | 2960 |
| 5 | tests/unit/test_documentation_current_state.py | 2721 |
| 6 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2600 |
| 7 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2531 |
| 8 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 2489 |
| 9 | tests/unit/core/test_risk_realized_outcome_sources.py | 1811 |
| 10 | tests/unit/api/test_pm_operating_quality_api.py | 1745 |

## Largest Functions

### origin/main

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 754 |
| 3 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 382 |
| 4 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 376 |
| 5 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 6 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 7 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 328 |
| 8 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 9 | test_rolling_and_historical_attribution_helper_edges_are_explicit | tests/unit/core/test_risk_realized_outcome_sources.py | 236 |
| 10 | test_source_context_lifts_external_hedge_readiness_as_fail_closed_currency_context | tests/unit/dpm/construction/test_enrichment.py | 235 |

### current branch

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 754 |
| 3 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 382 |
| 4 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 376 |
| 5 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 6 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 7 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 328 |
| 8 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 9 | test_rolling_and_historical_attribution_helper_edges_are_explicit | tests/unit/core/test_risk_realized_outcome_sources.py | 236 |
| 10 | test_source_context_lifts_external_hedge_readiness_as_fail_closed_currency_context | tests/unit/dpm/construction/test_enrichment.py | 235 |

## Most Complex Functions

### origin/main

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1063 | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 274 | 754 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 376 |
| 4 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 100 | 221 |
| 5 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 95 | 382 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 72 | 133 |
| 9 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 328 |
| 10 | test_wave_read_apis_return_durable_search_detail_items_and_proof_pack_posture | tests/unit/dpm/api/test_waves_api.py | 66 | 220 |

### current branch

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1063 | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 274 | 754 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 376 |
| 4 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 100 | 221 |
| 5 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 95 | 382 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 72 | 133 |
| 9 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 328 |
| 10 | test_wave_read_apis_return_durable_search_detail_items_and_proof_pack_posture | tests/unit/dpm/api/test_waves_api.py | 66 | 220 |

## Boundary Findings

### Service boundary findings (origin/main)

No findings.


### Service boundary findings (current branch)

No findings.


### Router infrastructure imports (origin/main)

No findings.


### Router infrastructure imports (current branch)

No findings.


## Notes

- This report is intentionally dependency-free and repeatable in local and CI environments.

- It is a first measurable baseline; future phases can add radon, vulture, deptry, bandit, pip-audit, Spectral, import-linter, and coverage thresholds.
