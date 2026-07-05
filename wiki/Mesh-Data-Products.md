# Mesh Data Products

## Mesh role

`lotus-manage` is a maturity-wave producer in the Lotus enterprise data mesh.

## Reader map

| Topic | Current source of truth | Evidence posture |
| --- | --- | --- |
| Active producer contracts | `contracts/domain-data-products/lotus-manage-products.v1.json` | Three active products: portfolio action register, bulk-review campaign membership, and PM operating quality score runs. |
| Repo-native trust telemetry | `contracts/trust-telemetry/*.telemetry.v1.json` | One deterministic contract snapshot per active product; validated by feature and PR-merge lanes. |
| Certification limits | Each telemetry snapshot `certification_limits` block | Checked-in snapshots do not assert live-environment runtime certification. |
| Runtime boundaries | Product-specific boundary notes below | Manage owns workflow evidence; source data, performance, risk, HR, conduct, order, OMS, and execution claims stay outside this repo. |

## Governed products

- Product ID: `lotus-manage:PortfolioActionRegister:v1`
- Product role: governed portfolio action register for management, reporting, gateway,
  Workbench discovery flows, and Lotus Idea opportunity intelligence consumption
- Approved consumers: `lotus-gateway`, `lotus-idea`
- Lotus Idea boundary: `lotus-idea` may consume this product as governed management-action
  evidence for opportunity intelligence and conversion orchestration; it does not own rebalance
  execution, PM operating controls, model-portfolio decisions, order routing, or OMS execution.
- Supportability discovery: direct Idea consumers may call
   `/api/v1/integration/capabilities?consumer_system=lotus-idea&tenant_id=<tenant>` before
   consuming action-register evidence.
- Idea action-intake route foundation: `POST /api/v1/rebalance/idea-action-intake` accepts
  source-safe `lotus-idea` conversion-intent handoff evidence and returns a not-certified
  acknowledgement. It is route-existence proof only; it does not create action-register records,
  approve rebalances, create orders, route OMS instructions, contact clients, authorize
  publication, or promote a supported feature.
- Implemented route families:
   - `/api/v1/rebalance/supportability/summary`
   - `/api/v1/rebalance/idea-action-intake`
   - `/api/v1/rebalance/runs/{rebalance_run_id}/artifact`
   - `/api/v1/rebalance/runs/{rebalance_run_id}/workflow`
   - `/api/v1/rebalance/workflow/decisions`
- Source declaration: `contracts/domain-data-products/lotus-manage-products.v1.json`
- Trust telemetry: `contracts/trust-telemetry/portfolio-action-register.telemetry.v1.json`

- Product ID: `lotus-manage:BulkReviewCampaignMembership:v1`
- Product role: governed Manage-owned campaign membership evidence for bulk-review rebalance
  waves, with optional approval, expiry, access-purpose, source-ref, and actor-entitlement
  governance evidence preserved in the membership envelope.
- Implemented route families:
  - `/api/v1/rebalance/waves/preview`
  - `/api/v1/rebalance/waves`
- Source declaration: `contracts/domain-data-products/lotus-manage-products.v1.json`
- Trust telemetry: `contracts/trust-telemetry/bulk-review-campaign-membership.telemetry.v1.json`

- Product ID: `lotus-manage:PmOperatingQualityScoreRun:v1`
- Product role: governed PM operating quality policy administration, score-run preview,
  immutable persisted score-run lifecycle, bounded fairness-analysis lifecycle, and immutable
  review-action ledger plus summary-invocation history generated from explicit bank policy,
  source-backed evidence, and optional persisted outcome reviews. Optional `pm_book_scope`
  materializes source-owned lotus-core
  `PortfolioManagerBookMembership:v1` evidence into `book_scope_evidence`. Enabled policies carry
  bank approval and fairness-review evidence into score-run `governance_evidence`.
