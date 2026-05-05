# RFC-0042 Slice 4 - Expected Snapshot Assembly

| Field | Value |
| --- | --- |
| **RFC** | RFC-0042 Post-Trade Outcome Feedback Loop |
| **Slice** | Slice 4 - Expected Snapshot Assembly |
| **Implementation Branch** | `feat/rfc0042-implementation` |
| **Date** | 2026-05-05 |
| **Status** | DONE |

---

## Implemented Scope

Slice 4 adds expected outcome snapshot assembly from implementation-backed manage artifacts:

1. RFC-0039 construction alternative set and selected alternative.
2. RFC-0040 pre-trade proof pack, source hashes, section hashes, and source lineage.
3. RFC-0041 rebalance wave item when the expected evidence is wave-linked.
4. RFC-0041 internal operations handoff ref when supplied.

The implementation lives in `src/core/outcomes/snapshots.py` and produces
`DpmExpectedOutcomeSnapshot` from `src/core/outcomes/models.py`.

## Guardrails

1. Selection must reference the supplied alternative set and an existing selected alternative.
2. Proof-pack portfolio, alternative-set, selected-alternative, and rebalance-run linkage must match.
3. Wave item portfolio, mandate, alternative-set, selected-alternative, and proof-pack linkage must
   match when wave evidence is supplied.
4. Handoff refs must belong to the wave, include the selected wave item, and must not claim external
   execution.
5. Expected values are assembled only from available selected-alternative metrics. Missing values are
   omitted rather than silently defaulted.
6. Source refs, source hashes, section hashes, and supportability posture are preserved for later
   persistence, API, report, AI, and audit slices.

## Expected Values

| Outcome Dimension | Expected Source |
| --- | --- |
| `DRIFT_REDUCTION` | RFC-0039 selected alternative `comparison_metrics.drift_after` |
| `COST` | RFC-0039 selected alternative `comparison_metrics.estimated_transaction_cost` when available |
| `CASH_RESIDUAL` | RFC-0039 selected alternative `comparison_metrics.cash_weight_after` when available |

Risk, performance, tax, FX residual, and execution-quality expected values are not defaulted in this
slice. They require source-backed artifacts or later source-owner contracts before support can be
claimed.

## Validation

Commands:

```powershell
python -m pytest tests\integration\dpm\test_outcome_expected_snapshot_assembly.py -q
python -m ruff check src\core\outcomes tests\unit\core\test_outcome_comparison.py tests\integration\dpm\test_outcome_expected_snapshot_assembly.py
```

Observed result:

1. `5 passed`
2. `All checks passed!`

## Supported-Feature Decision

No supported feature is promoted by Slice 4. This slice proves expected snapshot assembly only.
Runtime support still requires realized source adapters, persistence, APIs, OpenAPI certification,
live evidence, documentation publication, and downstream realization where surfaced.
