# RFC-0037: lotus-manage DPM Operating System and Mandate Intelligence

| Metadata | Details |
| --- | --- |
| **Status** | STRATEGIC PARENT ROADMAP - CHILD CAPABILITIES PARTIALLY IMPLEMENTED |
| **Created** | 2026-05-03 |
| **Depends On** | RFC-0001 through RFC-0013, RFC-0016 through RFC-0025, RFC-0028, RFC-0036, lotus-core RFC-0087 |
| **Doc Location** | `docs/rfcs/RFC-0037-dpm-operating-system-and-mandate-intelligence.md` |

---

## 0. Executive Summary

`lotus-manage` should become the Lotus ecosystem's management-side DPM operating system: the
backend authority for discretionary mandate portfolio management workflows, rebalance decisioning,
portfolio-manager controls, execution supportability, and mandate-level decision evidence.

The goal is not to build another calculator. The goal is to build a sellable, enterprise-grade,
front-office and investment-office platform that can support private-bank discretionary portfolio
management at scale.

The target product proposition:

1. every discretionary mandate is represented as a machine-readable digital twin,
2. every portfolio is continuously monitored against mandate, model, risk, liquidity, tax,
   sustainability, and operational constraints,
3. every rebalance is generated through an explainable and auditable construction process,
4. every exception is routed into a portfolio-manager command center,
5. every decision has a proof pack suitable for PM review, compliance review, operations,
   investment committee, client reporting, and audit,
6. every outcome is fed back into performance, risk, and future construction quality,
7. AI assists with summarization and evidence packaging without owning domain truth.

This RFC is deliberately ambitious. It defines a multi-slice roadmap to make `lotus-manage` the
"crown jewel" of Lotus by turning the existing rebalance engine into a full DPM operating platform.

Post-closure child work has implemented a substantial first-wave DPM product path across the RFC
family. RFC-0038, RFC-0039, RFC-0040, RFC-0041, and RFC-0042 now carry implementation-backed
backend authority and bounded Gateway/Workbench product realization for the canonical
front-office stack; report/render/archive and AI realization exist for the supported proof-pack,
wave, and outcome-review handoff paths; and `lotus-platform` owns the canonical DPM sales/demo
story through implementation-backed documentation and wiki truth. RFC-0037 remains a strategic
parent, not a single closed implementation. RFC-0043 governed PM copilot, richer source-owner
methodology depth, external OMS execution, PM scoring, client communication, and broader portfolio
memory are still future or partial scope.

---

## 1. Research Basis

### 1.1 External Market Benchmark

Public material from leading private banks shows a consistent DPM pattern:

| Market signal | Product implication for lotus-manage |
| --- | --- |
| Julius Baer describes discretionary mandates managed to agreed investment objectives, risk tolerance, guidelines, disciplined approach, monitoring, reviews, regular reporting, sustainability, bespoke mandates, CIO team involvement, and house-view-driven tactical decisions. | `lotus-manage` needs mandate digital twins, monitoring, review cadence, CIO model/house-view propagation, sustainability constraints, and recurring evidence/reporting. |
| Pictet frames discretionary management around goals, preferences, risk profile, constraints, assessing/designing/monitoring, global research, risk management, specialized strategies, dynamic opportunities, responsible investing, and bespoke strategies. | `lotus-manage` needs goal/risk/constraint capture, diversified construction, dynamic opportunity handling, responsible-investing controls, bespoke overlays, and monitoring. |
| Deutsche Bank positions DPM as modular, flexible, opportunity-aware, high-conviction, thematic, and resilient across market regimes. | `lotus-manage` needs modular strategy sleeves, tactical overlays, conviction and theme management, and market-regime scenario tools. |
| HSBC and DBS emphasize expert day-to-day portfolio management, risk appetite alignment, global opportunity access, mobile/digital DPM, defensive positioning, income streams, and mixed-asset mandates. | `lotus-manage` needs operational daily monitoring, digital transparency, income/liquidity objectives, defensive posture checks, and multi-asset support. |
| Citi and J.P. Morgan emphasize institutional resources, discipline, risk management, customized allocation, regular rebalancing, and transparent alignment. | `lotus-manage` needs investment-office integration, disciplined controls, customized allocation, systematic rebalancing, and explainable governance. |

### 1.2 Industry Methodology Basis

This RFC also incorporates established portfolio-management concepts:

1. the CFA portfolio-management process: objectives and constraints, asset allocation, security
   analysis, portfolio construction, monitoring/rebalancing, performance measurement, and reporting,
2. modern portfolio theory and Markowitz efficient-frontier reasoning as the baseline for risk/return
   trade-off thinking,
3. Black-Litterman as a practical framework for combining equilibrium portfolios with subjective or
   house views,
4. active portfolio management concepts such as active risk, tracking error, information ratio,
   breadth, transfer coefficient, and benchmark-relative discipline,
5. factor investing concepts that focus on underlying risk premia rather than only asset-class
   labels,
6. real-world constraint management: taxes, liquidity, regulation, minimum trade sizes, turnover,
   cash needs, currency, ESG/sustainability, concentration, market access, and operational readiness.

### 1.3 Lotus Ecosystem Context

`lotus-manage` must become powerful by orchestrating the ecosystem, not by duplicating it:

| Lotus app | Role in the target DPM operating system |
| --- | --- |
| `lotus-core` | Source of truth for portfolios, accounts, holdings, transactions, tax lots, cash, prices, FX, mandate bindings, model targets, eligibility, and source readiness. |
| `lotus-risk` | Authority for ex-ante risk, drawdown, concentration, stress, historical risk, and risk decomposition. |
| `lotus-performance` | Authority for returns, contribution, attribution, benchmarks, execution tracking, and realized outcome measurement. |
| `lotus-advise` | Advisor-led proposal, consent, client decision, and recommendation lifecycle. |
| `lotus-report` | Client, PM, investment committee, and audit report pack composition. |
| `lotus-ai` | Governed AI summaries, PM memos, exception narratives, evidence explanations, and review support. |
| `lotus-gateway` | Experience API composition and partial-readiness-aware product boundary. |
| `lotus-workbench` | Portfolio manager, advisor, operations, and leadership user experience. |

### 1.4 Domain Vocabulary and Design Normalization

This RFC family must use private-banking and institutional portfolio-management vocabulary. The
implementation should not read like a generic task tracker wrapped around a rebalance API.

Preferred language:

| Domain concept | Preferred Lotus term | Avoid |
| --- | --- | --- |
| Client-authorized DPM scope | discretionary mandate, investment mandate, mandate policy statement | generic account settings |
| Long-term policy allocation | strategic asset allocation, model portfolio, policy portfolio | target mix with no governance context |
| Short-term CIO or PM tilt | tactical asset allocation, house-view tilt, CIO model change | manual adjustment |
| Governed constraint set | mandate guidelines, investment restrictions, policy bands, hard/soft limits | arbitrary rules |
| Ongoing supervision | mandate monitoring, exception surveillance, review cadence | background scan |
| Rebalance decision | portfolio action, rebalance proposal, selected alternative | generated suggestion |
| Analytical comparison | construction alternative, risk/return/tax/liquidity trade-off | option list |
| Multi-currency control | reference currency, currency exposure, FX funding, hedge overlay | currency conversion only |
| Evidence record | proof pack, source lineage, decision timeline, audit artifact | log dump |
| Outcome review | expected-versus-realized review, post-trade feedback, execution-quality review | after-action note |
| AI role | governed PM copilot, narrative assistant, evidence summarizer | autonomous decision agent |
| Readiness posture | source readiness, supportability, degraded state, blocked state | success/failure flag |

Methodology anchors:

1. mandates should start from objectives, risk profile, time horizon, reference currency, liquidity
   needs, tax position, regulatory constraints, sustainability preferences, and bespoke
   restrictions,
2. construction should distinguish strategic allocation discipline from tactical or dynamic tilts,
3. construction and rebalancing must expose transaction cost, taxation, liquidity, risk, active
   risk/tracking error, concentration, currency exposure, and operational readiness,
4. scenario/stress analysis should be treated as a portfolio-construction and review control, not
   as a decorative chart,
5. portfolio memory should preserve decision rights, actor attribution, source lineage, and
   expected-versus-realized outcome evidence,
