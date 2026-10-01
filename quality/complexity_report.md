# lotus-manage Complexity Report

- Generated at: `2026-10-01T14:28:59+00:00`

- Baseline source snapshot: `5240420e2d3d6e470701c108dc5e5e9dead890ff`

- Report source snapshot: `5240420e+worktree`

- Mode: active source C-or-worse gate via `make complexity-gate`; broader dependency-free AST branch metrics remain report-only.

## Summary

| Metric | origin/main | current branch | Delta |
| --- | --- | --- | --- |
| Reported top functions | 10 | 10 | +0 |
| Highest complexity | 1068 | 1068 | +0 |

### Most Complex Current Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1068 | 1558 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 276 | 794 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 119 | 426 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 89 | 153 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 78 | 140 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

### Most Complex Current Source Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | _validate_summary_invocation_parents | src/infrastructure/pm_quality/in_memory.py | 19 | 50 |
| 2 | record_run | src/core/rebalance_runs/service.py | 13 | 99 |
| 3 | _validate_postgres_summary_invocation_parents | src/infrastructure/pm_quality/postgres.py | 13 | 49 |
| 4 | _validate_candidate_source_ref | src/core/waves/campaign_candidate_source_contracts.py | 12 | 70 |
| 5 | _split_sql_statements | src/infrastructure/postgres_migrations.py | 12 | 54 |
| 6 | build | src/core/rebalance_runs/operation_support_bundle.py | 11 | 37 |
| 7 | _validate_review_action_parent | src/infrastructure/pm_quality/in_memory.py | 11 | 35 |
| 8 | _campaign_workflow_labels_for_http_exception | src/api/routers/wave_campaign_workflow_telemetry.py | 11 | 21 |
| 9 | validate_revision_windows_and_hash | src/core/composite_membership.py | 11 | 19 |
| 10 | _scenario_outcomes | src/core/rebalance_runs/operation_support_bundle.py | 10 | 39 |

### Most Complex Current Test Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1068 | 1558 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 276 | 794 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 119 | 426 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 89 | 153 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 78 | 140 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

## Gate Posture

- Source functions at Radon C-or-worse are actively blocked by `make complexity-gate` (`python -m radon cc src -s -n C`).

- Broader source/test complexity rankings in this report remain report-only until baselines, false positives, lane placement, and exception policy are clear.
