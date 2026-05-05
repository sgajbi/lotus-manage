# RFC-0042 Slice 3 - Domain Model and Pure Comparison Engine

| Field | Value |
| --- | --- |
| **RFC** | RFC-0042 Post-Trade Outcome Feedback Loop |
| **Slice** | Slice 3 - Domain Model and Pure Comparison Engine |
| **Implementation Branch** | `feat/rfc0042-implementation` |
| **Date** | 2026-05-05 |
| **Status** | DONE |

---

## Implemented Scope

Slice 3 adds the pure RFC-0042 outcome-review domain boundary:

1. `src/core/outcomes/models.py` defines typed Pydantic contracts for source refs, freshness,
   supportability, metric values, tolerances, dimension inputs, dimension results, review comparison
   roll-up, and append-only outcome events.
2. `src/core/outcomes/comparison.py` implements deterministic expected-versus-realized comparison
   over supplied snapshots only.
3. `src/core/outcomes/__init__.py` exports the domain primitives without coupling them to APIs,
   persistence, source clients, reports, AI, or Workbench.
4. `tests/unit/core/test_outcome_comparison.py` validates tolerance behavior, state transitions,
   source-degraded and blocked behavior, unsupported-dimension guardrails, state roll-up precedence,
   and validation of invalid tolerance configuration.

## Boundaries Enforced

1. The comparator does not call `lotus-core`, `lotus-risk`, `lotus-performance`, Gateway, Workbench,
   report, or AI services.
2. The comparator does not calculate source-owner truth. It compares values already supplied by
   source-authoritative snapshots.
3. Unsupported dimensions cannot become `READY`, even when expected and realized values are present.
4. Execution quality blocks with `EXECUTION_EVIDENCE_BLOCKED` when mandatory execution evidence is
   missing.
5. Mixed ready plus unsupported dimensions roll up to `DEGRADED`, preventing a false all-ready
   support claim while still allowing supported dimensions to be inspected.
6. PM scoring, AI judgment, and narrative generation are absent from this slice.

## Deterministic State Logic

| Condition | Dimension State |
| --- | --- |
| Source contract not certified or source posture is `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| Mandatory source evidence missing, conflicting, invalid, or value absent | `BLOCKED` |
| Variance pressure exceeds hard tolerance | `BREACHED` |
| Variance pressure exceeds soft tolerance | `PENDING_REVIEW` |
| Values are comparable but source posture is degraded | `DEGRADED` |
| Values are comparable and within tolerance with ready sources | `READY` |

Review roll-up precedence is:

`BLOCKED` -> `BREACHED` -> `PENDING_REVIEW` -> `DEGRADED` or mixed `NOT_SUPPORTED` -> `READY`.

## Validation

Commands:

```powershell
python -m pytest tests\unit\core\test_outcome_comparison.py -q
python -m ruff check src\core\outcomes tests\unit\core\test_outcome_comparison.py
```

Observed result:

1. `10 passed`
2. `All checks passed!`

## Supported-Feature Decision

No supported feature is promoted by Slice 3. This slice proves pure domain behavior only. Runtime
support requires expected snapshot assembly, source adapters, persistence, APIs, OpenAPI
certification, live evidence, documentation publication, and downstream realization where surfaced.
