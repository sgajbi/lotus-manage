# RFC-0043: Governed AI PM Copilot for DPM

| Metadata | Details |
| --- | --- |
| **Status** | PROPOSED |
| **Created** | 2026-05-03 |
| **Depends On** | RFC-0037, RFC-0038, RFC-0039, RFC-0040, RFC-0041, RFC-0042 |
| **Doc Location** | `docs/rfcs/RFC-0043-governed-ai-pm-copilot-for-dpm.md` |

---

## 0. Executive Summary

RFC-0043 adds a governed PM copilot for discretionary mandate management. The copilot summarizes
evidence, drafts PM memos, explains exceptions, prepares investment-committee notes, and converts
proof packs into business-readable narratives.

The copilot must not make trade decisions, alter domain outputs, hide missing data, or replace PM,
CIO, compliance, risk, or operations approval.

The target architecture routes AI work through `lotus-ai` workflow packs. `lotus-manage` owns the
business evidence and workflow authority; `lotus-ai` owns prompt, provider, safety, evaluation,
async, and AI run posture.

---

## 1. Problem Statement

DPM evidence can be rich but dense. PMs, CIO teams, operations, advisors, and sales teams need
clear explanations:

1. why this mandate needs attention,
2. what changed,
3. which alternative was selected,
4. what risks and trade-offs exist,
5. what approvals are required,
6. what the client-safe story is,
7. what operations should watch.

Manual writing is slow and inconsistent. Uncontrolled AI would be dangerous. RFC-0043 defines a
bounded AI assistant that uses structured proof only.

## 1.5 Business Outcomes

This RFC targets the following business outcomes:

1. **Increase PM productivity**
   reduce time spent drafting memos, exception summaries, operations notes, and committee briefs.
2. **Improve communication quality**
   produce consistent, evidence-backed narratives for PMs, CIO teams, operations, advisors, and
   client-facing stakeholders.
3. **Make proof packs usable by humans**
   convert dense structured evidence into readable summaries without weakening the underlying
   audit trail.
4. **Differentiate Lotus demos**
   show governed AI as a safe assistant layered on top of deterministic DPM evidence.
5. **Reduce AI risk**
   ensure AI does not own trades, approvals, calculations, source truth, or workflow state.
6. **Increase ecosystem value**
   connect `lotus-manage` evidence with `lotus-ai` workflow-pack governance instead of building
   one-off local AI behavior.

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. Add PM memo generation from proof packs.
2. Add exception narrative generation from command-center exceptions.
3. Add CIO model-change summary generation from rebalance waves.
4. Add operations handoff summary generation.
5. Persist AI run posture and generated narrative refs.
6. Enforce no-domain-decision guardrails.
7. Route all AI execution through `lotus-ai`.
8. Support degraded behavior when AI is unavailable.

### 2.2 Non-Goals

1. AI-generated trades.
2. AI-selected alternatives.
3. AI rule or risk calculations.
4. AI-generated source data.
5. AI approval decisions.
6. Direct provider calls from `lotus-manage`.
7. Raw prompts or model outputs in logs/metrics.

---

## 3. Allowed Copilot Use Cases

### 3.1 PM Memo

Input:

1. proof pack,
2. selected alternative,
3. mandate health,
4. rule results,
5. source readiness.

Output:

1. concise PM memo,
2. key rationale,
3. trade-offs,
4. approval checklist,
5. caveats.

### 3.2 Exception Narrative

Input:

1. command-center exception,
2. mandate health snapshot,
3. relevant source readiness,
4. latest simulation/proof refs if available.

Output:

1. exception summary,
2. likely cause,
3. next action,
4. owner suggestion,
5. missing evidence list.

### 3.3 CIO Model-Change Brief

Input:

1. wave impact summary,
2. affected mandates,
3. aggregate exposures,
4. blocked counts,
5. approval workload.

Output:

1. model-change impact brief,
2. implementation risk summary,
3. key blocked cohorts,
4. PM workload summary.

### 3.4 Operations Handoff Summary

Input:

1. proof pack,
2. wave item state,
3. operations handoff checklist,
4. trade and FX requirements.

Output:

1. operations summary,
2. execution prerequisites,
3. blocking conditions,
4. support references.

---

## 4. Forbidden AI Behaviors

The copilot must never:

1. create or modify order intents,
2. choose selected alternative,
3. change run status,
4. change rule result,
5. change approval state,
6. hide data-quality issues,
7. invent missing source data,
8. call external providers directly,
9. log raw prompt,
10. log raw model output,
11. emit portfolio/client/security ids as metric labels,
12. present target-state features as implemented.

Tests must enforce these guardrails.

---

## 5. Workflow-Pack Families

Initial `lotus-ai` workflow-pack families:

1. `dpm_pm_memo.pack`
2. `dpm_exception_summary.pack`
3. `dpm_cio_model_change_brief.pack`
4. `dpm_operations_handoff_summary.pack`

