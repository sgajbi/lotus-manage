# RFC-0039: Advanced Portfolio Construction and Rebalance Alternatives

| Metadata | Details |
| --- | --- |
| **Status** | PROPOSED - IMPLEMENTATION READY |
| **Created** | 2026-05-03 |
| **Last Tightened** | 2026-05-03 |
| **Owner** | `lotus-manage` |
| **Business Sponsor Persona** | DPM head, portfolio manager, CIO desk, investment control, tax specialist, operations, sales/pre-sales |
| **Depends On** | RFC-0021, RFC-0022, RFC-0023, RFC-0024, RFC-0025, RFC-0028, RFC-0036, RFC-0037, RFC-0038, `lotus-core` RFC-0087, Gateway RFC-0098, Workbench RFC-0098 |
| **Doc Location** | `docs/rfcs/RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md` |
| **Implementation Branch** | TBD when implementation begins |

---

## 0. Executive Summary

RFC-0038 made `lotus-manage` understand a discretionary mandate as a governed operating object:
digital twin, health score, source readiness, monitoring exceptions, and command-center posture.
RFC-0039 is the next analytical step. It turns `lotus-manage` from a single-result rebalance engine
into a portfolio construction decision system that can generate, compare, explain, persist, and
select multiple rebalance alternatives for a discretionary mandate.

The business point is simple: a premium private bank does not tell a portfolio manager "here is one
trade list." It shows disciplined alternatives:

1. do nothing and accept current drift,
2. rebalance explainably toward model,
3. minimize turnover,
4. protect tax budget,
5. preserve liquidity and cash needs,
6. control risk and concentration,
7. respect ESG/restrictions,
8. manage currency exposure,
9. test construction under regime or stress conditions.

Each alternative must expose objective terms, constraints, trades, expected outcomes, feasibility,
source supportability, fallback decisions, and evidence. The selected alternative becomes the
input to proof packs, review workflows, rebalance waves, and post-trade outcome learning in later
RFCs.

This RFC is a manage-side backend RFC. As of this RFC tightening, `lotus-manage` construction
alternatives are not integrated with `lotus-gateway` or `lotus-workbench`. Gateway and Workbench
must receive separate paired RFCs near the end of the manage implementation, after the manage
contract and evidence are concrete enough to articulate correctly. The full business outcome must
not be claimed from manage-only implementation.

---

## 1. Gold-Standard Tightening Review

This section records the critical review performed before implementation.

| Area | First-draft strength | Gap found | Tightened requirement |
| --- | --- | --- | --- |
| Domain ambition | Strong construction vocabulary and method list. | Needed sharper MVP sequencing and proof gates. | Added MVP method set, later method gates, evidence requirements, and promotion rules. |
| Business outcome | Clear value for PMs and sales. | Needed persona-level outcomes and downstream realization boundary. | Added PM, CIO, tax, operations, sales/pre-sales, and an end-of-implementation Gateway/Workbench realization RFC slice. |
| Architecture | Correctly kept risk/performance as external authorities. | Risk/performance enrichment could be read as manage-owned. | Added strict domain authority rules and degraded enrichment semantics. |
| API design | Good basic alternative endpoints. | Needed certified API details, action semantics, idempotency, and comparison contract. | Added endpoint family, request/response expectations, no-alias rule, and OpenAPI requirements. |
| Solver posture | Objective/constraint traces were identified. | Needed deterministic fallback and infeasibility taxonomy. | Added solver trace, fallback, relaxation, and infeasibility requirements. |
| Slices | Had feature slices plus mandatory slices. | Needed full Lotus delivery standard and cross-repo realization slice. | Added platform/scaffolding, cleanup, proof, hardening, closure, and an end-of-implementation paired Gateway/Workbench RFC slice. |
| Evidence | Live proof was mentioned. | Needed exact evidence package and critical review standard. | Added canonical evidence package with request/response, alternatives matrix, traces, degraded examples, and selected-event proof. |
| Documentation | Supported-features ledger existed. | Needed business-facing wiki/demo outputs and implementation-backed wording. | Added documentation/wiki/demo expectations and supported-feature promotion discipline. |

Implementation must not begin until this RFC has a confirmed first-wave method set, upstream field
map, and fallback policy. Gateway/Workbench realization RFCs should be created near the end of the
manage implementation, once the implemented manage API contracts and evidence are stable enough to
write those RFCs accurately.

---

## 2. Business Outcomes

RFC-0039 must deliver these business outcomes:

1. **Better PM construction decisions**
   PMs compare multiple valid construction paths instead of accepting one generated trade list.
2. **Clear trade-off visibility**
   Each alternative shows drift, tracking error, turnover, estimated cost, tax, liquidity, cash,
   FX, ESG/restriction, source-readiness, and supportability trade-offs.
3. **More personalized DPM**
   Mandates can prioritize tax sensitivity, low turnover, liquidity, income needs, risk reduction,
   sustainability, currency exposure, or CIO model adherence.
4. **Higher investment discipline**
   Construction becomes objective-driven, constraint-aware, repeatable, and evidence-backed.
5. **Improved review and approval quality**
   PMs, CIO desk, compliance, tax specialists, and operations can see why one alternative was
   recommended, why another was rejected, and which constraints or fallbacks shaped the result.
6. **Reduced unnecessary trading**
   Turnover, transaction cost, tax realization, settlement, and liquidity impacts are compared
   before action.
7. **Stronger client-demo and sales narrative**
   Lotus can demonstrate institutional-grade portfolio construction as a visible value proposition,
   not a hidden optimizer.
