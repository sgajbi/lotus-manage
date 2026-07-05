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
certification-limit drift.

Validate with:

```powershell
make trust-telemetry-validate
python -m pytest tests\unit\test_trust_telemetry_contracts.py -q
```

Checked-in snapshots are contract fixtures validated by feature and PR-merge lanes. They do not by
themselves assert live-environment runtime certification.