Each pack registration must include:

1. owner app: `lotus-manage`,
2. workflow surface,
3. input schema ref,
4. output schema ref,
5. safety policy,
6. review posture,
7. artifact refs,
8. retention policy,
9. disabled/unavailable behavior.

---

## 6. Domain Models

### 6.1 DpmAiNarrativeRequest

Required fields:

1. `narrative_type`
2. `source_artifact_type`
3. `source_artifact_id`
4. `portfolio_id_hash`
5. `mandate_id_hash`
6. `tenant_id`
7. `audience`
8. `tone`
9. `max_length`
10. `include_caveats`
11. `actor`

Use hashed or internal refs where possible. Raw sensitive identifiers must not enter telemetry.

### 6.2 DpmAiNarrativeResponse

Required fields:

1. `narrative_id`
2. `narrative_type`
3. `state`
4. `source_artifact_id`
5. `workflow_pack_run_id`
6. `review_state`
7. `summary`
8. `sections`
9. `caveats`
10. `forbidden_claims_checked`
11. `lineage`
12. `created_at`

### 6.3 DpmAiNarrativeSection

Required fields:

1. `section_type`
2. `title`
3. `body`
4. `evidence_refs`
5. `caveats`

---

## 7. API Surface

### 7.1 Generate PM Memo

`POST /api/v1/rebalance/proof-packs/{proof_pack_id}/pm-memo`

Purpose:

1. submit proof-pack evidence to `lotus-ai`,
2. persist AI workflow-pack run posture,
3. return bounded narrative response.

### 7.2 Retrieve PM Memo

`GET /api/v1/rebalance/proof-packs/{proof_pack_id}/pm-memo`

### 7.3 Generate Exception Summary

`POST /api/v1/dpm/exceptions/{exception_id}/summary`

### 7.4 Generate Wave Brief

`POST /api/v1/rebalance/waves/{wave_id}/cio-brief`

### 7.5 Generate Operations Summary

`POST /api/v1/rebalance/proof-packs/{proof_pack_id}/operations-summary`

---

## 8. Safety and Evaluation

Required checks:

1. input schema validation,
2. proof-pack evidence completeness,
3. forbidden action check,
4. forbidden claim check,
5. missing evidence disclosure,
6. no raw sensitive telemetry,
7. no unsupported recommendation,
8. no domain field mutation.

Evaluation set:

1. successful ready rebalance,
2. blocked rebalance,
3. stale source data,
4. restricted instrument,
5. tax-sensitive alternative,
6. risk-breach alternative,
7. partial wave,
8. AI unavailable fallback.

---

## 9. Persistence

Tables:

1. `dpm_ai_narratives`
2. `dpm_ai_narrative_events`
3. `dpm_ai_narrative_source_refs`

Persist:

1. narrative metadata,
2. workflow-pack run id,
3. review state,
4. bounded output summary,
5. source artifact refs,
6. safety check results.

Do not persist:

1. raw provider request if it contains sensitive evidence,
2. raw model output unless governed by `lotus-ai` artifact policy,
3. high-cardinality telemetry fields.

---

## 10. Implementation Slices

### Slice 0 - AI Boundary and Workflow-Pack Design

1. define pack families,
2. align with `lotus-ai`,
3. create input/output schemas,
4. define forbidden claims.

### Slice 1 - Proof-Pack PM Memo

1. add PM memo request/response models,
2. call `lotus-ai` workflow-pack seam,
3. persist run posture,
4. support unavailable fallback.

### Slice 2 - Exception, Wave, and Operations Narratives

1. add exception summary,
2. add CIO brief,
3. add operations summary,
4. reuse safety checks.

### Slice 3 - Review and Governance

1. review actions,
2. narrative state transitions,
3. safety evaluation evidence,
4. supportability APIs.

### Slice 4 - Live Proof and Docs

1. run canonical proof-pack memo,
2. capture evidence,
3. update wiki,
4. update supported-features only after implementation.

---

## 11. Testing Requirements

1. no-domain-decision mutation tests,
2. forbidden claim tests,
3. AI unavailable fallback tests,
4. workflow-pack client tests,
5. safety/eval fixture tests,
6. persistence tests,
7. API and OpenAPI tests,
8. live proof through `lotus-ai` where configured.

---

## 12. Acceptance Criteria

RFC-0043 is complete when:

1. PM memo generation works from proof packs,
2. exception, wave, and operations summaries are implemented or explicitly deferred,
3. all AI calls go through `lotus-ai`,
4. generated narratives carry run posture and provenance,
5. guardrail tests prove AI cannot change domain truth,
6. OpenAPI is certified,
7. live proof captures AI-ready and AI-unavailable behavior,
8. docs clearly state that AI assists PMs but does not decide trades.
