# lotus-manage Refactor Health Report

- Generated at: `2026-07-13T13:46:14+00:00`

- Baseline ref: `origin/main`

- Baseline source snapshot: `a47d377f6b29bd475ca60bd51ff2f21a29fa556b`

- Report source snapshot: `2fc0f46b+worktree`

- Scope: Python code under `src/`, `tests/`, and `scripts/`; current OpenAPI schema.

## Scorecard

| Metric | origin/main | current branch | Delta |
| --- | --- | --- | --- |
| Python files | 894 | 896 | +2 |
| Total Python LOC | 193019 | 201877 | +8858 |
| Test functions | 2822 | 2888 | +66 |
| Service boundary findings | 0 | 0 | +0 |
| Router infrastructure imports | 0 | 0 | +0 |

## Current OpenAPI Completeness

| Metric | Current |
| --- | --- |
| Operations | 137 |
| Missing summary | 0 |
| Missing description | 0 |
| Missing tags | 0 |
| Missing 4xx/5xx response | 1 |
| Missing examples marker | 0 |

## Largest Files

### origin/main

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 7324 |
| 2 | tests/unit/dpm/api/test_api_rebalance.py | 3323 |
| 3 | tests/unit/dpm/proof_packs/test_proof_pack_builder.py | 3289 |
| 4 | tests/unit/dpm/waves/test_campaign_discovery.py | 3214 |
| 5 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 3122 |
| 6 | tests/unit/test_documentation_current_state.py | 2771 |
| 7 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2665 |
| 8 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2649 |
| 9 | tests/unit/core/test_risk_realized_outcome_sources.py | 1811 |
| 10 | tests/unit/api/test_pm_operating_quality_api.py | 1745 |

### current branch

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 7505 |
| 2 | tests/unit/dpm/api/test_api_rebalance.py | 3323 |
| 3 | tests/unit/dpm/proof_packs/test_proof_pack_builder.py | 3289 |
| 4 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 3283 |
| 5 | tests/unit/dpm/waves/test_campaign_discovery.py | 3215 |
| 6 | tests/unit/test_documentation_current_state.py | 2774 |
| 7 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2689 |
| 8 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2665 |
| 9 | tests/unit/api/test_pm_operating_quality_api.py | 2203 |
| 10 | tests/unit/dpm/pm_quality/test_pm_operating_quality.py | 1996 |

## Largest Functions

### origin/main

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 773 |
| 3 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 383 |
| 4 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 376 |
| 5 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 6 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 7 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 328 |
| 8 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 9 | test_wave_openapi_pins_campaign_workflow_assignment_and_automation_contracts | tests/unit/dpm/api/test_waves_api.py | 268 |
| 10 | test_rolling_and_historical_attribution_helper_edges_are_explicit | tests/unit/core/test_risk_realized_outcome_sources.py | 236 |

### current branch

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1549 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 773 |
| 3 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 396 |
| 4 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 380 |
| 5 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 6 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 7 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 334 |
| 8 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 9 | test_wave_openapi_pins_campaign_workflow_assignment_and_automation_contracts | tests/unit/dpm/api/test_waves_api.py | 268 |
| 10 | test_rolling_and_historical_attribution_helper_edges_are_explicit | tests/unit/core/test_risk_realized_outcome_sources.py | 236 |

## Most Complex Functions

### origin/main

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1063 | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 274 | 773 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 376 |
| 4 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 230 |
| 5 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 96 | 383 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 78 | 140 |
| 9 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 328 |
| 10 | test_wave_openapi_documents_preview_and_create | tests/unit/dpm/api/test_waves_api.py | 68 | 209 |

### current branch

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1066 | 1549 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 274 | 773 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 107 | 396 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 78 | 140 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

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