8. **Foundation for proof packs, waves, and outcome learning**
   Selected alternatives become structured inputs to RFC-0040 proof packs, RFC-0041 waves, and
   RFC-0042 expected-versus-realized review.

---

## 3. Current Baseline

Existing `lotus-manage` has:

1. deterministic rebalance simulation,
2. stateless and gated stateful execution envelopes,
3. core source-data integration for DPM model targets, mandate binding, eligibility, tax lots,
   market data coverage, and DPM source readiness,
4. mandate digital twin and health foundation from RFC-0038,
5. policy-pack controls,
6. workflow gates and supportability,
7. idempotency, lineage, artifacts, and certified API posture,
8. heuristic and solver-capable target-generation foundation.

Current gaps:

1. one execution generally produces one primary result,
2. construction alternatives are not first-class resources,
3. do-nothing baseline is not consistently surfaced as a comparable alternative,
4. solver objective and constraint trade-offs are not presented as PM choices,
5. infeasibility and soft-constraint relaxation evidence is not rich enough,
6. tax, turnover, cost, liquidity, FX, ESG, risk, and performance trade-offs are not normalized
   into a decision matrix,
7. alternative selection is not actor-attributed as a durable decision event,
8. Gateway and Workbench do not yet expose alternatives as a product workflow.

---

## 4. Goals and Non-Goals

### 4.1 Goals

1. Add first-class `DpmRebalanceAlternativeSet` and `DpmRebalanceAlternative` resources.
2. Generate a bounded set of alternatives for one discretionary mandate.
3. Include `DO_NOTHING_BASELINE`, `HEURISTIC_EXPLAINABLE`, and at least two additional first-wave
   construction methods before initial support promotion.
4. Expose objective terms, constraint traces, infeasibility, fallback, and relaxation evidence.
5. Normalize comparison metrics across alternatives.
6. Persist alternative sets, alternatives, and selection events.
7. Support stateful and stateless inputs, with stateful source-data support through core products.
8. Preserve domain authority for risk, performance, source data, report, archive, and AI.
9. Prepare selected alternatives for proof-pack and workflow RFCs.
10. Produce certified OpenAPI and live canonical evidence.

### 4.2 Non-Goals

1. Execute trades.
2. Replace `lotus-risk` as risk analytics authority.
3. Replace `lotus-performance` as performance authority.
4. Replace `lotus-core` as portfolio, tax-lot, price, FX, or eligibility authority.
5. Create advisor-led proposal or client-consent workflows. Those belong to `lotus-advise`.
6. Let AI choose alternatives. AI may summarize evidence only in later RFCs.
7. Guarantee global optimality under all market and mandate constraints.
8. Build the Gateway composition contract or Workbench UI in this RFC. Those require paired RFCs.

---

## 5. Architecture Direction

### 5.1 Manage-Side Construction Flow

```mermaid
flowchart LR
    Request[Alternative generation request] --> Source[Source context resolver]
    Source --> Twin[Mandate digital twin]
    Twin --> Methods[Construction method registry]
    Methods --> Baseline[Do-nothing baseline]
    Methods --> Heuristic[Explainable heuristic]
    Methods --> Solver[Solver-constrained method]
    Methods --> Enriched[Tax / liquidity / risk / ESG / FX methods]
    Baseline --> Compare[Comparison matrix]
    Heuristic --> Compare
    Solver --> Compare
    Enriched --> Compare
    Compare --> Persist[Alternative set persistence]
    Persist --> Select[Selection event]
    Select --> Proof[Future proof pack / wave / outcome RFCs]
```

### 5.2 Domain Authority Rules

| Domain | Authority | Manage usage |
| --- | --- | --- |
| Source portfolio, holdings, model, eligibility, tax lots, price, FX | `lotus-core` | consume source products and preserve source readiness |
| Mandate digital twin, health, construction alternatives, selection | `lotus-manage` | own |
| Risk impact, stress, drawdown, concentration, tracking error where authoritative | `lotus-risk` | consume enrichment; degrade truthfully when unavailable |
| Performance/benchmark context, attribution, realized return context | `lotus-performance` | consume enrichment/context; do not recompute performance truth |
| Proof pack/report generation | `lotus-report` | downstream consumer of selected alternative |
| Archive | `lotus-archive` | downstream evidence owner |
| AI narrative | `lotus-ai` | future summarization only |
| Composition API | `lotus-gateway` | future consumer and product boundary |
| User experience | `lotus-workbench` | future consumer through Gateway |

`lotus-manage` may calculate local construction diagnostics such as drift distance, turnover,
estimated transaction cost, and local concentration approximations only when the methodology is
documented, deterministic, and clearly labelled as manage-side construction diagnostics rather than
authoritative risk/performance analytics.

---

## 6. Construction Method Roadmap

### 6.1 First-Wave Required Methods

The first implementation wave must include:

| Method | Purpose | Required before support promotion |
| --- | --- | --- |
| `DO_NOTHING_BASELINE` | Compare against no action. | current drift, breaches, source readiness, no trades |
| `HEURISTIC_EXPLAINABLE` | Preserve deterministic target-difference baseline. | reason codes for capping, suppression, funding, blocking |
| `MIN_TURNOVER` | Reduce drift with fewer trades. | turnover weight, trade count, drift reduction, cost estimate |
| `TAX_AWARE` or `LIQUIDITY_AWARE` | Prove source-aware personalized construction. | tax-lot or cash/liquidity supportability and degraded behavior |

