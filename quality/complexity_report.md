# lotus-manage Complexity Report

- Generated at: `2026-06-02T00:47:32+00:00`

- Current ref: `3ef0c62`

- Mode: report-only maintainability baseline using dependency-free AST branch counting.

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
| 1 | generate_intents | src/core/rebalance/intents.py | 38 | 207 |
| 2 | external_treasury_currency_overlay_context | src/api/services/construction_treasury_source_context.py | 30 | 164 |
| 3 | validate_definition | src/core/waves/campaign_definitions.py | 30 | 69 |
| 4 | build_search_row | src/core/portfolio_memory/search_page.py | 28 | 86 |
| 5 | compile_mandate_digital_twin_from_core | src/core/mandates.py | 26 | 182 |
| 6 | generate_fx_and_simulate | src/core/rebalance/execution.py | 26 | 167 |
| 7 | _section_payload | src/core/proof_packs/builder.py | 22 | 130 |
| 8 | generate_targets_heuristic | src/core/rebalance/targets.py | 22 | 74 |
| 9 | _infer_example | src/api/openapi_enrichment.py | 22 | 48 |
| 10 | summarize_enrichment_posture | src/core/construction/enrichment.py | 21 | 89 |

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

- This report is phase 1/report-only. It intentionally does not fail builds until the baseline is reviewed and thresholds are agreed.
