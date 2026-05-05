# Construction Alternatives API Governance

This standard is the RFC-0039 Slice 1 scaffolding decision record for optimization-style
construction APIs in `lotus-manage`.

## Platform Automation Decision

No `lotus-platform` automation change is required for RFC-0039 Slice 1.

Reason:

1. platform already provides generic service scaffolding for OpenAPI quality, health/readiness,
   observability, structured logging, no-sensitive telemetry, wiki governance, mesh validation, CI
   lanes, and API certification;
2. RFC-0039 needs domain-specific construction-alternative rules rather than a generic
   cross-service scaffold;
3. moving construction-specific objective/constraint semantics into platform would over-generalize
   a DPM business capability and weaken domain ownership.

If two or more Lotus services later introduce optimizer-style resources with comparable trace,
fallback, and infeasibility requirements, this decision should be revisited and promoted to a
platform scaffold.

## Required API Shape For RFC-0039

The strategic endpoint family must be bounded and explicit:

1. generate construction alternatives for one mandate/portfolio context,
2. retrieve an alternative set by id,
3. select one alternative with actor attribution,
4. retrieve selection evidence and audit history where implemented.

Do not add compatibility aliases. As of the RFC-0037 through RFC-0043 revamp, `lotus-manage` is not
assumed to have production downstream consumers for this surface, so the correct target contract is
preferred over backward-compatible endpoint sprawl.

## Required Domain Vocabulary

Use these terms consistently:

| Term | Required meaning |
| --- | --- |
| `construction_alternative_set` | A generated, comparable set of alternatives for one mandate/portfolio context. |
| `construction_alternative` | One candidate portfolio-construction outcome produced by a named method. |
| `selected_alternative` | Actor-attributed chosen alternative. Selection does not execute trades. |
| `objective_trace` | Bounded explanation of objective terms such as drift, turnover, tax, cost, and liquidity. |
| `constraint_trace` | Bounded explanation of hard and soft constraints, their source, status, and relaxation posture. |
| `method_status` | `READY`, `PENDING_REVIEW`, `DEGRADED`, or `BLOCKED` posture for a method. |
| `source_supportability` | Source-data readiness and missing/degraded source families carried from upstream products. |

Avoid generic `option`, advisor-led `proposal`, or UI-owned language.

## Trace And Sensitive-Data Rules

Objective and constraint traces must be safe for audit and supportability, not raw optimization
dumps.

Required:

1. bounded term names and reason codes;
2. method id, method version, and solver/fallback posture where applicable;
3. source family and source lineage references;
4. low-cardinality status/reason fields suitable for metrics;
5. numeric values needed for reconciliation and business explanation.

Forbidden:

1. raw client names;
2. raw request/response body logging;
3. raw holdings or tax-lot dumps in logs or metrics;
4. high-cardinality instrument identifiers as metric labels;
5. unbounded solver matrices, optimizer internals, or full source payloads in traces;
6. hidden fallback from solver to heuristic.

## Method Status Rules

| Status | Required semantics |
| --- | --- |
| `READY` | Required data for the method is complete enough and the method output is actionable for PM review. |
| `PENDING_REVIEW` | Output exists but needs PM/compliance/operations review due to soft breach, missing optional enrichment, or fallback. |
| `DEGRADED` | Output is intentionally partial because a non-mandatory source is missing or stale. The missing family must be named. |
| `BLOCKED` | Method cannot produce a valid alternative because a mandatory source, hard constraint, or execution supportability requirement failed. |

No method may be `READY` when its mandatory source family is missing.

## OpenAPI And Test Scaffolding Requirements

Every RFC-0039 API implementation slice must add or update:

1. request and response examples for ready, degraded, blocked, fallback, and idempotent replay
   paths where applicable;
2. field descriptions, types, and examples for every public attribute;
3. unit tests for pure construction behavior;
4. API tests for status, error, and supportability behavior;
5. persistence parity tests when data is stored;
6. OpenAPI quality and vocabulary gate evidence;
7. no-sensitive logging/metrics tests when new telemetry is added.

## Observability Scaffold

Construction alternatives should use bounded labels only. Candidate metrics:

1. `lotus_manage_alternative_sets_total{status,input_mode}`
2. `lotus_manage_rebalance_alternatives_total{method,status}`
3. `lotus_manage_alternative_solver_duration_ms{method,status}`
4. `lotus_manage_alternative_generation_duration_ms{input_mode,status}`
5. `lotus_manage_alternative_source_degraded_total{source,reason}`
6. `lotus_manage_alternative_selection_total{status}`

These metrics must be added to `contracts/observability/lotus-manage-monitoring.v1.json` in the
implementation slice that introduces runtime telemetry. Slice 1 intentionally does not add runtime
metrics before the API and domain model exist.

