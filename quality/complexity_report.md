# lotus-manage Complexity Report

- Generated at: `2026-10-17T21:38:23+00:00`

- Baseline source snapshot: `3ab121ab9be5821a2602a0ef38c50cbd38206871`

- Report source snapshot: `6da2c5b7+worktree`

- Mode: active Radon function/method non-degradation via `make complexity-gate`; the dependency-free AST branch metrics below remain report-only and are not Radon scores.

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
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 120 | 426 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 89 | 155 |
| 7 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 83 | 145 |
| 8 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

### Most Complex Current Source Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | _turnover_budget_assessment | src/core/mandate_health_scoring.py | 20 | 60 |
| 2 | _resolve_item_payloads | src/api/services/wave_simulation_operations.py | 19 | 67 |
| 3 | _tax_budget_assessment | src/core/mandate_health_scoring.py | 19 | 59 |
| 4 | _validate_summary_invocation_parents | src/infrastructure/pm_quality/in_memory.py | 19 | 50 |
| 5 | _admit_wave_simulation_operation | src/api/services/wave_simulation_operations.py | 17 | 174 |
| 6 | admit_simulation_operation | src/infrastructure/waves/simulation_postgres.py | 17 | 79 |
| 7 | propose | src/api/services/historical_subject_policy.py | 15 | 96 |
| 8 | _resolve_single | src/infrastructure/composites/monthly_evidence.py | 15 | 75 |
| 9 | _load_releaseable_run | src/api/services/instruction_package_application.py | 14 | 39 |
| 10 | propose | src/api/services/composite_monthly_evaluation.py | 13 | 126 |

### Most Complex Current Test Functions

| Rank | Function | File | Complexity | Lines |
| --- | --- | --- | --- | --- |
| 1 | test_rfc0042_gold_standard_tightening_preserves_source_boundaries | tests/unit/test_documentation_current_state.py | 1068 | 1558 |
| 2 | test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts | tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py | 276 | 794 |
| 3 | test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events | tests/unit/dpm/api/test_portfolio_memory_api.py | 146 | 380 |
| 4 | execute | tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py | 120 | 426 |
| 5 | test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery | tests/unit/dpm/api/test_portfolio_memory_api.py | 102 | 231 |
| 6 | test_manage_consumer_declaration_tracks_current_core_inputs | tests/unit/test_domain_data_product_contracts.py | 89 | 155 |
| 7 | test_core_resolver_posts_selector_payload_and_correlation_header | tests/unit/dpm/infrastructure/test_core_sourcing_client.py | 83 | 145 |
| 8 | test_rfc0041_slice0_source_map_guardrails_stay_truthful | tests/unit/test_documentation_current_state.py | 80 | 128 |
| 9 | test_pm_operating_quality_openapi_contract_is_documented | tests/unit/api/test_pm_operating_quality_api.py | 73 | 142 |
| 10 | test_portfolio_memory_api_returns_queryable_source_backed_memory | tests/unit/dpm/api/test_portfolio_memory_api.py | 71 | 334 |

## Gate Posture

- `make complexity-gate` runs `python scripts/complexity_gate.py`: new source functions/methods must have Radon CC <= 10; existing functions/methods above 10 cannot increase against the exact immutable Git baseline. No headroom or allowlist applies.

- Unchanged/improved legacy findings remain explicit measured debt, printed by the gate. Renamed/moved functions are new identities. Class aggregates and maintainability index remain report-only.

- Feature branches compare with the exact resolved `origin/main` tip; pull requests use their actual base-branch tip. A shared ancestor must resolve, but the target tip supplies the scores. Clean main compares with `HEAD^`; main source edits compare with committed HEAD. Recorded report provenance cannot grant stale complexity allowances. Automatic HEAD comparisons require demonstrably different worktree source; explicit self refs are refused. Missing/unresolved/empty baselines, identical-source comparisons, malformed source and scanner failures fail closed. The blocking command writes no artifacts.

- Clean Main audits every first-parent released revision against its predecessor, using the immutable push-before commit or recorded reviewed release baseline. Missing/empty release provenance fails closed; an intermediate new C-rank function cannot be hidden by a later repair. Uncommitted Main comparisons are development proof only.

- Broader source/test complexity rankings in this report remain report-only until baselines, false positives, lane placement, and exception policy are clear.