6. AI must consume structured evidence and never become the source of investment truth.

---

## 2. Problem Statement

The current `lotus-manage` implementation is materially stronger than an MVP. It has a certified
rebalance surface, stateless and stateful execution envelopes, core source-data integration,
idempotency, supportability, workflow review, artifacts, policy packs, OpenAPI certification, and
test-pyramid governance.

However, the product is still centered on rebalance simulation. A market-leading DPM platform must
support the full lifecycle:

1. mandate onboarding and change management,
2. model and house-view governance,
3. continuous monitoring and exception detection,
4. portfolio construction and optimization,
5. rebalance wave orchestration,
6. pre-trade evidence and approval,
7. execution support and post-trade feedback,
8. performance/risk outcome learning,
9. client and internal reporting,
10. sales/demo storytelling.

Without this broader operating-system layer, `lotus-manage` risks being perceived as a technical
engine instead of a premium private-banking DPM product.

## 2.5 Business Outcomes

This RFC targets the following business outcomes:

1. **Increase DPM scalability**
   enable one portfolio manager to oversee a larger book through exception-based monitoring,
   mandate health scoring, and wave orchestration instead of manual portfolio-by-portfolio review.
2. **Improve investment discipline**
   make every rebalance traceable to mandate objectives, CIO/model guidance, risk limits, tax and
   liquidity constraints, and product eligibility.
3. **Strengthen client and regulator trust**
   produce evidence that explains why a discretionary action was proposed, approved, blocked, or
   deferred.
4. **Create a premium sales story**
   demonstrate a full private-banking DPM lifecycle with real APIs, real evidence, and realistic
   mandate scenarios.
5. **Increase ecosystem pull-through**
   make `lotus-core`, `lotus-risk`, `lotus-performance`, `lotus-report`, `lotus-ai`,
   `lotus-gateway`, and `lotus-workbench` more valuable by orchestrating them into a coherent DPM
   product.
6. **Reduce operational risk**
   replace spreadsheet-style exception tracking with governed workflows, supportability, lineage,
   data-readiness states, and audit artifacts.
7. **Improve decision quality over time**
   use post-trade outcome feedback to compare expected versus realized results and improve future
   construction and governance.

---

## 3. Product Vision

### 3.1 One-Sentence Vision

`lotus-manage` is the portfolio manager's operating system for discretionary mandates: it tells the
PM what needs attention, why it matters, what actions are allowed, what action is optimal, what the
evidence says, and what happened after action.

### 3.2 Product Promises

1. **Trust:** every recommendation is explainable, auditable, lineage-backed, and reproducible.
2. **Control:** every action stays inside mandate, policy, risk, tax, liquidity, and operational
   guardrails.
3. **Personalization:** every mandate can reflect client objectives, preferences, exclusions,
   liquidity needs, tax posture, and sustainability constraints.
4. **Scale:** one PM can oversee many mandates through exception-based monitoring and wave
   orchestration.
5. **Differentiation:** the platform can show sophisticated construction, risk, performance,
   sustainability, and narrative evidence in a demo-ready way.
6. **Ecosystem leverage:** `lotus-manage` activates the value of `lotus-core`, `lotus-risk`,
   `lotus-performance`, `lotus-report`, `lotus-ai`, `lotus-gateway`, and `lotus-workbench`.

### 3.3 Product Non-Promises

1. `lotus-manage` does not provide advisor-led proposal consent workflows; that belongs to
   `lotus-advise`.
2. `lotus-manage` does not become the system of record for holdings, transactions, tax lots, or
   market data; that belongs to `lotus-core`.
3. `lotus-manage` does not become the risk engine; that belongs to `lotus-risk`.
4. `lotus-manage` does not become the performance attribution engine; that belongs to
   `lotus-performance`.
5. `lotus-manage` does not let AI choose trades. AI may summarize, explain, check, and prepare
   evidence, but deterministic domain services remain authoritative.

### 3.4 Compatibility Posture

This RFC family is a strategic revamp, not a backward-compatible extension of the current
management API set.

Current assumption:

1. no downstream system is production-dependent on the target-state RFC-0037 through RFC-0043
   surfaces,
2. future `lotus-gateway` and `lotus-workbench` integration will be rebuilt against the certified
   target contract,
3. stale, duplicate, advisory-era, or misleading endpoints should be removed rather than wrapped,
4. compatibility aliases should not be introduced unless a later downstream migration RFC proves a
   real production dependency,
5. the target contract should optimize for domain correctness, API quality, observability,
   supportability, and evidence, not legacy payload shape preservation.

Implementation rule:

1. if downstream usage is discovered during implementation, document the consumer and migration
   plan,
2. prefer a short-lived migration issue over permanent compatibility code,
3. keep the strategic endpoint vocabulary clean even when a downstream adapter is temporarily
   required elsewhere,
4. redesign current APIs where needed to create a coherent enterprise-grade contract,
5. delete duplicate or poorly named endpoints instead of preserving them as aliases,
6. certify the new contract through OpenAPI, tests, live evidence, and supported-feature updates
   before gateway or Workbench integration is rebuilt.

---

## 4. Target Personas

### 4.1 Portfolio Manager

Needs:

1. see every mandate requiring attention,
2. understand why each mandate is out of line,
3. compare rebalance alternatives quickly,
4. approve or reject actions with evidence,
5. batch similar actions across many accounts,
6. defend decisions to CIO, compliance, operations, and clients.

### 4.2 Investment Committee / CIO Office

Needs:

1. publish house views and tactical tilts,
2. understand affected mandates,
3. approve model changes and rebalance waves,
4. monitor implementation progress,
5. review realized impact after execution.

### 4.3 Operations

Needs:

1. know which runs are ready, blocked, stale, or partially executable,
2. understand missing data and upstream readiness gaps,
3. track execution handoff state,
4. support incident investigation with lineage and deterministic artifacts.

### 4.4 Compliance / Risk Oversight

Needs:

1. verify mandate adherence,
2. inspect rule breaches and approvals,
3. prove suitability boundaries for discretionary authority,
4. review concentration, liquidity, tax, ESG, and restricted-instrument controls.

### 4.5 Advisor / Relationship Manager

Needs:

1. understand what the PM is doing and why,
2. explain performance, risk, and mandate adherence to clients,
3. know when a change requires client discussion or proposal flow in `lotus-advise`.

### 4.6 Sales / Demo Team

Needs:

1. compelling demo stories,
2. business-friendly feature narratives,
3. proof that Lotus is enterprise-grade,
4. visible cross-app ecosystem value.

---

## 5. Target Product Capability Map

### 5.1 Capability Layers

1. **Mandate Intelligence Layer**
   machine-readable mandate digital twin, objectives, constraints, review cadence, policy overlays.
2. **Construction Layer**
   model targets, house views, solver-based optimization, overlays, tax/turnover/liquidity controls.
3. **Monitoring Layer**
   continuous drift, risk, performance, liquidity, tax, ESG, data-quality, and operational checks.
4. **Decision Layer**
   alternatives, proof packs, explainability, review gates, approval workflows.
5. **Execution-Support Layer**
   rebalance waves, staging, execution handoff, operation state, exception handling.
6. **Feedback Layer**
   realized performance/risk/turnover/tax/cost outcomes, decision learning, PM quality metrics.
7. **Experience Layer**
   Workbench command center, PM cockpit, CIO cockpit, operations cockpit, demo-ready narratives.

### 5.2 Capability Ownership

| Capability | Owner | Notes |
| --- | --- | --- |
| Mandate digital twin | `lotus-manage` owns derived DPM contract; `lotus-core` owns source mandate binding data | Manage may persist DPM-specific interpretation and change history. |
| Portfolio state and tax lots | `lotus-core` | Manage consumes governed source products. |
| Rebalance construction | `lotus-manage` | Strategic owner of DPM action generation. |
| Risk analytics | `lotus-risk` | Manage requests and embeds risk evidence. |
| Performance analytics | `lotus-performance` | Manage uses outcomes and attribution evidence. |
| Report packs | `lotus-report` | Manage supplies decision proof and receives generated report refs. |
| AI explanations | `lotus-ai` | AI consumes structured evidence; it does not create domain truth. |
| UI cockpit | `lotus-workbench` via `lotus-gateway` | Gateway composes product-ready payloads. |