First-wave implementation may include solver-constrained construction only if solver trace,
fallback, infeasibility, and deterministic timeout behavior are production-grade.

### 6.2 Later Methods

RFC-0039 is the owning RFC for both first-wave and second-wave construction alternatives. Later
RFCs such as RFC-0040, RFC-0041, RFC-0042, and RFC-0043 consume selected alternatives for proof
packs, waves, outcome learning, and AI summarization; they must not create duplicate construction
method RFCs unless a genuinely separate business capability appears. The following second-wave
methods remain proposed inside RFC-0039 until each method is individually implemented, tested,
certified, and promoted:

1. `SOLVER_CONSTRAINED`
2. `RISK_AWARE`
3. `ESG_AWARE`
4. `CURRENCY_OVERLAY`
5. `REGIME_STRESS_AWARE`
6. advanced multi-objective blend methods

Second-wave implementation must stay slice-driven within this RFC:

1. `SOLVER_CONSTRAINED` only after deterministic solver timeouts, infeasibility taxonomy, fallback,
   and objective/constraint traces are production-grade.
2. `RISK_AWARE` only through `lotus-risk` authority or explicit degraded local diagnostics; manage
   must not become risk methodology authority.
3. `ESG_AWARE` only after restriction, sustainability, eligibility, and missing-profile behavior
   are source-backed or explicitly degraded.
4. `CURRENCY_OVERLAY` only after FX exposure, hedge-ratio bands, hedge eligibility, and settlement
   readiness are documented and tested.
5. `REGIME_STRESS_AWARE` only after scenario packs and stress contribution evidence are
   risk-authoritative or explicitly unavailable.
6. Advanced blends only after the component methods and objective weighting governance are already
   proven.

### 6.3 Method Definitions

#### DO_NOTHING_BASELINE

Purpose:

1. make "no action" a governed comparator,
2. quantify current drift, source readiness, rule breaches, cash, tax, restriction, and risk
   posture,
3. avoid implying that trading is always superior.

Required output:

1. no trade intents,
2. current state as after state,
3. health/rule results preserved,
4. drift reduction equal to zero,
5. reason code `baseline_no_action`.

#### HEURISTIC_EXPLAINABLE

Purpose:

1. preserve current deterministic rebalance logic,
2. provide reason-coded target-difference construction,
3. act as fallback when solver or enrichment is unavailable.

Rules:

1. same input produces same output,
2. no hidden relaxations,
3. all capping, suppression, funding, lot selection, and blocking has reason codes,
4. unsupported data produces degraded state rather than fabricated metrics.

#### MIN_TURNOVER

Purpose:

1. reduce material drift while avoiding unnecessary trading,
2. support low-activity or cost-sensitive mandates,
3. reduce operational burden.

Required metrics:

1. turnover weight,
2. trade count,
3. drift before/after/reduction,
4. estimated transaction cost,
5. minimum-trade-notional suppressions.

#### TAX_AWARE

Purpose:

1. reduce realized gains within mandate or policy tax budget,
2. use tax-lot windows from `lotus-core`,
3. flag missing tax lots explicitly.

Lot-selection posture:

1. `HIFO`
2. `LIFO`
3. `FIFO`
4. `MIN_GAIN`
5. `TAX_LOTS_UNAVAILABLE`

No tax-aware alternative may be `READY` when required tax lots are unavailable and the mandate
requires tax-aware execution.

#### LIQUIDITY_AWARE

Purpose:

1. protect cash buffers,
2. respect known cashflow needs when available,
3. avoid illiquid trades where liquidity profile is weak,
4. preserve settlement readiness.

Inputs:

1. current cash,
2. settlement ladder,
3. known cashflow forecast if available,
4. instrument liquidity profile if available.

#### SOLVER_CONSTRAINED

Purpose:

1. optimize against an explicit objective function,
2. respect hard and soft constraints,
3. quantify trade-offs.

Required solver trace:

1. solver engine,
2. solver version,
3. objective terms,
4. constraint set id,
5. time budget,
6. solve status,
7. gap/tolerance where available,
8. relaxed constraints,
9. infeasible constraints,
10. fallback method when used.

#### RISK_AWARE

Purpose:

1. reduce or control tracking error,
2. mitigate concentration,
3. avoid worsening drawdown or stress posture beyond mandate limits,
4. use `lotus-risk` enrichment where available.

Risk-aware alternatives may be generated in degraded mode with clearly labelled local diagnostics,
but must mark missing `lotus-risk` enrichment.

#### ESG_AWARE

Purpose:

1. apply sustainability exclusions,
2. avoid restricted sectors, issuers, and instruments,
3. prefer eligible sustainable instruments where the mandate requires it,
4. expose ESG degradation when source profiles are incomplete.

#### CURRENCY_OVERLAY

Purpose:

1. compare unhedged, partially hedged, and fully hedged outcomes,
2. separate strategic currency exposure from trade funding,
3. respect currency exposure and hedge-ratio bands,
4. avoid hedge trades when required FX, eligibility, forward points, or settlement evidence is
   missing.

#### REGIME_STRESS_AWARE

Purpose:

1. compare alternatives under named market-regime and stress packs,
2. reject or downgrade alternatives that improve drift while worsening unacceptable downside,
3. support CIO-required scenario checks,
4. expose degraded state when risk-authoritative scenario packs are unavailable.

---

## 7. Objective Function and Constraint Registry

### 7.1 Objective Function

Target objective model:

