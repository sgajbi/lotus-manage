# lotus-manage Complexity Report

- Generated at: `2026-06-27T06:14:34+00:00`

- Baseline source snapshot: `380d5f1b70c539fa583f39af8303c4298bdbf291`

- Report source snapshot: `380d5f1b+worktree`

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
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 274 | 754 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 376 |
| 4 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 100 | 221 |
| 5 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 95 | 382 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 87 | 148 |
| 7 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 8 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 72 | 133 |
| 9 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 328 |
| 10 | test_wave_read_apis_return_durable_search_detail_items_and_proof_pack_posture | tests/unit/dpm/api/test_waves_api.py | 66 | 220 |

### Most Complex Current Source Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | resolve_freshness_bucket | src/core/rebalance_runs/supportability_summary.py | 6 | 27 |
| 2 | run_simulation | src/core/rebalance/engine.py | 5 | 145 |
| 3 | pm_quality_summary_invocation_event | src/core/portfolio_memory/pm_quality_projection.py | 5 | 100 |
| 4 | resolve_bulk_review_campaign_portfolios | src/api/routers/wave_campaign_source_resolution.py | 5 | 83 |
| 5 | generate_fx_and_simulate | src/core/rebalance/execution.py | 5 | 81 |
| 6 | _source_lineage | src/core/outcomes/snapshots.py | 5 | 75 |
| 7 | build_mandate_refresh_result_from_core | src/api/services/mandate_refresh.py | 5 | 74 |
| 8 | collect_portfolio_memory_events | src/core/portfolio_memory/source_collection.py | 5 | 73 |
| 9 | compile_mandate_digital_twin_from_core | src/core/mandates.py | 5 | 69 |
| 10 | mandate_context_section_payload | src/core/proof_packs/mandate_context.py | 5 | 67 |

### Most Complex Current Test Functions

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

## Gate Posture

- Source functions at Radon C-or-worse are actively blocked by `make complexity-gate` (`python -m radon cc src -s -n C`).

- Broader source/test complexity rankings in this report remain report-only until baselines, false positives, lane placement, and exception policy are clear.