- Implemented route families:
  - `/api/v1/rebalance/pm-operating-quality/policies`
  - `/api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}`
  - `/api/v1/rebalance/pm-operating-quality/score-runs/preview`
  - `/api/v1/rebalance/pm-operating-quality/score-runs`
  - `/api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}`
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview`
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses`
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}`
  - `/api/v1/rebalance/pm-operating-quality/review-actions/preview`
  - `/api/v1/rebalance/pm-operating-quality/review-actions`
  - `/api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}`
  - `/api/v1/rebalance/pm-operating-quality/summary-invocations/preview`
  - `/api/v1/rebalance/pm-operating-quality/summary-invocations`
  - `/api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_invocation_id}`
- Source declaration: `contracts/domain-data-products/lotus-manage-products.v1.json`
- Trust telemetry: `contracts/trust-telemetry/pm-operating-quality-score-run.telemetry.v1.json`
- Boundary: scoring is disabled by default, missing required evidence blocks the run, and HR,
  compensation, conduct-enforcement, autonomous-ranking, AI-generated scoring, source-owner risk,
  performance, execution, and tax methodology remain outside the product contract. PM-book scope
  materialization fails closed for unavailable, incomplete, degraded, or empty source membership.
  Governance approval fails closed for missing approval, invalid or expired expiry, and
  unauthorized actors. Review actions preserve target score-run or fairness-analysis content hashes
  without recalculating scores, recomputing fairness, ranking PMs, or creating HR, compensation,
  conduct, client-contact, trade, order, OMS, or execution decisions. Review actions also carry
  structured `PM_QUALITY_APPROVAL_WORKFLOW_BOUNDARY` evidence with a deterministic content hash so
  consumers can distinguish immutable ledger evidence from unsupported CIO approval workflow,
  policy approval, client approval, trade approval, HR/conduct, order-routing, or OMS execution
  claims.
  Summary invocation rows carry structured `PM_QUALITY_SUMMARY_TEXT_BOUNDARY` evidence with a
  deterministic content hash, proving Manage records workflow/run/artifact refs and hashes only
  without storing or exposing generated summary text, reconstructing prompts or model responses,
  projecting downstream summary UX, contacting clients, approving trades, routing orders, or
  claiming OMS execution.

- Product ID: `lotus-manage:PmOperatingQualityFairnessAnalysis:v1`
- Product role: governed PM operating quality fairness-analysis evidence generated from persisted
  score-run ids and source-defined operating segments. The lifecycle is immutable and supports
  preview, create, list, and get without recomputing score runs.
- Implemented route families:
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview`
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses`
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}`
- Source declaration: `contracts/domain-data-products/lotus-manage-products.v1.json`
- Boundary: Manage validates common policy/as-of scope, minimum scorable segment counts, and
  governed average-score spread over caller-supplied source segments only. It does not infer
  protected classes, discover segments locally, rank PMs, or create HR, compensation, conduct,
  approval, client-contact, execution, or OMS decisions.

## Platform relationship

`lotus-platform` aggregates the repo-native declaration, validates trust telemetry, applies mesh SLO/access/evidence policies, and includes this product in generated catalog, dependency graph, live certification, maturity matrix, evidence packs, and RFC-0092 operating reports.

## Operating rule

Portfolio action state, campaign membership evidence, and explicit PM operating quality score-run
lifecycle evidence belong in `lotus-manage`. Platform certification can block publication when any
active producer product is missing repo-native trust telemetry, serving-route coverage, lifecycle,
access, SLO, or evidence posture. The checked-in snapshots are deterministic contract fixtures
validated by feature and PR-merge lanes; they do not by themselves assert live-environment runtime
certification. PM operating quality score-run lifecycle is not portfolio-memory event projection
and should not be treated as an execution, compensation, HR, conduct, or autonomous-ranking
product.

Stateful `portfolio_id` execution is not yet a promoted mesh consumption mode. The resolver seam is
implemented, but live source-data dependency declaration waits for RFC-087 `lotus-core` composed
DPM source-data products and the updated `sgajbi/lotus-core#330` dependency.
