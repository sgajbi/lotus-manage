# Trust Telemetry

This folder contains deterministic repo-native trust telemetry snapshots for active Manage
producer products.

| Snapshot | Product |
| --- | --- |
| `portfolio-action-register.telemetry.v1.json` | `lotus-manage:PortfolioActionRegister:v1` |
| `bulk-review-campaign-membership.telemetry.v1.json` | `lotus-manage:BulkReviewCampaignMembership:v1` |
| `pm-operating-quality-score-run.telemetry.v1.json` | `lotus-manage:PmOperatingQualityScoreRun:v1` |

Every active product in `contracts/domain-data-products/lotus-manage-products.v1.json` must have
exactly one snapshot here. The focused test
`tests/unit/test_trust_telemetry_contracts.py` derives coverage from that producer declaration and
fails on missing, unexpected, stale-route, freshness, metadata, lineage, artifact, or
certification-limit drift. Active catalog visibility is not the same as certification readiness:
product-specific posture expectations may require a blocked or operator-only fixture until linked
certification blockers are resolved and runtime trust evidence is regenerated.
Not-certified route foundations, including `POST /api/v1/rebalance/idea-action-intake`, may be
carried as explicit `route_foundations` evidence but must not appear in unblocked
customer-consumable `serving_routes`.

Validate with:

```powershell
make trust-telemetry-validate
python -m pytest tests\unit\test_trust_telemetry_contracts.py -q
```

Checked-in snapshots are contract fixtures validated by feature and PR-merge lanes. They do not by
themselves assert live-environment runtime certification.

`pm-operating-quality-score-run.telemetry.v1.json` is intentionally blocked while PM-quality
certification evidence remains branch-local or pending runtime regeneration. It must not publish
`quality_passed`, complete/reconciled, customer-consumable evidence until the linked PM-quality
certification blockers are merged to `main` and the trust snapshot is deliberately promoted.

`bulk-review-campaign-membership.telemetry.v1.json` is intentionally blocked while the platform
maturity matrix classifies `lotus-manage:BulkReviewCampaignMembership:v1` as
`deferred`/`future_wave` and product-specific mesh SLO, access, evidence-pack, and runtime
certification evidence are missing. The fixture carries `tenant_id=tenant-sg` to match the
tenant-scoped campaign-definition repository boundary, but it must remain operator-only
`quality_blocked` telemetry until those policy and certification gaps are deliberately closed.