```text
minimize:
    w_drift * drift_distance
  + w_tracking_error * tracking_error
  + w_turnover * turnover
  + w_cost * transaction_cost
  + w_tax * realized_tax
  + w_cash * cash_band_penalty
  + w_liquidity * liquidity_penalty
  + w_esg * esg_penalty
  + w_concentration * concentration_penalty
  + w_currency_overlay * currency_overlay_penalty
  + w_scenario_loss * scenario_loss_penalty
```

Objective weights may come from:

1. mandate digital twin,
2. policy pack,
3. construction method default,
4. explicit request override where policy allows.

Every objective term must be exposed in the alternative trace, even when the term is inactive.

### 7.2 Constraint Families

Initial constraint registry:

1. `ASSET_CLASS_BAND`
2. `INSTRUMENT_WEIGHT_MAX`
3. `ISSUER_WEIGHT_MAX`
4. `SECTOR_WEIGHT_MAX`
5. `REGION_WEIGHT_MAX`
6. `CURRENCY_EXPOSURE_MAX`
7. `TRACKING_ERROR_MAX`
8. `TURNOVER_MAX`
9. `TAX_REALIZATION_MAX`
10. `CASH_BAND`
11. `MIN_TRADE_NOTIONAL`
12. `NO_SHORTING`
13. `NO_OVERDRAFT`
14. `SETTLEMENT_CASH_LADDER`
15. `SHELF_ELIGIBILITY`
16. `CLIENT_RESTRICTION`
17. `SUSTAINABILITY_EXCLUSION`
18. `LIQUIDITY_MINIMUM`
19. `CURRENCY_HEDGE_RATIO_BAND`
20. `FX_FORWARD_ELIGIBILITY`
21. `SCENARIO_LOSS_MAX`
22. `REGIME_POLICY_BAND`
23. `STRESS_CONTRIBUTION_MAX`

Constraint severities:

1. `HARD`: cannot be relaxed without `BLOCKED`,
2. `SOFT`: may produce `PENDING_REVIEW`,
3. `INFO`: evidence only.

Relaxation rules:

1. hard constraints cannot be silently relaxed,
2. every soft relaxation must include reason, magnitude, policy authority, and evidence,
3. default implementation should avoid relaxations unless explicitly configured.

---

## 8. Domain Models

### 8.1 DpmRebalanceAlternativeSet

Required fields:

| Field | Type | Description | Example |
| --- | --- | --- | --- |
| `alternative_set_id` | string | Stable identifier for generated set. | `altset_PB_SG_GLOBAL_BAL_001_20260410_001` |
| `portfolio_id` | string | Portfolio id. | `PB_SG_GLOBAL_BAL_001` |
| `mandate_id` | string | Mandate id. | `MANDATE_PB_SG_GLOBAL_BAL_001` |
| `as_of_date` | date | Business date. | `2026-04-10` |
| `input_mode` | enum | `stateful` or `stateless`. | `stateful` |
| `requested_methods` | array | Methods requested by caller. | `["DO_NOTHING_BASELINE","MIN_TURNOVER"]` |
| `generated_methods` | array | Methods generated successfully or degraded. | `["DO_NOTHING_BASELINE","HEURISTIC_EXPLAINABLE","MIN_TURNOVER"]` |
| `source_readiness` | object | Source readiness summary. | `{ "state": "READY" }` |
| `alternatives` | array | Generated alternatives. | `[]` |
| `comparison_summary` | object | Ranked comparison and recommendation. | `{ "recommended_alternative_id": "alt_002" }` |
| `selected_alternative_id` | string/null | Selected alternative if actor selected one. | `alt_002` |
| `recommendation_basis` | string | Why recommendation was ranked first. | `best_drift_reduction_with_low_turnover` |
| `lineage` | object | Source and calculation lineage. | `{ "source_system": "lotus-manage" }` |
| `created_at` | datetime | Creation timestamp. | `2026-05-03T08:00:00Z` |

### 8.2 DpmRebalanceAlternative

Required fields:

1. `alternative_id`
2. `alternative_type`
3. `status`
4. `construction_method`
5. `objective_trace`
6. `constraint_trace`
7. `before`
8. `target`
9. `intents`
10. `after_simulated`
11. `rule_results`
12. `diagnostics`
13. `decision_metrics`
14. `risk_impact`
15. `tax_impact`
16. `turnover_impact`
17. `cost_impact`
18. `liquidity_impact`
19. `fx_impact`
20. `source_supportability`
21. `explanation`
22. `lineage`

### 8.3 DpmAlternativeDecisionMetrics

Required metrics:

1. `drift_before`
2. `drift_after`
3. `drift_reduction`
4. `turnover_weight`
5. `trade_count`
6. `estimated_transaction_cost_base`
7. `estimated_realized_gain_base`
8. `cash_after_weight`
9. `risk_score_before`
10. `risk_score_after`
11. `tracking_error_before`
12. `tracking_error_after`
13. `restriction_breach_count`
14. `source_readiness_state`
15. `method_rank`
16. `recommendation_score`

---

## 9. API Surface

### 9.1 Generate Alternatives

`POST /api/v1/rebalance/alternatives`

Purpose:

1. generate a bounded alternative set for one mandate or portfolio,
2. support stateless and stateful source input,
3. persist alternative set, lineage, and supportability.

Required request fields:

1. `input_mode`
2. `portfolio_id` or stateless input bundle
3. `as_of_date`
4. `mandate_id`
5. `requested_methods`
6. `policy_pack_id`
7. `max_alternatives`
8. `include_risk_enrichment`
9. `include_performance_context`
10. `include_tax_impact`
11. `solver_time_budget_ms`
12. `idempotency_key`