---

## 6. Feature Set

### 6.1 Feature 1 - Mandate Digital Twin

Create a first-class DPM mandate object used by every stateful execution and monitoring workflow.

Minimum fields:

1. `mandate_id`
2. `portfolio_id`
3. `client_segment`
4. `jurisdiction`
5. `base_currency`
6. `reference_currency`
7. `risk_profile`
8. `investment_objective`
9. `time_horizon`
10. `income_objective`
11. `liquidity_requirement`
12. `cash_buffer_min_weight`
13. `cash_buffer_max_weight`
14. `model_portfolio_id`
15. `benchmark_id`
16. `strategic_asset_allocation`
17. `tactical_asset_allocation_limits`
18. `max_single_position_weight`
19. `max_issuer_weight`
20. `max_sector_weight`
21. `max_region_weight`
22. `max_currency_exposure`
23. `max_tracking_error`
24. `max_active_share`
25. `max_turnover`
26. `tax_budget`
27. `realized_gain_preference`
28. `restricted_instruments`
29. `restricted_issuers`
30. `restricted_sectors`
31. `allowed_product_types`
32. `esg_strategy`
33. `sustainability_exclusions`
34. `minimum_trade_notional`
35. `rounding_policy`
36. `lot_selection_policy`
37. `review_cadence`
38. `last_reviewed_at`
39. `next_review_due_at`
40. `effective_from`
41. `effective_to`
42. `source_lineage`

The digital twin must support:

1. source-data lineage from `lotus-core`,
2. PM-approved overlays,
3. versioning,
4. change reason codes,
5. audit diff between mandate versions,
6. compatibility with stateless and stateful execution,
7. explainable flattening into engine options and policy packs.

### 6.2 Feature 2 - Mandate Health Score

Create a normalized health score for each discretionary mandate.

Score dimensions:

1. allocation drift,
2. cash drag,
3. risk drift,
4. concentration risk,
5. liquidity readiness,
6. tax budget usage,
7. turnover budget usage,
8. performance deviation,
9. model freshness,
10. price/FX/source-data readiness,
11. ESG or restriction breaches,
12. workflow or approval blockage,
13. stale review cadence.

Output:

1. `health_score` from 0 to 100,
2. `health_state` as `READY`, `PENDING_REVIEW`, or `BLOCKED`,
3. top three reasons,
4. action recommendation,
5. source-data posture,
6. evidence links.

Rules:

1. hard mandate breach forces `BLOCKED`,
2. soft breach or stale review forces `PENDING_REVIEW`,
3. score should be decomposable by dimension,
4. no opaque score without reason contributions,
5. score should be stable under unchanged inputs.

### 6.3 Feature 3 - DPM Command Center

Create a backend command-center API for Workbench:

1. portfolio-manager book view,
2. mandate health summary,
3. exception queue,
4. rebalance readiness,
5. stale data queue,
6. approval queue,
7. wave execution status,
8. PM action workload,
9. CIO model-change impact,
10. operations supportability posture.

Example buckets:

1. `REBALANCE_READY`
2. `DRIFT_ATTENTION`
3. `RISK_ATTENTION`
4. `CASH_ATTENTION`
5. `DATA_BLOCKED`
6. `POLICY_BLOCKED`
7. `APPROVAL_REQUIRED`
8. `EXECUTION_PENDING`
9. `POST_TRADE_REVIEW_DUE`

The command center should be an API product, not only a UI concept.

### 6.4 Feature 4 - CIO House-View and Model Change Propagation

Allow CIO/model teams to publish:

1. strategic model changes,
2. tactical tilts,
3. high-conviction themes,
4. asset-class overweight/underweight views,
5. region/currency/sector views,
6. risk-on/risk-off posture,
7. effective dates,
8. review and expiry dates,
9. affected model portfolios,
10. rationale and source materials.

`lotus-manage` should calculate:

1. affected mandates,
2. expected trade waves,
3. aggregate notional by instrument/currency,
4. expected risk and tracking-error changes,
5. liquidity and capacity issues,
6. tax and turnover impact,
7. exceptions and blocked portfolios,
8. PM approval workload.

### 6.5 Feature 5 - Advanced Portfolio Construction Lab

Move from simple target generation toward a production-grade construction layer.

Objective function components:

1. minimize distance to target model,
2. minimize tracking error,
3. minimize turnover,
4. minimize transaction costs,
5. minimize realized tax,
6. minimize cash drag,
7. maximize expected active return where permitted,
8. preserve liquidity buffer,
9. prefer higher-conviction instruments,
10. penalize concentration and restricted exposures.

Constraint families:

1. asset class weights,
2. instrument weights,
3. issuer weights,
4. sector weights,
5. geography weights,
6. currency exposure,
7. credit quality,
8. duration,
9. liquidity buckets,
10. ESG ratings and exclusions,
11. tax realization budget,
12. turnover budget,
13. minimum trade notional,
14. lot-size or round-lot rules,
15. cash bands,
16. no-shorting,
17. no-overdraft,
18. settlement cash ladder,
19. client-specific restrictions,
20. product-shelf eligibility.

Construction modes:

1. `HEURISTIC_EXPLAINABLE`
2. `SOLVER_CONSTRAINED`
3. `BLACK_LITTERMAN_VIEW_BLEND`
4. `TAX_AWARE`
5. `LIQUIDITY_AWARE`
6. `ESG_AWARE`
7. `STRESS_AWARE`

Solver governance:

1. solver inputs must be persisted in artifact,
2. solver status must be exposed,
3. infeasible constraints must be explained,
4. fallback path must be deterministic,
5. no silent relaxation without explicit reason code,
6. every relaxed constraint must be included in evidence,
7. solver time budget must be bounded,
8. solver dependency health must affect capability contract.

### 6.6 Feature 6 - Rebalance Alternatives

For each mandate, generate multiple alternatives:

1. minimal-turnover rebalance,
2. full model alignment,
3. tax-aware rebalance,
4. risk-reducing rebalance,
5. liquidity-preserving rebalance,
6. ESG-compliant rebalance,
7. PM custom overlay rebalance,
8. do-nothing baseline.

Each alternative must include:

1. expected drift reduction,
2. expected risk change,
3. expected performance attribution impact,
4. estimated transaction cost,
5. estimated realized gain/loss,
6. turnover,
7. number of trades,
8. FX requirements,
9. rule outcomes,
10. data readiness,
11. approval requirement,
12. explanation.

### 6.7 Feature 7 - Pre-Trade Proof Pack

Every proposed rebalance should produce a proof pack.

Required sections:

1. decision summary,
2. mandate context,
3. before state,
4. target state,
5. proposed trades,
6. after state,
7. drift reduction,
8. risk impact,
9. performance/benchmark context,
10. tax impact,
11. turnover and cost impact,
12. liquidity impact,
13. FX funding plan,
14. rule results,
15. blocked/soft exceptions,
16. source-data readiness,
17. lineage,
18. PM approval checklist,
19. operations handoff checklist,
20. AI-generated PM memo reference where enabled.

Proof pack outputs:

1. JSON artifact,
2. Markdown summary,
3. report-package input for `lotus-report`,
4. AI narrative input for `lotus-ai`,
5. Workbench display payload through `lotus-gateway`.

### 6.8 Feature 8 - Rebalance Wave Orchestration

Create batch-level orchestration for many mandates.

Wave dimensions:

1. model portfolio,
2. mandate type,
3. risk profile,
4. region,
5. base currency,
6. PM book,
7. CIO change event,
8. data readiness,
9. execution venue or operational window,
10. client segment.

Wave states:

1. `DRAFT`
2. `SOURCE_CHECK`
3. `SIMULATING`
4. `REVIEWING`
5. `APPROVED`
6. `STAGED`
7. `HANDOFF_READY`
8. `HANDOFF_SENT`
9. `PARTIALLY_COMPLETED`
10. `COMPLETED`
11. `CANCELLED`
12. `FAILED`

Wave APIs must support:

1. create wave,
2. preview affected portfolios,
3. source readiness check,
4. simulate all,
5. compare alternatives,
6. approve selected alternatives,
7. stage operations,
8. export/handoff package,
9. pause/resume/cancel,
10. retry failed items,
11. search wave items,
12. produce wave proof pack.

Top-level run statuses must still use current RFC conventions for individual simulations:
`READY`, `PENDING_REVIEW`, `BLOCKED`.

### 6.9 Feature 9 - Continuous Mandate Monitoring

Introduce scheduled monitoring jobs:

1. daily drift scan,
2. market-data freshness scan,
3. source-readiness scan,
4. risk breach scan,
5. cash drag scan,
6. tax budget scan,
7. liquidity event scan,
8. model staleness scan,
9. review cadence scan,
10. ESG/restriction scan,
11. post-trade outcome scan.

Monitoring output:

1. exception id,
2. mandate id,
3. portfolio id,
4. severity,
5. reason code,
6. measured value,
7. threshold,
8. source timestamp,
9. recommended next action,
10. link to simulation/proof pack if generated.

### 6.10 Feature 10 - Post-Trade Outcome Feedback

After execution, `lotus-manage` should compare expected versus realized outcomes.

Metrics:

1. expected vs realized drift reduction,
2. expected vs realized risk change,
3. expected vs realized turnover,
4. expected vs realized transaction cost,
5. tax realization variance,
6. cash residual variance,
7. execution slippage,
8. partial-fill impact,
9. benchmark-relative impact,
10. attribution since rebalance.

Inputs:

1. execution or transaction records from `lotus-core`,
2. performance from `lotus-performance`,
3. risk from `lotus-risk`,
4. proof pack from `lotus-manage`,
5. report materialization from `lotus-report`.

### 6.11 Feature 11 - PM Copilot Through lotus-ai

AI should assist, not decide.

Allowed AI outputs:

1. PM memo draft,
2. exception summary,
3. proof-pack narrative,
4. client-safe explanation draft,
5. investment-committee meeting summary,
6. blocked-run triage summary,
7. change-impact summary,
8. operations handoff summary.

Forbidden AI outputs:

1. direct trade decisions,
2. hidden model weights,
3. replacing rule-engine results,
4. replacing risk calculations,
5. replacing suitability or mandate validation,
6. inventing missing data,
7. changing approval state.

AI governance:

1. prompts registered in `lotus-ai`,
2. structured evidence input only,
3. bounded output schema,
4. safety checks,
5. model/provider policy,
6. review and provenance state,
7. no PII or sensitive payload labels in telemetry,
8. deterministic fallback when AI unavailable.

### 6.12 Feature 12 - DPM Sales and Client-Demo Mode

Create implementation-backed demo stories:

1. balanced mandate drift after CIO model change,
2. tax-aware rebalance with HIFO lot selection,
3. multi-currency FX funding and hedge explanation,
4. ESG/sustainability restriction handling,
5. risk breach and mitigation alternative,
6. cash drag and income objective alignment,
7. volatile-market defensive repositioning,
8. rebalance wave across PM book,
9. post-trade outcome review,
10. AI PM memo generated from proof pack.

Demo rules:

1. no fake unsupported features,
2. every demo state backed by APIs,
3. every screenshot backed by canonical stack evidence,
4. every business claim backed by source data and proof artifacts,
5. demo data must include realistic DPM mandates, not only simple portfolios.

### 6.13 Feature 13 - Currency Overlay and Hedge Governance

Currency exposure is a first-class mandate dimension, not only a cash-conversion detail.

Required capabilities:

1. derive base-currency, local-currency, and settlement-currency exposure from `lotus-core`,
2. compare unhedged, partially hedged, and fully hedged rebalance alternatives,
3. support mandate-level hedge ratio bands by currency, asset class, sleeve, and instrument type,
4. show expected cash, FX, cost, liquidity, and settlement effects before a plan is approved,
5. identify when hedge instruments, FX rates, forward points, or settlement calendars are missing,
6. distinguish strategic currency exposure from operational FX needed to fund trades,
7. preserve deterministic reason codes for hedge suppression, hedge adjustment, and hedge breach.

Business outcome:

1. PMs can manage multi-currency mandates with clear risk, funding, and hedge evidence,
2. operations can see settlement and funding readiness before trade staging,
3. client-facing material can explain currency posture without reconstructing it from raw trades.

### 6.14 Feature 14 - Market-Regime and Stress Simulator

The platform must help a PM understand how a mandate behaves under plausible regime changes before
action is taken.

Required capabilities:

1. consume stress, drawdown, concentration, and exposure data from `lotus-risk`,
2. support named scenario packs such as rate shock, equity sell-off, credit widening, USD rally,
   commodity shock, inflation surprise, liquidity freeze, and defensive-risk-off rotation,
3. compare current, target, and alternative portfolios under the same scenario set,
4. expose scenario loss, drawdown contribution, breached limits, and mitigation trades,
5. allow CIO model-change waves to carry required scenario checks,
6. mark results degraded when a scenario pack, risk model, or exposure dimension is unavailable,
7. keep scenario evidence in proof packs and post-trade outcome reviews.

Business outcome:

1. investment-office users can demonstrate disciplined regime-aware construction,
2. PMs can avoid alternatives that improve drift while worsening unacceptable tail exposure,
3. risk and compliance reviewers can inspect scenario evidence before approval.

### 6.15 Feature 15 - Portfolio Memory and Decision Timeline

`lotus-manage` must remember why decisions were made, not only what the latest run produced.

Required capabilities:

1. maintain a portfolio-level timeline of mandate changes, monitoring exceptions, model-change
   impacts, alternative sets, selected alternatives, proof packs, approvals, deferrals, wave states,
   execution handoffs, and outcome reviews,
2. link every timeline event to source lineage, actor, reason, status vocabulary, and artifacts,
3. support PM, operations, compliance, CIO, and audit views over the same event record,
4. distinguish automated observations from human decisions,
5. expose decision memory to `lotus-ai` only through structured evidence packs,
6. provide before/after and expected/realized context for future construction quality analysis,
7. retain enough history to support client review, complaint handling, and internal supervision.

Business outcome:

1. PMs can explain the lifecycle of a mandate without manually stitching together run records,
2. supervisors can review whether decisions were timely, disciplined, and mandate-consistent,
3. future AI and analytics features have a governed memory substrate instead of inferred context.

---

## 7. Target Data Products

### 7.1 Required Inputs from lotus-core

Existing RFC-0087 products remain required:

1. `DpmModelPortfolioTarget:v1`
2. `DiscretionaryMandateBinding:v1`
3. `InstrumentEligibilityProfile:v1`
4. `PortfolioTaxLotWindow:v1`
5. `MarketDataCoverageWindow:v1`
6. `DpmSourceReadiness:v1`

Additional target products likely required:

1. `MandateDigitalTwinSource:v1`
2. `PortfolioCashflowForecast:v1`
3. `ExecutionFillWindow:v1`
4. `TransactionCostSchedule:v1`
5. `InstrumentLiquidityProfile:v1`
6. `SecurityReferenceEnrichment:v1`
7. `SustainabilityProfile:v1`
8. `ClientRestrictionProfile:v1`
9. `ModelChangeEvent:v1`
10. `BenchmarkConstituentWindow:v1`
11. `PortfolioCurrencyExposureWindow:v1`
12. `CurrencyOverlayPolicy:v1`
13. `HedgingInstrumentProfile:v1`
14. `StressScenarioPack:v1`
15. `MarketRegimeSignal:v1`

### 7.2 Required Inputs from lotus-risk

1. ex-ante risk summary,
2. concentration breakdown,
3. drawdown and stress summary,
4. factor or exposure decomposition when implemented,
5. risk impact for proposed alternatives,
6. risk breach reason codes.

### 7.3 Required Inputs from lotus-performance

1. benchmark-aware returns,
2. contribution and attribution,
3. realized outcome after rebalance,
4. performance deviation from mandate/benchmark,
5. post-trade feedback inputs.

### 7.4 Required Outputs from lotus-manage

Potential governed data products:

