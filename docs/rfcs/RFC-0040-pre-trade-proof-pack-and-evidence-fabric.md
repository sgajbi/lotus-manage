# RFC-0040: Pre-Trade Proof Pack and DPM Evidence Fabric

| Metadata | Details |
| --- | --- |
| **Status** | PROPOSED |
| **Created** | 2026-05-03 |
| **Depends On** | RFC-0017, RFC-0019, RFC-0020, RFC-0021, RFC-0023, RFC-0036, RFC-0037, RFC-0038, RFC-0039 |
| **Doc Location** | `docs/rfcs/RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md` |

---

## 0. Executive Summary

RFC-0040 creates the DPM pre-trade proof pack: a durable evidence artifact that explains why a
portfolio action is being proposed, what it changes, what risks and constraints were evaluated, what
source data was used, who reviewed it, and what downstream reports or narratives can be generated.

This RFC is the trust layer for `lotus-manage`. It turns rebalance output into a complete PM,
compliance, operations, investment-committee, sales-demo, and audit artifact.

The proof pack must be structured enough for machines and readable enough for humans.

---

## 1. Current Baseline

Existing foundations:

1. deterministic run artifact contract,
2. support bundle APIs,
3. lineage APIs,
4. workflow gate APIs,
5. stateful core source lineage,
6. OpenAPI certification,
7. demo request/response evidence under non-git-tracked output folders when generated.

Current gaps:

1. no first-class pre-trade proof-pack aggregate,
2. no normalized cross-section evidence for mandate, alternatives, risk, tax, liquidity, FX, and
   source readiness,
3. no report-ready package contract for `lotus-report`,
4. no AI-ready structured evidence contract for `lotus-ai`,
5. no Workbench-ready proof-pack summary contract through `lotus-gateway`.

## 1.5 Business Outcomes

This RFC targets the following business outcomes:

1. **Trustworthy discretionary decisions**
   give PMs, compliance, operations, and auditors one durable proof artifact explaining every
   proposed action.
2. **Faster approvals**
   reduce approval friction by packaging mandate, risk, tax, liquidity, rule, trade, and source
   evidence before review.
3. **Higher-quality client and investment-committee material**
   make DPM decisions report-ready and narrative-ready without manual reconstruction.
4. **Lower operational support cost**
   allow support teams to diagnose a decision from one proof pack instead of searching across run,
   lineage, source, workflow, and log surfaces.
5. **Safer AI usage**
   provide `lotus-ai` with structured evidence rather than letting AI infer or invent business
   context.
6. **Differentiated sales demos**
   show that Lotus can prove every DPM action end to end with source lineage and business-readable
   evidence.

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. Add `DpmPreTradeProofPack` as a first-class durable product artifact.
2. Generate proof packs from selected alternatives or direct rebalance runs.
3. Include mandate, source, before, target, after, trades, risk, tax, turnover, cost, liquidity, FX,
   currency overlay, scenario, rules, workflow, decision timeline, and lineage evidence.
4. Produce JSON artifact and Markdown summary.
5. Provide adapter outputs for `lotus-report` and `lotus-ai`.
6. Certify APIs and OpenAPI examples.
7. Support Workbench display through Gateway without UI-side evidence reconstruction.

### 2.2 Non-Goals

1. Render PDF directly; `lotus-report` and `lotus-render` own rendering.
2. Generate AI narrative directly inside `lotus-manage`; `lotus-ai` owns generation.
3. Replace existing run artifacts immediately.
4. Execute trades.
5. Replace approval workflows; proof pack supplies evidence to them.

---

## 3. Proof Pack Sections

Required sections:

1. `decision_summary`
2. `mandate_context`
3. `source_readiness`
4. `before_state`
5. `target_state`
6. `selected_alternative`
7. `trade_intents`
8. `after_state`
9. `drift_impact`
10. `risk_impact`
11. `performance_context`
12. `tax_impact`
13. `turnover_and_cost`
14. `liquidity_and_cash`
15. `fx_funding_plan`
16. `currency_overlay_evidence`
17. `scenario_and_regime_evidence`
18. `eligibility_and_restrictions`
19. `sustainability_controls`
20. `rule_results`
21. `diagnostics`
22. `approval_requirements`
23. `operations_handoff`
24. `decision_timeline`
25. `lineage`
26. `supportability`
27. `reporting_refs`
28. `ai_refs`

Every section must include:

1. `state`
2. `summary`
3. `evidence`
4. `source_refs`
5. `reason_codes`
6. `generated_at`

---

## 4. Domain Models

### 4.1 DpmPreTradeProofPack

Required fields:

1. `proof_pack_id`
2. `proof_pack_version`
3. `portfolio_id`
4. `mandate_id`
5. `rebalance_run_id`
6. `alternative_set_id`
7. `selected_alternative_id`
8. `as_of_date`
9. `status`
10. `decision_summary`
11. `sections`
12. `approval_requirements`
13. `operations_handoff`
14. `decision_timeline`
15. `lineage`
16. `markdown_summary`
17. `report_input_ref`
18. `ai_evidence_ref`
19. `created_at`
20. `created_by`