Response:

1. full `DpmRebalanceAlternativeSet`,
2. per-alternative status,
3. source readiness and degradation details,
4. support reference,
5. persistence refs.

### 9.2 Retrieve Alternative Set

`GET /api/v1/rebalance/alternatives/{alternative_set_id}`

Purpose:

1. retrieve persisted alternative set,
2. support Gateway/Workbench comparison,
3. support proof-pack generation.

### 9.3 Select Alternative

`POST /api/v1/rebalance/alternatives/{alternative_set_id}/select`

Purpose:

1. mark selected alternative,
2. persist actor, rationale, timestamp, and selection version,
3. prepare selected alternative for proof pack and workflow review.

Rules:

1. selection does not execute trades,
2. only one selected alternative is active per selection version,
3. selecting a `BLOCKED` alternative requires explicit override and remains `BLOCKED` or
   `PENDING_REVIEW` according to policy,
4. actor attribution is mandatory,
5. selection must emit audit and lineage evidence.

### 9.4 Compare Alternatives

`GET /api/v1/rebalance/alternatives/{alternative_set_id}/comparison`

Purpose:

1. return a compact comparison matrix for Gateway/Workbench and proof packs,
2. avoid forcing consumers to parse full trade-level details when only comparison is needed.

This endpoint may be implemented as a view over the stored set, but if added, it must be certified
and not duplicate business truth.

---

## 10. Persistence and Retention

Tables:

1. `dpm_alternative_sets`
2. `dpm_rebalance_alternatives`
3. `dpm_alternative_selection_events`

Required indexes:

1. `(portfolio_id, created_at desc)`
2. `(mandate_id, created_at desc)`
3. `(alternative_set_id)`
4. `(selected_alternative_id)`
5. `(status, created_at desc)`
6. `(idempotency_key)`

Retention:

1. selected alternatives: 7 years,
2. unselected alternatives: configurable, default 2 years,
3. blocked alternatives linked to audit or compliance review: 7 years,
4. diagnostic traces may be shortened or summarized where required by storage and sensitivity
   policy, but selected-alternative evidence must remain audit-grade.

---

## 11. OpenAPI and API Certification

Every endpoint in RFC-0039 must be certified before promotion.

Swagger requirements:

1. group under `DPM Construction Alternatives`,
2. explain what each endpoint is for,
3. explain when to use each construction method,
4. explain how solver, fallback, infeasibility, and degraded-source states should be interpreted,
5. include full request and response examples,
6. include ready, pending-review, blocked, infeasible, solver-unavailable, source-degraded, and
   tax-lots-missing examples,
7. every attribute has description, type, and example,
8. no `Any` or untyped dictionary contracts,
9. no duplicate aliases,
10. no advisory/proposal vocabulary leakage,
11. OpenAPI examples are validated by tests.

---

## 12. Security, Audit, Observability, and Data Mesh

Required controls:

1. actor attribution for selection,
2. support references for generation and selection,
3. bounded objective/constraint traces,
4. no raw client names or personal data in logs/metrics,
5. no raw holdings/tax-lot dumps in logs/metrics,
6. no request/response body logging,
7. low-cardinality metrics for method, status, source state, solver status, and failure reason,
8. structured audit for alternative generation, selection, blocked selection, and override attempts,
9. domain-product consumer declarations updated if new upstream data products are consumed,
10. trust telemetry updated if alternatives become a managed data product.

Potential metrics:

1. `lotus_manage_alternative_sets_total{status,input_mode}`
2. `lotus_manage_rebalance_alternatives_total{method,status}`
3. `lotus_manage_alternative_solver_duration_ms{method,status}`
4. `lotus_manage_alternative_generation_duration_ms{input_mode,status}`
5. `lotus_manage_alternative_source_degraded_total{source,reason}`
6. `lotus_manage_alternative_selection_total{status}`

---

## 13. Implementation Slices

Slice 0 evidence is recorded in
`docs/rfcs/RFC-0039-source-data-and-method-map.md`. That file is the governed source map for
first-wave methods, current engine reuse, upstream authority, and missing data-product posture.

### Slice 0: RFC Tightening, Method Scope, and Source Map

Scope:

1. finalize this RFC,
2. confirm first-wave methods,
3. validate current engine and solver capabilities,
4. map constraints to mandate digital twin, policy pack, and source products,
5. identify source-data gaps for risk, tax, liquidity, ESG, FX, cost, and scenario data.

Acceptance:

1. field-by-field source map exists,
2. first-wave method list is explicit,
3. missing upstream fields are listed by owner and not patched locally,
4. no implementation begins with ambiguous method semantics.

### Slice 1: Platform Automation and Scaffolding Improvement Slice

Slice 1 scaffolding governance is recorded in
`docs/standards/construction-alternatives-api-governance.md`. That document records the
platform no-change decision, manage-local optimization-style API rules, bounded trace policy,
method-status semantics, OpenAPI/test scaffolding, and observability scaffold.

Scope:

1. identify platform scaffolding gaps for optimization-style APIs,
2. review OpenAPI example scaffolding for objective/constraint traces,
3. review observability and no-sensitive-trace governance,
4. improve platform automation if the gap is cross-cutting,
5. improve manage-local reusable scaffolding if the gap is repo-specific.

Acceptance:

1. cross-cutting gaps are fixed in `lotus-platform` when applicable,
2. no-change decisions are explicit,
3. future construction APIs start with better scaffolding.

### Slice 2: Cleanup and Structure Slice