1. `DpmMandateDigitalTwin:v1`
2. `DpmMandateHealthSnapshot:v1`
3. `DpmRebalanceAlternativeSet:v1`
4. `DpmPreTradeProofPack:v1`
5. `DpmRebalanceWave:v1`
6. `DpmPortfolioActionRegister:v2`
7. `DpmPostTradeOutcomeReview:v1`
8. `DpmCioModelChangeImpact:v1`
9. `DpmCurrencyOverlayPlan:v1`
10. `DpmScenarioImpactRun:v1`
11. `DpmDecisionTimeline:v1`

---

## 8. Proposed API Surface

All public APIs must use `/api/v1`.

### 8.1 Mandate Intelligence

1. `GET /api/v1/mandates/{mandate_id}`
2. `GET /api/v1/mandates/by-portfolio/{portfolio_id}`
3. `GET /api/v1/mandates/{mandate_id}/versions`
4. `GET /api/v1/mandates/{mandate_id}/diff?from_version=&to_version=`
5. `POST /api/v1/mandates/{mandate_id}/refresh-from-core`
6. `GET /api/v1/mandates/{mandate_id}/health`
7. `GET /api/v1/mandates/{mandate_id}/exceptions`

### 8.2 Monitoring and Command Center

1. `GET /api/v1/dpm/command-center`
2. `GET /api/v1/dpm/exceptions`
3. `GET /api/v1/dpm/monitoring/runs`
4. `POST /api/v1/dpm/monitoring/run-once`
5. `GET /api/v1/dpm/books/{portfolio_manager_id}/health`

### 8.3 Construction and Alternatives

1. `POST /api/v1/rebalance/alternatives`
2. `GET /api/v1/rebalance/alternatives/{alternative_set_id}`
3. `POST /api/v1/rebalance/alternatives/{alternative_set_id}/select`
4. `POST /api/v1/rebalance/proof-packs`
5. `GET /api/v1/rebalance/proof-packs/{proof_pack_id}`

### 8.4 Rebalance Waves

1. `POST /api/v1/rebalance/waves`
2. `GET /api/v1/rebalance/waves`
3. `GET /api/v1/rebalance/waves/{wave_id}`
4. `POST /api/v1/rebalance/waves/{wave_id}/source-check`
5. `POST /api/v1/rebalance/waves/{wave_id}/simulate`
6. `POST /api/v1/rebalance/waves/{wave_id}/approve`
7. `POST /api/v1/rebalance/waves/{wave_id}/stage`
8. `POST /api/v1/rebalance/waves/{wave_id}/handoff`
9. `POST /api/v1/rebalance/waves/{wave_id}/cancel`
10. `GET /api/v1/rebalance/waves/{wave_id}/items`
11. `GET /api/v1/rebalance/waves/{wave_id}/proof-pack`

### 8.5 Post-Trade Feedback

1. `POST /api/v1/rebalance/outcome-reviews`
2. `GET /api/v1/rebalance/outcome-reviews/{review_id}`
3. `GET /api/v1/rebalance/runs/{rebalance_run_id}/outcome-review`

### 8.6 AI-Assisted Evidence

1. `POST /api/v1/rebalance/proof-packs/{proof_pack_id}/pm-memo`
2. `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/pm-memo`

These routes would call `lotus-ai` workflow-pack execution seams and persist returned run posture.

### 8.7 Currency Overlay

1. `POST /api/v1/currency-overlays/simulate`
2. `GET /api/v1/currency-overlays/{overlay_plan_id}`
3. `POST /api/v1/currency-overlays/{overlay_plan_id}/select`

These routes expose currency posture and hedge-governance evidence as part of construction and
proof-pack workflows. They must not become independent FX-trading APIs.

### 8.8 Regime and Stress Simulation

1. `POST /api/v1/scenarios/impact-runs`
2. `GET /api/v1/scenarios/impact-runs/{scenario_run_id}`
3. `GET /api/v1/scenarios/packs`

These routes consume risk-authoritative scenario packs and expose mandate-ready impact evidence for
alternatives, waves, proof packs, and outcome reviews.

### 8.9 Decision Timeline

1. `GET /api/v1/portfolios/{portfolio_id}/decision-timeline`
2. `GET /api/v1/mandates/{mandate_id}/decision-timeline`
3. `GET /api/v1/decision-events/{decision_event_id}`

These routes provide portfolio memory for PM, compliance, operations, CIO, report, and AI evidence
workflows. Timeline APIs return decision facts and evidence refs, not AI-generated interpretation.

---

## 9. Domain Model Sketches

### 9.1 Mandate Digital Twin

```json
{
  "mandate_id": "mandate_pb_balanced_sgd_001",
  "portfolio_id": "PB_SG_GLOBAL_BAL_001",
  "mandate_version": "2026-05-03T00:00:00Z",
  "base_currency": "SGD",
  "reference_currency": "SGD",
  "risk_profile": "BALANCED",
  "investment_objective": "LONG_TERM_TOTAL_RETURN",
  "liquidity_requirement": {
    "cash_buffer_min_weight": "0.02",
    "cash_buffer_max_weight": "0.08",
    "known_cash_needs": []
  },
  "model_binding": {
    "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
    "benchmark_id": "BENCH_GLOBAL_BALANCED_SGD"
  },
  "constraints": {
    "single_position_max_weight": "0.10",
    "issuer_max_weight": "0.15",
    "turnover_budget": "0.20",
    "max_tracking_error": "0.05",
    "tax_budget": {
      "max_realized_gain_base": {"amount": "50000.00", "currency": "SGD"}
    }
  },
  "sustainability": {
    "strategy": "ESG_LEADERS",
    "excluded_sectors": ["TOBACCO", "CONTROVERSIAL_WEAPONS"]
  },
  "source_lineage": {
    "source_system": "lotus-core",
    "source_product": "DiscretionaryMandateBinding:v1"
  }
}
```

### 9.2 Mandate Health Snapshot

```json
{
  "portfolio_id": "PB_SG_GLOBAL_BAL_001",
  "mandate_id": "mandate_pb_balanced_sgd_001",
  "as_of_date": "2026-05-03",
  "health_score": 82,
  "health_state": "PENDING_REVIEW",
  "top_reasons": [
    {"reason_code": "ALLOCATION_DRIFT", "severity": "SOFT"},
    {"reason_code": "CASH_ABOVE_BAND", "severity": "SOFT"}
  ],
  "dimension_scores": [
    {"dimension": "DRIFT", "score": 68},
    {"dimension": "RISK", "score": 91},
    {"dimension": "DATA_READINESS", "score": 100}
  ],
  "recommended_action": "SIMULATE_REBALANCE",
  "evidence_refs": []
}
```

### 9.3 Rebalance Alternative

```json
{
  "alternative_id": "alt_min_turnover_001",
  "alternative_type": "MIN_TURNOVER",
  "status": "READY",
  "objective_summary": {
    "drift_reduction_pct": "0.72",
    "turnover_weight": "0.06",
    "estimated_cost_base": {"amount": "830.00", "currency": "SGD"},
    "estimated_tax_realized_base": {"amount": "4200.00", "currency": "SGD"}
  },
  "risk_impact": {
    "tracking_error_before": "0.041",
    "tracking_error_after": "0.034"
  },
  "rule_results": [],
  "intents": [],
  "explanation": {
    "summary": "Reduces allocation drift while preserving tax and turnover budgets."
  }
}
```

---

## 10. Implementation Slices

### Slice 0 - RFC Proof, Feature Inventory, and Market-Backed Product Baseline

Deliverables:

1. finalize this RFC,
2. update README/wiki product positioning,
3. create implementation-backed feature inventory,
4. map each target feature to owning Lotus apps,
5. identify source-data gaps and upstream RFCs,
6. define demo story inventory.

Acceptance criteria:

1. RFC is approved,
2. supported-features list distinguishes current vs target-state features,
3. wiki explains the DPM operating-system roadmap for business, sales, dev, ops, and clients,
4. no target-state claim is presented as implemented.

### Slice 1 - Mandate Digital Twin Foundation

Deliverables:

1. DPM mandate domain model,
2. source resolver from `lotus-core` mandate products,
3. versioning and diff semantics,
4. mandate-to-engine-options compiler,
5. mandate API surface,
6. tests across default, bespoke, restricted, ESG, tax-aware, and liquidity-heavy mandates.

Acceptance criteria:

1. every stateful rebalance can attach a mandate twin,
2. no simulation runs without explicit mandate source posture,
3. mandate changes are traceable and reproducible,
4. OpenAPI fully documents all mandate fields.

### Slice 2 - Mandate Health and Continuous Monitoring

Deliverables:

1. health score engine,
2. exception taxonomy,
3. monitoring job model,
4. command-center summary API,
5. source-readiness integration,
6. tests for stale, blocked, soft-review, and ready states.

Acceptance criteria:

1. a PM can see which mandates need attention without manually running simulations,
2. health score is decomposed and explainable,
3. monitoring results persist with lineage,
4. degraded upstream data produces truthful states.

### Slice 3 - Advanced Construction and Alternatives

Deliverables:

1. alternative-set model,
2. solver objective registry,
3. constraint registry,
4. target method governance,
5. tax-aware and turnover-aware alternatives,
6. explainability for infeasible or relaxed constraints.

Acceptance criteria:

1. at least four alternatives can be generated for a canonical portfolio,
2. every alternative has measurable trade-offs,
3. solver mode is bounded, tested, and explainable,
4. fallback behavior is deterministic and documented.

### Slice 4 - Pre-Trade Proof Pack

Deliverables:

1. proof-pack model,
2. proof-pack artifact API,
3. Markdown summary generation,
4. report-input adapter for `lotus-report`,
5. AI memo input adapter for `lotus-ai`,
6. proof-pack OpenAPI certification.

Acceptance criteria:

1. every selected rebalance alternative can produce a proof pack,
2. proof pack contains mandate, risk, performance, tax, turnover, FX, rule, and lineage evidence,
3. proof pack can be rendered in Workbench and sent to reporting/AI seams.

### Slice 5 - Rebalance Wave Orchestration

Deliverables:

1. wave aggregate model,
2. wave item model,
3. batch source-readiness checks,
4. batch simulation,
5. approval/staging/handoff states,
6. retry/cancel support,
7. wave supportability APIs.

Acceptance criteria:

1. a CIO model change can generate an affected-portfolio wave,
2. individual portfolio failures do not hide successful items,
3. partial readiness is explicit,
4. supportability and lineage exist at wave and item level.

### Slice 6 - Risk/Performance Feedback Loop

Deliverables:

1. outcome-review model,
2. expected-vs-realized comparison,
3. integration with `lotus-performance`,
4. integration with `lotus-risk`,
5. PM quality metrics,
6. post-trade review API.

Acceptance criteria:

1. completed runs can be reviewed after transaction/performance data is available,
2. variance is attributed to market move, execution slippage, partial fill, model drift, or data issue,
3. feedback becomes searchable supportability evidence.

### Slice 7 - AI PM Copilot

Deliverables:

1. workflow-pack spec for PM memo,
2. proof-pack-to-AI evidence adapter,
3. AI run posture persistence,
4. review actions,
5. safety and no-domain-truth guardrails,
6. Workbench-ready narrative payload.

Acceptance criteria:

1. PM memo can be generated from structured proof only,
2. AI output carries provenance and review state,
3. AI unavailable state degrades gracefully,
4. tests prove no AI output changes domain decisions.

### Slice 8 - Workbench/Gateway Product Experience

Deliverables:

1. gateway composition contracts,
2. Workbench command center,
3. mandate health panels,
4. alternatives comparison,
5. proof-pack view,
6. wave cockpit,
7. outcome-review view,
8. demo screenshot pack.

Acceptance criteria:

1. all UI features are gateway-backed,
2. no unsupported fake states,
3. canonical live validation includes DPM command-center scenarios,
4. business/demo wiki pages include diagrams and evidence.

### Slice 9 - Enterprise Hardening and Certification

Deliverables:

1. OpenAPI certification for all new endpoints,
2. API vocabulary inventory updates,
3. source-data product declarations,
4. trust telemetry fixtures,
5. migration and retention policy,
6. observability metrics,
7. structured logging,
8. security and entitlement posture,
9. performance/load tests,
10. complete wiki/readme updates.

Acceptance criteria:

1. all endpoints are certified,
2. every attribute has description, type, and example,
3. every endpoint has what/when/how guidance,
4. test pyramid is complete,
5. canonical live proof covers every target workflow,
6. documentation is business-, dev-, sales-, ops-, and client-demo-ready.

---

## 11. Testing Strategy

### 11.1 Unit Tests

Required areas:

1. mandate compiler,
2. health score decomposition,
3. exception taxonomy,
4. optimizer objective assembly,
5. constraint validation,
6. proof-pack generation,
7. wave state machine,
8. outcome-review calculations,
9. AI adapter no-domain-truth guards.

### 11.2 Contract Tests

Required areas:

1. OpenAPI model documentation,
2. request/response separation,
3. no unversioned route aliases,
4. source-data product declaration validation,
5. trust telemetry validation,
6. gateway composition contracts.

### 11.3 Integration Tests

Required areas:

1. `lotus-core` mandate source resolution,
2. `lotus-risk` risk impact enrichment,
3. `lotus-performance` outcome enrichment,
4. `lotus-report` proof-pack reporting handoff,
5. `lotus-ai` PM memo execution,
6. PostgreSQL persistence and migration smoke,
7. partial-upstream-readiness behavior.

### 11.4 Live Canonical Tests

Canonical data must include:

1. balanced SGD mandate,
2. growth USD mandate,
3. income mandate,
4. ESG mandate,
5. restricted-instrument mandate,
6. tax-sensitive mandate,
7. multi-currency mandate,
8. stale-data mandate,
9. risk-breach mandate,
10. CIO model-change wave.

Live evidence must capture:

1. request/response payloads,
2. proof-pack artifacts,
3. command-center output,
4. Workbench screenshots where applicable,
5. source-data readiness evidence,
6. risk/performance/report/AI integration posture.

---

## 12. Observability and Operations

Metrics:

1. `lotus_manage_mandate_health_total{state,reason,freshness_bucket}`
2. `lotus_manage_monitoring_exceptions_total{severity,reason}`
3. `lotus_manage_rebalance_alternatives_total{status,alternative_type}`
4. `lotus_manage_rebalance_wave_items_total{state,reason}`
5. `lotus_manage_proof_pack_total{state,reason}`
6. `lotus_manage_outcome_review_total{state,reason}`

Forbidden metric labels:

1. portfolio id,
2. client id,
3. account id,
4. security id,
5. correlation id,
6. trace id,
7. raw prompt,
8. request body,
9. response body.

Structured log fields:

1. `service`
2. `operation`
3. `state`
4. `reason`
5. `tenant_scope`
6. `correlation_present`
7. `source_system`
8. `source_supportability_state`
9. `workflow_state`
10. `evidence_ref`

Supportability surfaces:

1. command-center support profile,
2. monitoring job support profile,
3. wave support bundle,
4. proof-pack support bundle,
5. outcome-review support bundle,
6. AI memo run posture.

---

## 13. Governance and Controls

Required controls:

1. API certification,
2. OpenAPI examples,
3. domain-data-product declarations,
4. trust telemetry declarations,
5. data lineage and source-readiness classification,
6. migration governance,
7. retention governance,
8. structured logging,
9. bounded metrics,
10. entitlement and tenant posture,
11. policy-pack governance,
12. no advisory/proposal ownership leakage,
13. no AI domain-decision ownership,
14. no unsupported Workbench UI states.

Approval boundaries:

1. PM approval required for soft mandate exceptions,
2. CIO approval required for model or house-view waves where configured,
3. compliance approval required for restricted constraint relaxation where configured,
4. operations confirmation required before external execution handoff where configured.

---

## 14. Rollout Plan

### Phase 1 - Foundation

1. mandate digital twin,
2. health score,
3. monitoring,
4. command-center API.

### Phase 2 - Differentiation

1. construction alternatives,
2. proof packs,
3. tax/liquidity/ESG-aware construction,
4. Workbench comparison experience.

### Phase 3 - Scale

1. wave orchestration,
2. CIO model-change impact,
3. PM book workflow,
4. operations handoff support.

### Phase 4 - Intelligence

1. post-trade feedback loop,
2. outcome learning,
3. governed AI PM memos,
4. client/reporting packaging.

---

