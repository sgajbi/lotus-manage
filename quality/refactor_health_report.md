# lotus-manage Refactor Health Report

- Generated at: `2026-09-07T01:29:30+00:00`

- Baseline ref: `origin/main`

- Baseline source snapshot: `d0b56d92005132cf21d97a65e20e75bd13b414e7`

- Report source snapshot: `77330783`

- Scope: Python code under `src/`, `tests/`, and `scripts/`; current OpenAPI schema.

## Scorecard

| Metric | origin/main | current branch | Delta |
| --- | --- | --- | --- |
| Python files | 919 | 921 | +2 |
| Total Python LOC | 214106 | 215136 | +1030 |
| Test functions | 3114 | 3119 | +5 |
| Service boundary findings | 0 | 0 | +0 |
| Router infrastructure imports | 0 | 0 | +0 |

## Current OpenAPI Completeness

| Metric | Current |
| --- | --- |
| Operations | 140 |
| Missing summary | 0 |
| Missing description | 0 |
| Missing tags | 0 |
| Missing 4xx/5xx response | 1 |
| Missing examples marker | 0 |

## Largest Files

### origin/main

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 7624 |
| 2 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 3609 |
| 3 | tests/unit/test_ci_workflow_gate_enforcement.py | 3386 |
| 4 | tests/unit/dpm/api/test_api_rebalance.py | 3329 |
| 5 | tests/unit/dpm/proof_packs/test_proof_pack_builder.py | 3289 |
| 6 | tests/unit/dpm/waves/test_campaign_discovery.py | 3215 |
| 7 | tests/unit/test_documentation_current_state.py | 2788 |
| 8 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2689 |
| 9 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2670 |
| 10 | tests/unit/api/test_pm_operating_quality_api.py | 2308 |

### current branch

| Rank | File | Lines |
| --- | --- | --- |
| 1 | tests/unit/dpm/api/test_waves_api.py | 7671 |
| 2 | tests/unit/dpm/waves/test_campaign_definition_repository.py | 3609 |
| 3 | tests/unit/test_ci_workflow_gate_enforcement.py | 3386 |
| 4 | tests/unit/dpm/api/test_api_rebalance.py | 3329 |
| 5 | tests/unit/dpm/proof_packs/test_proof_pack_builder.py | 3289 |
| 6 | tests/unit/dpm/waves/test_campaign_discovery.py | 3215 |
| 7 | tests/unit/test_documentation_current_state.py | 2788 |
| 8 | tests/unit/dpm/api/test_portfolio_memory_api.py | 2706 |
| 9 | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 2670 |
| 10 | tests/unit/api/test_pm_operating_quality_api.py | 2308 |

## Largest Functions

### origin/main

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1558 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 774 |
| 3 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 396 |
| 4 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 380 |
| 5 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 6 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 7 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 334 |
| 8 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 9 | test_wave_openapi_pins_campaign_workflow_assignment_and_automation_contracts | tests/unit/dpm/api/test_waves_api.py | 268 |
| 10 | test_dpm_supportability_and_async_schemas_have_descriptions_and_examples | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 237 |

### current branch

| Rank | Function | File | Lines |
| --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1558 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 791 |
| 3 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 396 |
| 4 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 380 |
| 5 | _core_execution_context | tests/unit/dpm/api/test_construction_api.py | 354 |
| 6 | _generate_wave_lifecycle | scripts/generate_rfc0041_wave_evidence.py | 350 |
| 7 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 334 |
| 8 | run_demo_pack | scripts/run_demo_pack_live.py | 302 |
| 9 | test_wave_openapi_pins_campaign_workflow_assignment_and_automation_contracts | tests/unit/dpm/api/test_waves_api.py | 268 |
| 10 | test_dpm_supportability_and_async_schemas_have_descriptions_and_examples | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 237 |

## Most Complex Functions

### origin/main

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1068 | 1558 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 275 | 774 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 107 | 396 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 89 | 153 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 78 | 140 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

### current branch

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1068 | 1558 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 275 | 791 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 107 | 396 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 89 | 153 |
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
