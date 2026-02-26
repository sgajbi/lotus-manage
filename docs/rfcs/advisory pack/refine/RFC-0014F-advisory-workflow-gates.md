# RFC-0014F: Advisory Workflow Gates & Next-Step Semantics (Stateless, Pre-Persistence)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14F |
| **Depends On** | RFC-0014A (Proposal Simulation) |
| **Strongly Recommended** | RFC-0014D (Suitability Scanner), RFC-0014E (Proposal Artifact) |
| **Doc Location** | `docs/rfcs/advisory pack/refine/RFC-0014F-advisory-workflow-gates.md` |
| **Backward Compatibility** | Not required |
| **Implemented In** | 2026-02-19 |

---

## 0. Executive Summary

RFC-0014F introduces **workflow semantics** for advisory proposals—without persistence—by defining:

- a clear **gate decision**: what review/approval is required before proceeding
- a deterministic **recommended next step** for advisor workflow:
  - NONE / RISK_REVIEW / COMPLIANCE_REVIEW / CLIENT_CONSENT / EXECUTION_READY
- standardized **reasons** that explain *why* the gate is required

This is a stateless “workflow brain” that interprets:
- simulation `status` (READY / PENDING_REVIEW / BLOCKED)
- rule results (HARD vs SOFT)
- suitability issues (NEW / RESOLVED / PERSISTENT with severity)

and returns a consistent **GateDecision** block in both:
- `/rebalance/proposals/simulate` response
- `/rebalance/proposals/artifact` (if implemented)
 - `/rebalance/simulate` response (shared DPM vocabulary)

---

## 1. Motivation / Problem Statement

In advisory workflows, a simulation result must be turned into a process decision:

- Is this proposal ready to present to the client?
- Does it require compliance or risk review?
- Is it blocked due to data quality or infeasibility?
- If it’s reviewable, what exactly triggered the gate?

Without explicit gates, UIs and downstream systems must infer workflow from raw diagnostics, which leads to inconsistent behavior and audit challenges.

---

## 2. Scope

### 2.1 In Scope
- Define `GateDecision` schema and deterministic evaluation logic.
- Add `gate_decision` to proposal simulation result and proposal artifact.
- Add `gate_decision` to DPM rebalance simulation result for shared workflow semantics.
- Define mapping rules from:
  - rule_results (HARD/FAIL, SOFT/FAIL)
  - suitability summary (new issues and severities)
  - data quality diagnostics

### 2.2 Out of Scope
- Persistence of workflow state (approval tracking, who approved, timestamps)
- Integration with human review systems (ticketing/workflow engines)
- Jurisdiction-specific gating policies (can be layered later)

---

## 3. Definitions

### 3.1 Gate vs Status
- **Status** (engine feasibility):
  - `READY`: feasible and within hard rules; may still need review
  - `PENDING_REVIEW`: feasible but requires review based on soft rules/policy
  - `BLOCKED`: infeasible or hard fail; cannot proceed

- **GateDecision** (workflow next step):
  - what the advisor/system should do next, and why

### 3.2 Gate types (enumeration)
- `BLOCKED`
- `RISK_REVIEW_REQUIRED`
- `COMPLIANCE_REVIEW_REQUIRED`
- `CLIENT_CONSENT_REQUIRED`
- `EXECUTION_READY`
- `NONE` (only used when proposal is informational and no action is intended)

In practice:
- `EXECUTION_READY` means “can move to execute if client consent already obtained”
- `CLIENT_CONSENT_REQUIRED` means “ready to show client; request consent”
- Review gates mean “needs internal review before client consent”

---

## 4. GateDecision Schema