## 15. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Duplicating domain logic from risk/performance/core | Define explicit source ownership and consume governed outputs. |
| Building impressive but unsupported UI | Gateway-backed contracts and canonical live proof required. |
| AI becoming a shadow decision engine | AI can summarize evidence only; domain decisions remain deterministic and reviewed. |
| Over-complex optimizer becomes opaque | Require objective/constraint trace, solver status, infeasibility explanation, and fallback. |
| Too many APIs without product coherence | Command-center, proof-pack, and wave aggregates must tie workflows together. |
| Market data/source quality causes misleading decisions | Source-readiness gate and health score must block or degrade truthfully. |
| Sales demos overclaim target-state features | Wiki and supported-features list must separate implemented from target. |

---

## 16. Success Measures

Business:

1. PM can identify all attention-needed mandates in under one minute,
2. PM can compare rebalance alternatives with clear trade-offs,
3. CIO can see model-change impact across mandates,
4. compliance can inspect decision evidence without engineering help,
5. sales can demo an end-to-end DPM lifecycle with real API evidence.

Engineering:

1. all new APIs certified,
2. all new workflows have proof artifacts,
3. all new source dependencies declared,
4. no unsupported Workbench surface,
5. no high-cardinality telemetry labels,
6. canonical live proof covers every promoted feature.

Analytical:

1. alternatives expose risk, tax, turnover, cost, liquidity, and drift trade-offs,
2. post-trade outcome review reconciles expected versus realized impact,
3. mandate health score is decomposable and deterministic.

---

## 17. Reference Links

1. Julius Baer discretionary mandates:
   `https://www.juliusbaer.com/uk/en/our-solutions/investing/discretionary-mandates/`
2. Pictet discretionary mandate:
   `https://www.pictet.com/sg/en/individuals-families/investment-solutions/discretionary-mandate`
3. Deutsche Bank Wealth Management DPM:
   `https://wealth.db.com/en/what-we-do/discretionary-portfolio-management.html`
4. HSBC Private Bank DPM:
   `https://www.privatebanking.hsbc.com/investing/discretionary-portfolio-management/`
5. Citi Private Bank investment management:
   `https://www.privatebank.citibank.com/we-offer/investment-management`
6. J.P. Morgan Private Bank investing:
   `https://privatebank.jpmorgan.com/nam/en/services/investing`
7. CFA Institute portfolio management overview:
   `https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/portfolio-management-overview`
8. CFA Institute asset allocation overview:
   `https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/overview-asset-allocation`
9. Andrew Ang, Asset Management: A Systematic Approach to Factor Investing:
   `https://academic.oup.com/book/3342`
10. Goldman Sachs Black-Litterman history:
   `https://www.goldmansachs.com/our-firm/history/moments/1990-black-litterman-model`

---

## 18. Deliberate Next Step

This RFC should be reviewed as a strategic target-state roadmap before implementation begins. The
first implementation RFC should be a smaller execution RFC for Slice 1 and Slice 2:

`RFC-0038: Mandate Digital Twin, Health Score, and DPM Command Center Foundation`

That follow-up RFC should include concrete API schemas, migrations, exact source-data contracts,
OpenAPI examples, testing plan, and canonical demo data requirements.

---

## 19. Gold-Standard Execution Contract

This section is the execution contract for RFC-0037 and the RFC-0038 through RFC-0043 delivery
family. It exists to remove ambiguity before implementation begins.

### 19.1 Supported-Features Ledger

Target-state features must remain separate from implementation-backed features until live proof
exists. Promotion requires API certification, tests, canonical evidence, and wiki/supported-feature
updates.

| Feature | Owning RFC | Initial support state | Promotion rule |
| --- | --- | --- | --- |
| Mandate digital twin | RFC-0038 | Supported first wave | Core/manage-backed refresh/read/version/diff and bounded Gateway/Workbench command-center realization are implementation-backed; richer source depth remains owner scope. |
| Mandate health score | RFC-0038 | Supported first wave | Decomposed scoring, reason codes, tests, monitoring integration, and command-center evidence are implementation-backed; additional source dimensions remain owner scope. |
| DPM command center | RFC-0038 | Supported first wave | Bounded command-center summary APIs, PM-book-backed monitoring, Gateway composition, Workbench cockpit, and populated canonical proof are implementation-backed. |
| CIO house-view propagation | RFC-0041 | Supported first wave for CIO model-change waves plus bounded source-owned risk-event and tactical house-view wave consumption | `CIO_MODEL_CHANGE` affected-cohort discovery is source-backed and audited; risk-event and tactical house-view waves consume owning source products; global campaign discovery remains future source-owner depth. |
| Advanced construction lab | RFC-0039 | Supported first wave | Alternatives are persisted, comparable, explainable, and source-posture-aware with Gateway/Workbench first-wave product proof; proof-pack/wave/report/AI lifecycle stays in owning RFCs. |
| Rebalance alternatives | RFC-0039 | Supported first wave | Generation, read, selection, comparison, and degraded-source posture are implementation-backed; external execution and autonomous choice remain unsupported. |
| Tax/liquidity/risk/ESG construction | RFC-0039 | Supported source-backed subsets | Implemented only where source products exist for tax lots, cashflow, risk, client restrictions, sustainability, and related posture; unsupported dimensions remain explicit. |
| Currency overlay and hedge governance | RFC-0039 | Supported bounded construction posture | Currency-aware alternatives exist, but full hedge governance, FX funding, and execution/settlement workflows remain future source-owner scope. |
| Regime and stress simulator | RFC-0039/RFC-0040 | Supported bounded construction and proof-pack posture | `RegimeScenarioPackEvaluation:v1` can feed construction alternatives and direct source-owned proof-pack `regime_stress_context` enrichment; scenario contribution approval and richer CIO approval remain future depth. |
| Pre-trade proof pack | RFC-0040 | Supported first wave | Durable JSON/Markdown/report/AI evidence artifacts, Gateway composition, Workbench review UX, report materialization, AI memo, and canonical proof are implementation-backed. |
| Decision timeline and portfolio memory | RFC-0040 | Partial first-wave support | Manage/Gateway/Workbench portfolio-memory read model, report/AI bounded context consumers, and structured no-OMS execution boundary evidence are implementation-backed; OMS, PM-scoring, and client-communication event families remain future scope. |
| Rebalance wave orchestration | RFC-0041 | Supported first wave | Explicit-list, PM-book, and CIO model-change waves plus Gateway/Workbench command center, report materialization, and AI memo handoff are implementation-backed; OMS and richer cohorts remain future. |
| Post-trade outcome feedback | RFC-0042 | Supported first wave | Manage outcome-review authority, Gateway composition, Workbench UX, report/archive materialization, and governed AI narrative request path are implementation-backed; OMS, PM scoring, and richer source methodology remain future. |
| Governed PM copilot | RFC-0043 | Proposed | Promote only after `lotus-ai` workflow-pack guardrails and AI-unavailable fallbacks are proven. |
| DPM sales/demo story | RFC-0037 plus wiki | Supported canonical story | `lotus-platform` PR #310 and wiki publication commit `884bec3` provide the implementation-backed canonical DPM demo story for `PB_SG_GLOBAL_BAL_001`. |

### 19.2 Mandatory Delivery Slices

The detailed RFCs may have feature-specific slices, but every implementation must also execute the
following mandatory slices in order. Do not move to the next slice until the current slice has
working code, tests, documentation posture, and evidence appropriate to its scope.

#### Mandatory Slice A - Platform Automation and Scaffolding Improvement

Run this slice before app-local implementation and again whenever repeated platform gaps appear.
If no platform change is needed, record a deliberate no-change decision.

Required checks:

1. identify whether app scaffolding should already provide the needed API certification,
   OpenAPI examples, health endpoints, structured logging, metrics, error models, migration smoke,
   test scaffolding, CI defaults, documentation scaffolding, wiki source, and governance hooks,
2. improve `lotus-platform` automation when a gap is repeatable across applications,
3. keep app-local changes only where the concern is genuinely `lotus-manage` domain behavior,
4. update central context, skills, or scaffolding docs when platform behavior changes.

Exit evidence:

1. list of platform gaps found,
2. platform PR or explicit no-change decision,
3. app-local implementation boundary recorded,
4. impacted validators or templates documented.

