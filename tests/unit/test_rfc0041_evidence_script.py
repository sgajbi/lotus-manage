import json

from scripts.generate_rfc0041_wave_evidence import (
    _aggregate_reconciliation,
    _content_hash,
    _render_critical_review,
    _stable_json,
    build_critical_review,
)


SOURCE_ANALYTICS = [
    {
        "source_family": "RISK",
        "supportability_state": "READY",
        "source_refs": [{"source_system": "lotus-risk"}],
    },
    {
        "source_family": "PERFORMANCE",
        "supportability_state": "DEGRADED",
        "source_refs": [{"source_system": "lotus-performance"}],
    },
]


def test_rfc0041_evidence_script_hashes_stable_json() -> None:
    first = _stable_json({"b": 2, "a": 1})
    second = _stable_json({"a": 1, "b": 2})

    assert first == second
    assert _content_hash(first).startswith("sha256:")
    assert _content_hash(first) == _content_hash(second)
    assert list(json.loads(first)) == ["a", "b"]


def test_rfc0041_aggregate_reconciliation_requires_exceptions_and_no_execution_claim() -> None:
    reconciliation = _aggregate_reconciliation(
        {
            "final_item_state_counts": {
                "HANDOFF_READY": 1,
                "SOURCE_DEGRADED": 1,
                "REVIEW_REQUIRED": 1,
                "SOURCE_BLOCKED": 1,
            },
            "source_analytics": SOURCE_ANALYTICS,
            "external_execution_claimed": False,
        }
    )

    assert reconciliation["passed"] is True
    assert reconciliation["item_total"] == 4
    assert reconciliation["ready_total"] == 1
    assert reconciliation["blocked_total"] == 1

    failed = _aggregate_reconciliation(
        {
            "final_item_state_counts": {"HANDOFF_READY": 1, "SOURCE_BLOCKED": 1},
            "source_analytics": SOURCE_ANALYTICS,
            "external_execution_claimed": True,
        }
    )
    assert failed["passed"] is False


def test_rfc0041_critical_review_is_machine_readable_and_markdown_renderable() -> None:
    manifest = {
        "output_dir": "output/rfc0041-wave-proof/test",
        "lifecycle": {
            "wave_id": "dwv_test",
            "cancel_wave_id": "dwv_cancel_test",
            "proof_pack_id": "dpp_test",
            "final_wave_state": "HANDOFF_READY",
            "cancel_wave_state": "CANCELLED",
            "final_item_state_counts": {
                "HANDOFF_READY": 1,
                "SOURCE_DEGRADED": 1,
                "REVIEW_REQUIRED": 1,
                "SOURCE_BLOCKED": 1,
            },
            "source_analytics": SOURCE_ANALYTICS,
            "supportability_state": "blocked",
            "supportability_reason": "wave_blocked_items",
            "proof_pack_linked_item_count": 1,
            "handoff_ref_count": 1,
            "external_execution_claimed": False,
        },
        "openapi_certification": {"passed": True, "missing": [], "weak": []},
        "aggregate_reconciliation": {
            "passed": True,
            "risk_source_state": "READY",
            "performance_source_state": "DEGRADED",
            "source_analytics_families": ["PERFORMANCE", "RISK"],
        },
    }

    review = build_critical_review(manifest)
    markdown = _render_critical_review(review)

    assert review["result"] == "passed"
    assert all(review["checks"].values())
    assert {finding["status"] for finding in review["findings"]} == {
        "passed",
        "accepted_boundary",
    }
    assert "# RFC-0041 Live Proof Critical Review" in markdown
    assert "`wave_reached_handoff_ready`: PASS" in markdown
