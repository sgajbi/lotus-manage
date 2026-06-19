# lotus-manage Duplicate Implementation Inventory

- Detector: exact normalized Python function-body duplicates.
- Scope: `src, scripts`.
- Minimum function size: `8` lines.
- Gate posture: active non-regression gate via `make duplicate-implementation-gate`; existing groups are explicitly baselined and future exact duplicate groups fail.

## Current Duplicate Groups

### Group 1

- Fingerprint: `317ca65810972045193f59d164afab794958f3bcb2d4e3dc50f5142cca03d15f`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/api/routers/runtime_utils.py` | `postgres_connection_exception_types` | 46 | 12 |
| `src/api/services/rebalance_policy_pack_repository.py` | `postgres_connection_exception_types` | 27 | 12 |
| `src/api/services/rebalance_run_support_repository.py` | `postgres_connection_exception_types` | 23 | 12 |

### Group 2

- Fingerprint: `32cba6c2f7cace3a0498797762fed88ee0f97d1e34b9533204cd7ae766fcca78`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/core/portfolio_memory/models.py` | `_portfolio_memory_supportability_state` | 1279 | 10 |
| `src/core/portfolio_memory/supportability.py` | `portfolio_memory_state` | 14 | 10 |

### Group 3

- Fingerprint: `3bcc7cf6f60fca55c4be481bcafefe56cb4e893206e780f08778de34a32808da`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_approval_decision` | 491 | 47 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_assignment_action` | 539 | 47 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_assignment_task` | 635 | 47 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_launch` | 443 | 47 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_maker_checker_control` | 587 | 47 |

### Group 4

- Fingerprint: `676e5772d69cbaf2dc95a2b328572fe21700d12b87acdd5f16e6ab84dbb5e22b`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/api/routers/rebalance_runs_workflow_decision_routes.py` | `get_dpm_workflow_decisions_by_correlation` | 150 | 17 |
| `src/api/routers/rebalance_runs_workflow_history_routes.py` | `get_dpm_run_workflow_history_by_correlation` | 66 | 17 |

### Group 5

- Fingerprint: `7d6fe32652673c07585310d95a88ecbcc35c2a3131810826bc2cad7402bddd44`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/api/routers/pm_operating_quality_book_scope_builder.py` | `_pm_book_member_source_refs` | 118 | 12 |
| `src/api/services/pm_operating_quality_service.py` | `_pm_book_member_source_refs` | 224 | 12 |

### Group 6

- Fingerprint: `847ede373a8c35ca9ffc13af638fafc6d1c8133fa7656e09e7f086ef3cd36b2c`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `scripts/generate_rfc0041_wave_evidence.py` | `_request` | 46 | 16 |
| `scripts/generate_rfc0042_outcome_evidence.py` | `_request` | 46 | 16 |

### Group 7

- Fingerprint: `955f5589fc5bc3cf7cf06477bce4261c3e2ca57ec2b9fb1661e4fae54b0d7904`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/core/portfolio_memory/models.py` | `_event_source_systems` | 1267 | 10 |
| `src/core/portfolio_memory/search_filters.py` | `event_source_systems` | 61 | 10 |

### Group 8

- Fingerprint: `97f605e668b3d05093526f1e085ef07f8ed6b806e764a84b6ee5e2886e810cf6`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/infrastructure/rebalance_runs/in_memory.py` | `create_operation` | 509 | 10 |
| `src/infrastructure/rebalance_runs/in_memory.py` | `update_operation` | 520 | 10 |

### Group 9

- Fingerprint: `99c928e5d1a1afc97bb9eaf92df49d4e16bc841f67d00b1e2eb0dbe82e5be389`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/infrastructure/rebalance_runs/postgres.py` | `create_operation` | 301 | 9 |
| `src/infrastructure/rebalance_runs/postgres.py` | `update_operation` | 311 | 9 |

### Group 10

- Fingerprint: `de1163a135da66d809e4c3d60216165ef9c6080e3e6873225f1705165c9cd8d0`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_approval_decision` | 136 | 18 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_assignment_action` | 155 | 18 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_assignment_task` | 174 | 18 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_launch` | 117 | 18 |
| `src/infrastructure/waves/campaign_definitions.py` | `record_definition_maker_checker_control` | 193 | 18 |