### 4.1.1 Decision Timeline Requirements

The proof pack must be able to anchor itself in portfolio memory.

Required timeline evidence:

1. most recent mandate version event,
2. current monitoring exception events that triggered or influenced the action,
3. model-change, tactical house-view, or PM-initiated event where applicable,
4. generated alternative set event,
5. selected alternative event,
6. approval or deferral event,
7. wave inclusion event when applicable,
8. downstream execution handoff and post-trade outcome refs when available.

Each timeline event must include `event_id`, `event_type`, `event_time`, `actor`, `source_system`,
`reason_codes`, `status`, and `artifact_refs`.

### 4.2 DpmProofPackSection

Required fields:

1. `section_id`
2. `section_type`
3. `state`
4. `title`
5. `summary`
6. `facts`
7. `metrics`
8. `reason_codes`
9. `evidence_refs`
10. `source_supportability`

### 4.3 DpmProofPackDecisionSummary

Required fields:

1. `decision_type`
2. `recommended_action`
3. `selected_alternative_type`
4. `business_rationale`
5. `expected_benefit`
6. `main_tradeoffs`
7. `top_risks`
8. `approval_state`
9. `operations_state`

---

## 5. API Surface

### 5.1 Generate Proof Pack

`POST /api/v1/rebalance/proof-packs`

Purpose:

1. generate a proof pack from selected alternative or run,
2. persist the proof pack,
3. return full JSON artifact and summary refs.

Request fields:

1. `source_type`: `REBALANCE_RUN` or `SELECTED_ALTERNATIVE`
2. `rebalance_run_id`
3. `alternative_set_id`
4. `selected_alternative_id`
5. `include_markdown`
6. `include_report_input`
7. `include_ai_evidence_input`
8. `actor`
9. `reason`

### 5.2 Retrieve Proof Pack

`GET /api/v1/rebalance/proof-packs/{proof_pack_id}`

Purpose:

1. retrieve durable proof pack,
2. support Workbench evidence view and audit.

### 5.3 Proof Pack Markdown

`GET /api/v1/rebalance/proof-packs/{proof_pack_id}/summary.md`

Purpose:

1. return human-readable Markdown summary,
2. support PM, operations, and report preview workflows.

### 5.4 Proof Pack Report Input

`GET /api/v1/rebalance/proof-packs/{proof_pack_id}/report-input`

Purpose:

1. return typed package for `lotus-report`,
2. avoid report-side reconstruction of DPM decisions.

### 5.5 Proof Pack AI Evidence Input

`GET /api/v1/rebalance/proof-packs/{proof_pack_id}/ai-evidence-input`

Purpose:

1. return structured, bounded, no-decision AI input for `lotus-ai`,
2. support RFC-0043 PM memo generation.

---

## 6. Persistence

Tables:

1. `dpm_pre_trade_proof_packs`
2. `dpm_pre_trade_proof_pack_sections`
3. `dpm_pre_trade_proof_pack_refs`

Retention:

1. proof packs tied to selected alternatives: 7 years,
2. proof packs tied to blocked or rejected workflows: 7 years if audit-linked,
3. draft proof packs: configurable, default 1 year.

Integrity requirements:

1. proof pack content hash,
2. source run hash,
3. source alternative hash,
4. source-data lineage refs,
5. immutable after creation except append-only refs.

---

## 7. Report and AI Handoff Contracts

### 7.1 Report Input

`DpmProofPackReportInput` must include:

1. title,
2. portfolio and mandate identifiers,
3. decision summary,
4. before/after allocation tables,
5. trade table,
6. risk/tax/cost/liquidity sections,
7. rule and diagnostics sections,
8. approval and operations sections,
9. source lineage.

### 7.2 AI Evidence Input

`DpmProofPackAiEvidenceInput` must include only structured evidence:

1. no raw prompt,
2. no hidden calculations,
3. no instruction to choose trades,
4. no unsupported facts,
5. bounded facts and metrics,
6. explicit forbidden-action guardrails.

---

## 8. Implementation Slices

### Slice 0 - Evidence Map and Artifact Design

1. map existing run/artifact/support-bundle fields to proof-pack sections,
2. identify missing evidence,
3. decide minimum viable proof-pack sections.

Exit evidence:

1. section-to-source mapping,
2. gap list,
3. examples reviewed with business and engineering lens.

### Slice 1 - Domain Models and Pure Proof Builder

1. add proof-pack models,
2. build proof pack from existing run result,
3. build proof pack from selected alternative,
4. generate deterministic content hash.

Exit evidence:

1. unit tests for every section,
2. deterministic hash tests,
3. missing-section degraded tests.

### Slice 2 - Markdown Summary and Human Readability

1. add Markdown renderer,
2. add section ordering,
3. add PM-friendly language without unsupported claims,
4. add snapshot tests.

Exit evidence:

1. Markdown examples,
2. no broken tables,
3. no target-state claims for missing evidence.

### Slice 3 - Persistence and APIs

1. add migrations and repository,
2. add generate/retrieve/markdown APIs,
3. add OpenAPI examples,
4. add supportability fields.

Exit evidence:

1. migration smoke,
2. API tests,
3. OpenAPI certification.

