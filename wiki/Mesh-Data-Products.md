# Mesh Data Products

## Mesh role

`lotus-manage` is a maturity-wave producer in the Lotus enterprise data mesh.

## Governed products

- Product ID: `lotus-manage:PortfolioActionRegister:v1`
- Product role: governed portfolio action register for management, reporting, gateway, and
  Workbench discovery flows
- Implemented route families:
  - `/api/v1/rebalance/supportability/summary`
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

- Product ID: `lotus-manage:PmOperatingQualityScoreRun:v1`
- Product role: governed PM operating quality policy administration, score-run preview, and
  immutable persisted lifecycle generated from explicit bank policy, source-backed evidence, and
  optional persisted outcome reviews. Optional `pm_book_scope` materializes source-owned lotus-core
  `PortfolioManagerBookMembership:v1` evidence into `book_scope_evidence`. Enabled policies carry
  bank approval and fairness-review evidence into score-run `governance_evidence`.
- Implemented route families:
  - `/api/v1/rebalance/pm-operating-quality/policies`
  - `/api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}`
  - `/api/v1/rebalance/pm-operating-quality/score-runs/preview`
  - `/api/v1/rebalance/pm-operating-quality/score-runs`
  - `/api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}`
- Source declaration: `contracts/domain-data-products/lotus-manage-products.v1.json`
- Boundary: scoring is disabled by default, missing required evidence blocks the run, and HR,
  compensation, conduct-enforcement, autonomous-ranking, AI-generated scoring, source-owner risk,
  performance, execution, and tax methodology remain outside the product contract. PM-book scope
  materialization fails closed for unavailable, incomplete, degraded, or empty source membership.
  Governance approval fails closed for missing approval, invalid or expired expiry, and
  unauthorized actors.

- Product ID: `lotus-manage:PmOperatingQualityFairnessAnalysis:v1`
- Product role: governed PM operating quality fairness-analysis evidence generated from persisted
  score-run ids and source-defined operating segments. The lifecycle is immutable and supports
  preview, create, list, and get without recomputing score runs.
- Implemented route families:
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview`
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses`
  - `/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}`
- Source declaration: planned mesh promotion after the wider PM-quality product surface is
  Gateway/Workbench-realized; current Manage truth is implementation-backed API evidence.
- Boundary: Manage validates common policy/as-of scope, minimum scorable segment counts, and
  governed average-score spread over caller-supplied source segments only. It does not infer
  protected classes, discover segments locally, rank PMs, or create HR, compensation, conduct,
  approval, client-contact, execution, or OMS decisions.

## Platform relationship

`lotus-platform` aggregates the repo-native declaration, validates trust telemetry, applies mesh SLO/access/evidence policies, and includes this product in generated catalog, dependency graph, live certification, maturity matrix, evidence packs, and RFC-0092 operating reports.

## Operating rule

Portfolio action state, campaign membership evidence, and explicit PM operating quality score-run
lifecycle evidence belong in `lotus-manage`. Platform certification can block publication when
action-register telemetry, lifecycle, access, SLO, or evidence posture drifts. PM operating quality
score-run lifecycle is not portfolio-memory event projection and should not be treated as an
execution, compensation, HR, conduct, or autonomous-ranking product.

Stateful `portfolio_id` execution is not yet a promoted mesh consumption mode. The resolver seam is
implemented, but live source-data dependency declaration waits for RFC-087 `lotus-core` composed
DPM source-data products and the updated `sgajbi/lotus-core#330` dependency.