Slice 2 structure starts with `src/core/construction/`, a dedicated domain package for
construction-alternative vocabulary and future models. Existing `src/core/rebalance/` modules remain
the execution engine boundary; construction modules must wrap and compare engine outputs rather than
turning the rebalance engine into a monolithic alternatives service.

Scope:

1. separate pure construction logic from API orchestration, persistence, and enrichment,
2. remove duplicated heuristic rules encountered,
3. remove stale advisory/proposal language,
4. replace generic "option" language with "construction alternative" or "selected alternative",
5. keep docs/wiki truth aligned.

Acceptance:

1. construction domain modules are clear and testable,
2. no advisory ownership leakage remains,
3. `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-manage` passes before merge when wiki changed.

### Slice 3: Domain Models and Pure Alternative Engine

Slice 3 domain primitives live in `src/core/construction/`. The first implementation pass adds
bounded construction method/status/source vocabulary, Pydantic alternative models, objective and
constraint trace models, do-nothing baseline construction, rebalance-result wrapping for the
explainable heuristic alternative, normalized drift/turnover comparison metrics, and conservative
alternative-set status roll-up. API, persistence, and method registry work remain later slices.

Scope:

1. add alternative set models,
2. add alternative models,
3. add objective and constraint traces,
4. wrap existing heuristic as one alternative,
5. add do-nothing baseline,
6. add pure comparison metrics.

Acceptance:

1. deterministic model tests pass,
2. objective trace completeness is tested,
3. constraint trace completeness is tested,
4. comparison metrics reconcile.

### Slice 4: Method Registry and Solver/Fallback Governance

Slice 4 implementation lives in `src/core/construction/method_registry.py`. It adds one bounded
registry entry for every declared construction method, first-wave source-family requirements,
support-promotion gates, solver-required posture, explicit solver-unavailable fallback to
`HEURISTIC_EXPLAINABLE`, and bounded solver failure classification.

Scope:

1. add construction method registry,
2. add solver availability posture,
3. add solver trace where solver is used,
4. add fallback handling,
5. add infeasibility classification.

Acceptance:

1. solver success, unavailable, timeout, infeasible, and fallback cases are tested,
2. fallback is explicit and never hidden,
3. hard constraint infeasibility returns `BLOCKED`.

### Slice 5: Tax, Turnover, Liquidity, Cost, and FX Enrichment

Slice 5 implementation lives in `src/core/construction/enrichment.py` and related construction
models. It adds pure enrichment posture for tax, turnover, liquidity/cash, estimated transaction
cost, and FX source state. Transaction cost remains explicitly local/estimated until an
authoritative cost source product exists.

Scope:

1. connect tax lots,
2. calculate turnover and estimated cost,
3. calculate liquidity/cash posture,
4. calculate FX exposure and hedge-readiness posture where first-wave scope allows,
5. classify missing inputs.

Acceptance:

1. tax-lot present and missing cases are tested,
2. turnover budget tests pass,
3. liquidity/cash tests pass,
4. FX degraded cases are explicit where FX method is included.

### Slice 6: Risk and Performance Context

Slice 6 implementation extends `src/core/construction/enrichment.py` and construction models with
`AuthoritativeRiskContext` and `AuthoritativePerformanceContext`. These are seams for preserving
upstream supportability and reason codes from `lotus-risk` and `lotus-performance`; they do not
calculate authoritative risk or performance inside `lotus-manage`. Missing risk/performance context
degrades explicitly with bounded reason codes.

Scope:

1. add seams for risk enrichment,
2. add seams for performance/benchmark context,
3. support degraded mode,
4. preserve upstream supportability and calculation authority.

Acceptance:

1. mocked upstream risk/performance tests pass,
2. unavailable upstream tests pass,
3. response examples with and without enrichment are certified,
4. manage does not recompute authoritative risk/performance figures.

### Slice 7: Persistence and APIs

Slice 7 implementation adds the first certified backend API surface for construction alternatives:
`POST /api/v1/construction/alternative-sets/generate`,
`GET /api/v1/construction/alternative-sets/{alternative_set_id}`, and
`POST /api/v1/construction/alternative-sets/{alternative_set_id}/selections`. It also adds the
`ConstructionRepository` contract, in-memory repository, Postgres repository foundation, migration
`0005_construction_alternatives.sql`, idempotency replay/conflict behavior, and actor-attributed
selection decisions. The API generates RFC-0039 first-wave alternatives: do-nothing baseline,
explainable heuristic, minimum-turnover, and tax-aware posture.

Scope:

1. add migrations and repositories,
2. add generate, retrieve, select, and optional comparison APIs,
3. add idempotency and replay posture,
4. add supportability,
5. certify OpenAPI.

Acceptance:

1. repository parity tests pass for in-memory and PostgreSQL paths where applicable,
2. API tests cover ready, pending review, blocked, infeasible, source-degraded, and idempotent
   replay cases,
3. OpenAPI certification passes.

Evidence:

1. `python -m pytest tests/unit/dpm/construction tests/unit/dpm/api/test_construction_api.py -q`
   passed with 22 tests.
2. `python scripts/openapi_quality_gate.py` passed.
3. `python -m pytest tests/integration/test_openapi_certification_matrix.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q`
   passed with 91 tests.
4. `python -m ruff check src/core/construction src/infrastructure/construction src/api/routers/construction.py src/api/services/construction_service.py tests/unit/dpm/construction tests/unit/dpm/api/test_construction_api.py`
   passed.
5. `python -m mypy src/core/construction src/api/routers/construction.py src/api/services/construction_service.py`
   passed.

