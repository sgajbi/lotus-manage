"""Shared complete synthetic monthly source assembly for domain and PostgreSQL proofs."""

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.source import MonthlyEligibilitySourceRequest
from tests.composite_monthly_eligibility_helpers import source_snapshot
from tests.composite_staged_eligibility_helpers import lifecycle_material


def assembly_material():
    snapshot = source_snapshot()
    _, _, proposal, *_ = lifecycle_material()
    request = MonthlyEligibilitySourceRequest(
        scope=proposal.proposal.policy.scope,
        month=snapshot.month,
        source_cut_id=snapshot.source_cut_id,
        owner_service="synthetic-source",
        expected_source_revision=snapshot.source_revision,
        expected_content_hash=hash_canonical_payload(snapshot.model_dump(mode="json")),
        expected_portfolio_ids=tuple(snapshot.expected_portfolio_ids),
        reporting_currency=snapshot.reporting_currency,
    )
    inputs = [
        {
            "kind": kind,
            "owner_service": "synthetic-source",
            "source_cut_id": "cut-" + kind,
            "evidence": {
                "product_name": "Synthetic" + kind,
                "product_version": "v1",
                "revision": "r1",
                "digest": "sha256:" + "1" * 64,
            },
        }
        for kind in sorted(["PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"])
    ]
    material = {"observations": snapshot.model_dump(mode="json"), "inputs": inputs}
    return request, {
        "product_name": "CompositeMonthlyEligibilityAssembly",
        "product_version": "v1",
        **material,
        "compatibility_binding": {
            "product_name": "CompositeSourceCutCompatibility",
            "product_version": "v1",
            "revision": "r1",
            "digest": hash_canonical_payload(material),
        },
        "compatibility_posture": "SYNTHETIC_UNQUALIFIED",
    }