#### Mandatory Slice B - Cleanup and Structure

Required checks:

1. remove dead advisory leftovers, stale endpoints, duplicate RFC/documentation material, and
   misleading target-state claims,
2. simplify modules before adding new behavior,
3. move long-lived operator and product material to wiki source where appropriate,
4. avoid duplicating detailed RFC mechanics in the wiki,
5. keep supported-features material implementation-backed.

Exit evidence:

1. dead-code and duplicate-doc review notes,
2. updated repository structure when needed,
3. wiki/source-doc split recorded,
4. tests proving removed behavior is no longer exposed if endpoints are deleted.

#### Mandatory Slice C - Implementation Proof

Required checks:

1. prove each endpoint and workflow against the RFC,
2. capture full request/response evidence under non-git-tracked `output/`,
3. validate every returned figure, readiness state, reason code, lineage ref, and degraded state,
4. run canonical core/manage proof when source data is part of the feature,
5. file or fix every gap discovered during evidence review.

Exit evidence:

1. live evidence folder path,
2. request/response inventory,
3. critical review notes,
4. fixed-gap summary,
5. remaining deferred items with owner and rationale.

#### Mandatory Slice D - Second-Last Hardening and Review

Required checks:

1. perform a code review focused on bugs, architecture, duplication, dead code, and test quality,
2. certify every touched API and error path,
3. verify Swagger grouping, what/when/how guidance, request examples, response examples, and
   field-level descriptions, types, and examples,
4. verify data-mesh declarations, telemetry, structured logging, bounded metrics, health,
   readiness, and platform governance,
5. run repository-native checks and monitor GitHub lanes.

Exit evidence:

1. review findings and fixes,
2. OpenAPI/API vocabulary certification,
3. test-pyramid adequacy statement,
4. local and GitHub check posture,
5. no unresolved P0/P1 implementation gaps.

#### Mandatory Slice E - Final Closure

Required checks:

1. update README, RFC, runbook, context, wiki source, and supported-features truth,
2. publish wiki after merge when wiki truth changed,
3. record whether skills, agent guidance, documentation workflow, or context should change,
4. mark the RFC implementation status truthfully,
5. clean branch state, PR state, and local generated artifacts.

Exit evidence:

1. final evidence summary,
2. wiki source and publication posture,
3. supported-features update,
4. skills/context decision,
5. branch hygiene and CI closure.

### 19.3 Documentation-As-Product Standard

Documentation must be suitable for business, engineering, sales, marketing, operations, and client
demo preparation:

1. README stays concise and command-accurate,
2. wiki explains feature behavior, integrations, operational posture, and diagrams in
   business-readable language,
3. RFCs carry implementation detail, architecture, test and evidence requirements,
4. supported-features separates implemented, gated, and proposed features,
5. no sales or demo material may claim target-state behavior before implementation-backed proof.

### 19.4 Enterprise, Data-Mesh, and Observability Baseline

Every implementation RFC in this family inherits this baseline. A feature is not complete until it
meets the relevant Lotus platform standards as well as its business acceptance criteria.

Data-mesh requirements:

1. declare every produced or consumed domain data product in repo-native contracts where applicable,
2. keep `lotus-core`, `lotus-risk`, `lotus-performance`, `lotus-report`, and `lotus-ai` source
   authority explicit,
3. attach lineage, freshness, completeness, source-readiness, and supportability metadata to
   cross-service evidence,
4. update trust telemetry, SLO, access, and evidence-policy posture when a feature becomes a
   governed product,
5. validate with repo-native mesh and platform certification gates before promotion.

API and contract requirements:

1. use clean strategic `/api/v1` contracts; do not preserve poor legacy shapes for compatibility,
2. certify every endpoint through OpenAPI quality, API vocabulary, no-alias, request/response
   examples, error examples, and field-level descriptions/types/examples,
3. expose bounded problem-details errors and deterministic reason codes,
4. make partial readiness and degraded source states first-class response states,
5. keep downstream Gateway/Workbench integration out of scope until the target API is certified.

Observability and operations requirements:

1. structured logs must carry service, operation, state, supportability reason, correlation id, and
   trace context where available,
2. metrics must use bounded, non-sensitive labels only,
3. health, liveness, readiness, supportability, and operator diagnostics must distinguish app
   health from source-data readiness,
4. audit events must record actor, decision, state transition, reason codes, and artifact refs,
5. telemetry must never expose client identifiers, holdings, raw requests/responses, proof-pack
   sensitive payloads, trace ids, or correlation ids as metric labels,
6. live proof must include logs/metrics/supportability posture, not only business responses.

Delivery requirements:

1. use repo-native checks first and GitHub lanes for asynchronous heavy proof,
2. monitor Feature Lane and PR Merge Gate while continuing non-overlapping work,
3. fix CI failures promptly,
4. keep branch history small, meaningful, and truthful,
5. leave no open P0/P1 architecture, API, data-mesh, observability, or test-quality gap before
   closure.

Feature-expansion rule:

1. every new feature must strengthen the enterprise posture or include explicit compensating
   controls,
2. no feature may close if it increases endpoint sprawl, source-authority ambiguity, undocumented
   states, unbounded telemetry labels, weak error handling, or superficial tests,
3. new capabilities should reduce operational effort, improve auditability, improve decision
   quality, or make source-readiness clearer,
4. if a valuable feature introduces unavoidable complexity, the implementation must add modular
   boundaries, supportability, observability, and tests that make the complexity operationally
   manageable,
5. final review must explicitly state how enterprise posture improved versus the pre-RFC baseline.

---

## 20. Post-Closure WTBD Integration Audit

The 2026-05-09 and 2026-05-10 WTBD audits moved completed RFC37 child-roadmap truth into this
strategic parent RFC without marking the full parent roadmap done.

| WTBD | Integrated result | Current boundary |
| --- | --- | --- |
| RFC37-WTBD-001 | RFC-0042 now supports manage-owned outcome-review authority plus bounded Gateway/Workbench, report/archive, and AI narrative first-wave realization. | Source-owner methodology depth, external OMS execution, PM scoring, and client communication remain future scope. |
| RFC37-WTBD-005 | Supported proof-pack, rebalance-wave, and outcome-review evidence now flow from manage-owned report inputs into generated report, render, archive, Gateway/Workbench request posture, AI evidence handoff, and report/archive lineage families. | `lotus-manage` does not generate or archive documents, client communication execution remains unsupported, and any new evidence artifact family needs its own owner, controls, and proof. |
| RFC37-WTBD-006 | `lotus-platform` PR #310, merge `42e0ecff3597257ac3ea63b0c59b425603eeb291`, and wiki publication commit `884bec3` provide the canonical DPM demo story for `PB_SG_GLOBAL_BAL_001`. | Demo material must keep unsupported OMS, PM-scoring, client-communication, autonomous AI, and unimplemented degraded/blocked seed fixtures out of supported claims. |

Gold-pass assessment:

1. Truly completed: RFC37-WTBD-006 is complete as a governed canonical sales/demo story,
   RFC37-WTBD-001 is complete for the RFC-0042 bounded first-wave outcome-review product path, and
   RFC37-WTBD-005 is complete for supported proof-pack, wave, and outcome-review evidence
   materialization.
2. Quality improvements made: RFC-0037 now distinguishes implemented child capabilities from the
   remaining parent-roadmap ambition instead of leaving the supported-features ledger entirely in
   proposed state.
3. Debt removed: stale parent-roadmap wording that understated RFC-0042 and the canonical demo story
   was retired while preserving explicit unsupported boundaries.
4. Testing and evidence proven: proof is anchored in RFC-0040/RFC-0041/RFC-0042 report-input,
   render, archive, Gateway/Workbench, AI-evidence, and canonical evidence, `lotus-platform`
   PR #310, platform wiki publication commit `884bec3`, and the documentation regression that
   guards RFC/WTBD/wiki truth.
5. Expected-standard decision: the completed child-roadmap items have reached the expected standard
   on merged and wiki-published owning-repository truth; RFC-0037 remains partial only where
   future source-owner depth, portfolio-memory completion, OMS execution, PM scoring, client
   communication, and broader copilot workspace scope are still unimplemented.
