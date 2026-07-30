# lotus-manage Complexity Report

- Generated at: `2026-07-30T10:50:13+00:00`

- Baseline source snapshot: `36ff8eeeb55bfaa9f9a02d91f9788e1518c05a50`

- Report source snapshot: `88da9d46+worktree`

- Mode: active source C-or-worse gate via `make complexity-gate`; broader dependency-free AST branch metrics remain report-only.

## Summary

| Metric | origin/main | current branch | Delta |
| --- | --- | --- | --- |
| Reported top functions | 10 | 10 | +0 |
| Highest complexity | 1066 | 1066 | +0 |

### Most Complex Current Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1066 | 1549 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 275 | 774 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 107 | 396 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 78 | 140 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

### Most Complex Current Source Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | _validate_summary_invocation_parents | src/infrastructure/pm_quality/in_memory.py | 19 | 50 |
| 2 | _validate_postgres_summary_invocation_parents | src/infrastructure/pm_quality/postgres.py | 13 | 49 |
| 3 | _validate_candidate_source_ref | src/core/waves/campaign_candidate_source_contracts.py | 12 | 70 |
| 4 | _validate_review_action_parent | src/infrastructure/pm_quality/in_memory.py | 11 | 35 |
| 5 | _campaign_workflow_labels_for_http_exception | src/api/routers/wave_campaign_workflow_telemetry.py | 11 | 21 |
| 6 | _split_sql_statements | src/infrastructure/postgres_migrations.py | 10 | 42 |
| 7 | list_definitions_by_workflow_projection | src/infrastructure/waves/campaign_definitions.py | 9 | 64 |
| 8 | _workflow_projection_matches | src/infrastructure/waves/campaign_definitions.py | 9 | 38 |
| 9 | _validate_postgres_review_action_parent | src/infrastructure/pm_quality/postgres.py | 9 | 36 |
| 10 | build_supportability_summary_response | src/core/rebalance_runs/supportability_summary.py | 8 | 75 |

### Most Complex Current Test Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1066 | 1549 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 275 | 774 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 107 | 396 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 78 | 140 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

## Gate Posture

- Source functions at Radon C-or-worse are actively blocked by `make complexity-gate` (`python -m radon cc src -s -n C`).

- Broader source/test complexity rankings in this report remain report-only until baselines, false positives, lane placement, and exception policy are clear.