### Slice 8: Implementation Proof Slice

Slice 8 has local application-contract evidence in
`output/rfc0039-proof/20260503-172059/` (ignored by Git). The first evidence pass used an already
aligned portfolio and was rejected as not business-useful. The proof was regenerated with drifted
holdings for `PB_SG_GLOBAL_BAL_001`, producing a comparison matrix where do-nothing preserves
drift with zero turnover, heuristic and tax-aware alternatives remove drift with turnover, and the
minimum-turnover alternative correctly lands in `PENDING_REVIEW` after turnover-budget suppression.
This is not yet canonical front-office live-stack proof.

Scope:

1. prove canonical portfolio alternatives,
2. capture request/response evidence,
3. capture comparison matrix,
4. capture objective/constraint trace samples,
5. capture infeasible/fallback/degraded examples,
6. critically review evidence and fix gaps.

Acceptance:

1. live manage proof passes for `PB_SG_GLOBAL_BAL_001`,
2. evidence includes at least do-nothing, heuristic, min-turnover, and one source-aware alternative,
3. no supported-feature promotion occurs until every promoted method has evidence.

Current evidence:

1. `output/rfc0039-proof/20260503-172059/01-generate-request.json`
2. `output/rfc0039-proof/20260503-172059/01-generate-response.json`
3. `output/rfc0039-proof/20260503-172059/02-read-response.json`
4. `output/rfc0039-proof/20260503-172059/03-selection-request.json`
5. `output/rfc0039-proof/20260503-172059/03-selection-response.json`
6. `output/rfc0039-proof/20260503-172059/04-comparison-matrix.json`
7. `output/rfc0039-proof/20260503-172059/metadata.json`
8. `output/rfc0039-proof/live-validator/summary.json`

Critical review:

1. First proof pass was not accepted because zero drift created no meaningful construction
   trade-off.
2. Regenerated proof demonstrates real trade-offs across drift reduction, turnover, method status,
   selection, and degraded enrichment reason codes.
3. The repeatable live validator now includes `construction_alternatives_first_wave`, proving
   generate/read/select plus first-wave trade-off checks. In local short-lived runtime, that probe
   passed while two existing Postgres-supportability probes failed because no Postgres DSN was
   configured for the local app profile.
4. Remaining gap: canonical front-office stack proof against the governed seeded runtime is still
   required before Slice 8 can be marked complete.

### Slice 9: Second-Last Hardening and Review Slice

Scope:

1. perform full code review,
2. verify numerical determinism,
3. verify solver fallback,
4. verify objective/constraint traceability,
5. verify error handling,
6. verify OpenAPI quality,
7. verify latency and performance,
8. verify test pyramid adequacy,
9. remove dead code and duplicates.

Acceptance:

1. every Swagger field has description, type, and example,
2. every error path is tested,
3. generation latency is bounded and documented,
4. no duplicate or deprecated construction endpoints remain.

### Slice 10: Gateway and Workbench Realization RFC Slice

Scope:

1. create or tighten a paired Gateway RFC for DPM construction alternative composition after the
   manage APIs, evidence, supportability states, and selected-alternative contracts are stable,
2. create or tighten a paired Workbench RFC for the DPM construction lab / alternatives comparison
   UI after the Gateway composition needs are clear,
3. define how Gateway consumes manage alternatives without recomputing construction truth,
4. define how Workbench renders alternatives, comparison matrix, selected alternative, evidence,
   degraded states, and action gating,
5. define canonical demo proof across manage, gateway, and workbench,
6. explicitly record that current `lotus-manage` is not yet integrated with Gateway/Workbench for
   construction alternatives.

Acceptance:

1. Gateway RFC identifies the strategic endpoint family it will expose to Workbench.
2. Workbench RFC defines product journeys, screen anatomy, visual proof, accessibility, and
   Gateway-only consumption.
3. The RFCs are grounded in the implemented manage contracts and live evidence from Slices 8 and 9,
   not speculative payloads.
4. Manage RFC-0039 remains backend authority for alternatives; Gateway/Workbench do not own
   construction logic.
5. Full business outcome is explicitly not claimed until paired RFCs are implemented and live
   proven.

### Slice 11: Final Closure Slice

Scope:

1. update README, repository context, RFC index, wiki, and supported-features material,
2. update agent context or skills if reusable construction guidance emerges,
3. record final gold-pass assessment,
4. publish wiki after merge,
5. complete branch hygiene.

Acceptance:

1. documentation is useful to business, engineering, sales/pre-sales, marketing, operations, and
   client-demo audiences,
2. supported features are implementation-backed,
3. CI is green,
4. wiki check-only and post-merge publish are complete.

---

## 14. Test Pyramid

| Layer | Required proof |
| --- | --- |
| Unit | model validation, objective trace, constraint trace, comparison metrics, method registry |
| Pure engine | do-nothing, heuristic, min-turnover, source-aware method behavior |
| Solver | success, infeasible, timeout, unavailable, fallback |
| Enrichment | tax lots, turnover, liquidity, cost, FX, risk/performance degraded behavior |
| Repository | in-memory and PostgreSQL persistence, selection events, idempotent replay |
| API/contract | generate, retrieve, select, comparison, error paths, OpenAPI examples |
| Live | canonical portfolio alternatives with evidence package |
| Observability | metrics, logs, audit, support references, forbidden-field tests |
| Performance | bounded generation latency and fan-out timeout behavior |

Tests must validate real metrics, reason codes, and reconciliation. Status-code-only tests are not
enough.