### Slice 4 - Report and AI Handoff Adapters

1. add report-input contract,
2. add AI evidence-input contract,
3. add downstream mock tests,
4. add no-domain-truth AI guard tests.

Exit evidence:

1. report payload example,
2. AI payload example,
3. forbidden-field tests.

### Slice 5 - Live Proof and Docs

1. generate proof pack from canonical stateful portfolio,
2. save request/response evidence under `output/`,
3. update wiki and README,
4. update supported-features after proof.

Exit evidence:

1. live proof artifact,
2. reviewed evidence notes,
3. docs and wiki current.

---

## 9. Testing Requirements

1. proof-pack section completeness tests,
2. content hash determinism tests,
3. missing evidence degradation tests,
4. Markdown rendering tests,
5. report-input contract tests,
6. AI evidence guardrail tests,
7. repository persistence tests,
8. API and OpenAPI tests,
9. canonical live proof.

---

## 10. Acceptance Criteria

RFC-0040 is complete when:

1. proof packs can be generated from a selected alternative or run,
2. every proof pack is durable, hashed, lineage-backed, and retrievable,
3. Markdown summary is readable and deterministic,
4. report and AI handoff payloads are bounded and certified,
5. OpenAPI is complete,
6. canonical live evidence exists,
7. Workbench can consume proof-pack truth through Gateway in a later UI slice without reconstructing
   evidence client-side.

---

## 11. Gold-Standard Execution Contract

RFC-0040 is the DPM trust layer. It must produce evidence that is machine-readable, human-readable,
audit-ready, and safe for downstream reporting and AI summarization.

### 11.1 Supported-Features Ledger

| Feature | Support state before implementation | Promotion rule |
| --- | --- | --- |
| Pre-trade proof pack JSON | Proposed | Promote only after all required sections, lineage, hashes, and retrieval APIs are certified. |
| Human-readable Markdown summary | Proposed | Promote only after deterministic rendering and business-language review pass. |
| Report input handoff | Proposed | Promote only after `lotus-report` payload contract tests and examples exist. |
| AI evidence handoff | Proposed | Promote only after forbidden-field and structured-evidence guard tests pass. |
| Decision timeline anchoring | Proposed | Promote only after mandate, exception, alternative, approval, wave, handoff, and outcome events link. |
| Proof-pack audit and supportability | Proposed | Promote only after immutable hashes, source refs, supportability, and retention posture are complete. |

### 11.2 Architecture and Domain Direction

Implementation must treat the proof pack as a governed investment-decision artifact:

1. it records the business rationale, mandate context, selected alternative, trade intent,
   risk/tax/liquidity/currency/scenario evidence, source readiness, approvals, and operations state,
2. it is not a replacement for `lotus-report`; it supplies report input,
3. it is not an AI prompt; it supplies structured evidence to `lotus-ai`,
4. it is not a log archive; it is a curated DPM evidence product,
5. it must support PM, compliance, operations, CIO, audit, and demo use cases without exposing
   sensitive raw telemetry or payload internals.

### 11.3 Mandatory Delivery Slices

These slices are mandatory in addition to the feature-specific slices in Section 8.

#### Mandatory Slice A - Platform Automation and Scaffolding Improvement

Review whether platform scaffolding should provide reusable evidence-artifact patterns, Markdown
snapshot tests, report/AI handoff examples, OpenAPI artifact examples, and retention/governance
checklists. Improve platform automation for repeatable gaps; otherwise record a no-change decision.

#### Mandatory Slice B - Cleanup and Structure

Consolidate overlapping artifact, support-bundle, lineage, and workflow evidence builders where it
reduces duplication. Remove stale proof terminology that implies advisor consent or client proposal
ownership.

#### Mandatory Slice C - Implementation Proof

Generate proof packs from both a direct rebalance run and a selected alternative. Save full JSON,
Markdown, report-input, and AI-evidence request/response captures under `output/`. Review every
section for unsupported claims, missing source refs, and degraded-state clarity.

#### Mandatory Slice D - Second-Last Hardening and Review

Review immutability, hashing, lineage, retention, OpenAPI field quality, error handling, no-sensitive
AI/report handoff fields, Markdown readability, and test-pyramid depth. Every proof section must
have positive and degraded tests.

#### Mandatory Slice E - Final Closure

Update README/wiki/supported-features only for proven evidence surfaces. Publish wiki after merge
when proof-pack behavior or demo material changes. Record skills/context decisions and leave branch
and PR posture clean.

### 11.4 Evidence Expectations

Closure evidence must include:

1. proof-pack JSON example,
2. Markdown summary example,
3. report-input example,
4. AI-evidence input example,
5. missing-evidence degraded example,
6. decision-timeline linkage example,
7. OpenAPI/API certification summary,
8. local and GitHub check summary.

### 11.5 Enterprise Baseline

This RFC inherits RFC-0037 Section 19.4. Completion requires proof-pack lineage, retention posture,
audit events, no-sensitive report/AI handoff contracts, structured logging, bounded metrics,
operator diagnostics, API certification, and GitHub lane evidence for every proof-pack endpoint.