```json
"gate_decision": {
  "gate": "BLOCKED|RISK_REVIEW_REQUIRED|COMPLIANCE_REVIEW_REQUIRED|CLIENT_CONSENT_REQUIRED|EXECUTION_READY|NONE",
  "recommended_next_step": "FIX_INPUT|RISK_REVIEW|COMPLIANCE_REVIEW|REQUEST_CLIENT_CONSENT|EXECUTE",
  "reasons": [
    {
      "reason_code": "NEW_HIGH_SUITABILITY_ISSUE",
      "severity": "HIGH",
      "source": "SUITABILITY|RULE_ENGINE|DATA_QUALITY",
      "details": {
        "issue_id": "SUIT_ISSUER_MAX|ISSUER_X",
        "message": "Issuer concentration exceeds 20% after proposal."
      }
    }
  ],
  "summary": {
    "hard_fail_count": 1,
    "soft_fail_count": 2,
    "new_high_suitability_count": 1,
    "new_medium_suitability_count": 0
  }
}
````

Determinism:

* `reasons` must be sorted deterministically:

  1. severity HIGH→MEDIUM→LOW
  2. source
  3. reason_code
  4. stable key within details (e.g., issue_id)

---

## 5. Gate Evaluation Rules (Deterministic Policy)

### 5.1 Inputs to gate evaluation

* `status` from simulation
* `rule_results[]`

  * each has: rule_id, pass/fail, severity (HARD/SOFT/INFO), impacts
* `suitability` (if available)

  * counts of NEW issues by severity
  * list of NEW issues
* diagnostics data-quality flags (missing prices/fx, reconciliation mismatch, etc.)

### 5.2 Policy evaluation order

Evaluate in strict order:

#### Rule 1: BLOCKED dominates

If `status == BLOCKED`:

* `gate = BLOCKED`
* `recommended_next_step = FIX_INPUT`
* reasons include:

  * all HARD rule failures
  * plus any key diagnostics (missing FX, missing prices, oversell, insufficient cash)

#### Rule 2: Compliance review triggers

Else if any of the following:

* NEW suitability issue severity HIGH
* any rule failure of type SOFT but tagged as “COMPLIANCE_SENSITIVE” (optional tagging)
* governance breaches (SELL_ONLY violated, BANNED/SUSPENDED traded) if not already blocked
  Then:
* `gate = COMPLIANCE_REVIEW_REQUIRED`
* `recommended_next_step = COMPLIANCE_REVIEW`

#### Rule 3: Risk review triggers

Else if:

* any SOFT rule failures (e.g., cash band breach)
* NEW suitability issue severity MEDIUM
  Then:
* `gate = RISK_REVIEW_REQUIRED`
* `recommended_next_step = RISK_REVIEW`

#### Rule 4: Client consent

Else if proposal is feasible and clean:

* `gate = CLIENT_CONSENT_REQUIRED`
* `recommended_next_step = REQUEST_CLIENT_CONSENT`

#### Rule 5: Execution ready (optional)

If the request includes `options.client_consent_already_obtained=true`:

* and gate would otherwise be CLIENT_CONSENT_REQUIRED
  Then:
* `gate = EXECUTION_READY`
* `recommended_next_step = EXECUTE`

---

## 6. Reason Codes (Standardized)

Minimum set:

### 6.1 From rule engine

* `HARD_RULE_FAIL:<rule_id>`
* `SOFT_RULE_FAIL:<rule_id>`

### 6.2 From suitability (NEW issues)

* `NEW_HIGH_SUITABILITY_ISSUE`
* `NEW_MEDIUM_SUITABILITY_ISSUE`

### 6.3 Data quality / reconciliation

* `DATA_QUALITY_MISSING_PRICE`
* `DATA_QUALITY_MISSING_FX`
* `RECONCILIATION_MISMATCH`
* `VALUATION_MODE_TRUST_SNAPSHOT_WARNING` (if applicable)

### 6.4 Governance flags

* `GOVERNANCE_SELL_ONLY_VIOLATION`
* `GOVERNANCE_RESTRICTED_INCREASE`
* `GOVERNANCE_SUSPENDED_PRESENT`
* `GOVERNANCE_BANNED_PRESENT`

All reason codes must be documented and stable.

---

## 7. API Integration

### 7.1 Proposal simulate response

Add `gate_decision` to the response alongside:

* status, rule_results, diagnostics, suitability, drift_analysis

### 7.2 Proposal artifact

If RFC-0014E implemented:

* include the same `gate_decision` in `summary.recommended_next_step`
* include full block in artifact top-level to support workflow routing

### 7.3 DPM simulate response

Add `gate_decision` to DPM `/rebalance/simulate` response with shared semantics:
- clean discretionary runs default to `EXECUTION_READY` unless consent policy is enabled
- blocked and pending-review flows map to deterministic workflow gates

---

## 8. Implementation Plan

1. Implement shared gate evaluator in `src/core/common/workflow_gates.py`.
2. Add `GateDecision` contracts in `src/core/models.py`.
3. Add engine options:
   * `enable_workflow_gates`
   * `workflow_requires_client_consent`
   * `client_consent_already_obtained`
4. Wire into:
   * advisory simulate (`ProposalResult.gate_decision`)
   * advisory artifact (`ProposalArtifact.gate_decision`)
   * DPM simulate (`RebalanceResult.gate_decision`)
5. Add unit/API/contract coverage.

---

## 9. Testing Plan

### 9.1 Unit tests

* BLOCKED always yields gate BLOCKED
* NEW HIGH suitability => compliance review
* SOFT rule fail only => risk review
* clean READY => client consent
* consent already obtained => execution ready

### 9.2 Golden tests

Add:

* `scenario_14F_blocked_gate.json`
* `scenario_14F_compliance_gate_new_high.json`
* `scenario_14F_risk_gate_soft_fail.json`
* `scenario_14F_client_consent_gate_clean.json`

Each asserts:

* gate
* next step
* deterministic reasons ordering

---

## 10. Acceptance Criteria (DoD)

* Implemented: responses include `gate_decision` with stable schema.
* Implemented: deterministic gate policy with test coverage.
* Implemented: standardized reason codes and deterministic sorting.
* Implemented: advisory artifact and simulate include gate decision; DPM simulate includes shared gate decision.

---

## 11. Follow-ups

* RFC-0014G: Persist workflow state (proposal saved, approval tracking)
* RFC-0014H: Jurisdiction-specific gate policies
* RFC-0014I: Integration with consent and execution systems



## Behavior Reference (Implemented)

1. Workflow gates are derived from deterministic policy evaluation over status, rule outcomes, suitability severity, and key diagnostics.
2. `BLOCKED` always dominates gate outcomes and routes to input-fix workflow.
3. Clean feasible proposals route to client-consent or execution-ready based on consent options.
4. Shared gate vocabulary is applied consistently in advisory simulate, advisory artifact, and DPM simulate responses.