---

## 15. Canonical Evidence Package

Implementation proof must produce a non-git-tracked evidence folder, for example:

`output/live-demo/<timestamp>/rfc0039-construction-alternatives/`

Required artifacts:

1. generate alternatives request/response,
2. retrieve alternative set request/response,
3. select alternative request/response,
4. optional comparison endpoint request/response,
5. alternative comparison matrix,
6. objective trace sample,
7. constraint trace sample,
8. infeasible example,
9. solver fallback example,
10. source-unavailable degraded example,
11. selected-alternative audit event sample,
12. OpenAPI/API certification summary,
13. latency summary,
14. critical review notes and fixes.

---

## 16. Supported-Features Ledger

| Feature | Support state before implementation | Promotion rule |
| --- | --- | --- |
| Alternative set generation | Proposed | Promote only after alternatives are persisted, comparable, and reproducible. |
| Do-nothing baseline | Proposed | Promote only after current-state comparison and no-trade evidence are proven. |
| Explainable heuristic alternative | Proposed | Promote only after reason-coded deterministic output is proven. |
| Minimum-turnover alternative | Proposed | Promote only after turnover, trade count, drift reduction, and cost trade-offs are tested. |
| Tax-aware construction | Proposed | Promote only after lot availability, lot selection, tax budget, and degraded-source behavior are proven. |
| Liquidity-aware construction | Proposed | Promote only after cash, settlement, liquidity, and cashflow-readiness evidence is complete. |
| Solver-constrained construction | Proposed | Promote only after solver status, objective terms, constraints, relaxations, infeasibility, and fallback are exposed. |
| Risk/performance-aware construction | Proposed | Promote only after enrichment seams or live integrations degrade truthfully when unavailable. |
| ESG/restriction-aware construction | Proposed | Promote only after restriction, sustainability, and eligibility evidence is complete. |
| Currency-overlay construction | Proposed | Promote only after FX exposure, hedge-ratio, FX funding, settlement, and hedge-blocking evidence exists. |
| Regime/stress-aware construction | Proposed | Promote only after scenario packs and stress contribution evidence are risk-authoritative. |
| Alternative selection | Proposed | Promote only after actor-attributed selection events are persisted and audited. |

---

## 17. Risks and Controls

| Risk | Control |
| --- | --- |
| Hidden optimizer behavior | Expose objective terms, constraints, relaxations, infeasibility, and fallback. |
| PM over-trusts a mathematically optimal but operationally poor result | Compare tax, turnover, liquidity, cost, source readiness, and blocked actions. |
| Manage duplicates risk/performance authority | Preserve enrichment boundaries and degrade when upstream authority is unavailable. |
| Missing tax/lot/liquidity data produces false readiness | Tax/liquidity methods cannot be `READY` when required source data is missing. |
| API sprawl | One strategic alternatives endpoint family; no aliases. |
| Solver non-determinism | Bounded time budgets, deterministic fallback, traceable solver version and tolerance. |
| Sensitive optimization traces leak | Bounded traces and forbidden-field tests. |
| Full business outcome not visible | Paired Gateway and Workbench RFCs are created after manage implementation proof and hardening, then implemented separately before any full product-outcome claim. |

---

## 18. Definition of Done

RFC-0039 is complete only when:

1. at least four first-wave methods are implemented and certified,
2. alternative sets are persisted and retrievable,
3. every alternative includes comparable decision metrics,
4. objective and constraint traces are complete,
5. solver/fallback/infeasibility behavior is explicit,
6. selected alternative is actor-attributed and audited,
7. OpenAPI is complete and certified,
8. live proof shows realistic discretionary mandate comparison for `PB_SG_GLOBAL_BAL_001`,
9. degraded-source behavior is tested,
10. no AI, Gateway, or UI layer chooses the alternative on behalf of the PM,
11. paired Gateway/Workbench RFCs have been created from stable manage contracts and live evidence for integration and full realization,
12. README/wiki/supported-features are updated truthfully,
13. CI is green,
14. wiki is published after merge,
15. branch and remote hygiene are clean.

---

## 19. Gold-Pass Assessment Template

To be completed during final closure:

| Assessment Area | Final Result |
| --- | --- |
| What was truly completed | TBD |
| Quality improvements made | TBD |
| Debt removed | TBD |
| Construction methods proven | TBD |
| Objective/constraint trace proof | TBD |
| Solver/fallback proof | TBD |
| Source-data and degraded proof | TBD |
| API certification result | TBD |
| Data mesh and observability result | TBD |
| Gateway/Workbench realization RFC result | TBD |
| Documentation/wiki result | TBD |
| Remaining governed follow-up | TBD |
| Gold-standard conclusion | TBD |

---

## 20. Relationship to Gateway and Workbench Realization

This RFC delivers manage-side construction alternatives. It does not by itself deliver the full
business outcome to users.

Full realization requires:

1. Gateway and Workbench realization RFCs created near the end of manage implementation, after
   manage API contracts, supportability behavior, and live evidence are stable enough to avoid
   speculative payloads,
2. a Gateway RFC that composes manage alternative sets into a Workbench-facing construction
   comparison contract,
3. a Workbench RFC that renders a DPM construction lab / alternatives comparison experience,
4. canonical proof across manage, gateway, and workbench,
5. documentation and wiki material useful for business, engineering, operations, sales/pre-sales,
   marketing, and client demos.

Until those paired RFCs are implemented and live-proven, `lotus-manage` may claim backend
construction-alternatives support only, not the complete front-office DPM construction experience.
