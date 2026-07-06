# lotus-manage Complexity Report

- Generated at: `2026-07-06T00:31:21+00:00`

- Baseline source snapshot: `46dbf0ff47bfa2afbfdfc4560e637cbff42af940`

- Report source snapshot: `6e51ba03+worktree`

- Mode: active source C-or-worse gate via `make complexity-gate`; broader dependency-free AST branch metrics remain report-only.

## Summary

| Metric | origin/main | current branch | Delta |
| --- | --- | --- | --- |
| Reported top functions | 10 | 10 | +0 |
| Highest complexity | 1063 | 1063 | +0 |

### Most Complex Current Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1063 | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 274 | 773 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 376 |
| 4 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 230 |
| 5 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 96 | 383 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 72 | 133 |
| 9 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 328 |
| 10 | test_wave_openapi_documents_preview_and_create | tests/unit/dpm/api/test_waves_api.py | 68 | 209 |

### Most Complex Current Source Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | _campaign_workflow_labels_for_http_exception | src/api/routers/wave_campaign_workflow_telemetry.py | 11 | 21 |
| 2 | launch_bulk_review_campaign_definition_response | src/api/routers/wave_campaign_launch_http.py | 9 | 88 |
| 3 | list_definitions_by_workflow_projection | src/infrastructure/waves/campaign_definitions.py | 9 | 62 |
| 4 | build_supportability_summary_response | src/core/rebalance_runs/supportability_summary.py | 9 | 59 |
| 5 | _workflow_projection_matches | src/infrastructure/waves/campaign_definitions.py | 9 | 38 |
| 6 | _control_lifecycle_state | src/core/waves/campaign_maker_checker_controls.py | 7 | 43 |
| 7 | _operation_request_portfolio_id | src/infrastructure/rebalance_runs/in_memory_helpers.py | 7 | 20 |
| 8 | _record_active_definition_update | src/infrastructure/waves/campaign_definitions.py | 6 | 58 |
| 9 | resolve_freshness_bucket | src/core/rebalance_runs/supportability_summary.py | 6 | 27 |
| 10 | validate_campaign_command_actor_entitlement | src/core/waves/campaign_actor_entitlements.py | 6 | 15 |

### Most Complex Current Test Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1063 | 1546 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 274 | 773 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 376 |
| 4 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 230 |
| 5 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 96 | 383 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 72 | 133 |
| 9 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 328 |
| 10 | test_wave_openapi_documents_preview_and_create | tests/unit/dpm/api/test_waves_api.py | 68 | 209 |

## Gate Posture

- Source functions at Radon C-or-worse are actively blocked by `make complexity-gate` (`python -m radon cc src -s -n C`).

- Broader source/test complexity rankings in this report remain report-only until baselines, false positives, lane placement, and exception policy are clear.
