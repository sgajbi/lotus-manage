import json

import pytest

from scripts.generate_rfc0040_proof_pack_evidence import (
    EvidenceError,
    _assert_ready_handoff_pack,
    _contains_forbidden_ai_field,
    _content_hash,
    _section_states,
    _stable_json,
    build_critical_review,
)


def test_rfc0040_evidence_script_hashes_stable_json() -> None:
    first = _stable_json({"b": 2, "a": 1})
    second = _stable_json({"a": 1, "b": 2})

    assert first == second
    assert _content_hash(first).startswith("sha256:")
    assert _content_hash(first) == _content_hash(second)
    assert list(json.loads(first)) == ["a", "b"]


def test_rfc0040_evidence_script_detects_forbidden_ai_field_names_recursively() -> None:
    assert _contains_forbidden_ai_field({"sections": [{"bounded_facts": {"client_id": "x"}}]})
    assert _contains_forbidden_ai_field({"sections": [{"bounded_facts": {"Client_Name": "x"}}]})
    assert not _contains_forbidden_ai_field(
        {"sections": [{"bounded_facts": {"portfolio_id": "PB_SG_GLOBAL_BAL_001"}}]}
    )


def test_rfc0040_evidence_script_requires_handoff_refs_and_ready_sections() -> None:
    proof_pack = {
        "content_hash": "sha256:abc",
        "report_input_ref": {"ref_type": "DPM_PROOF_PACK_REPORT_INPUT"},
        "ai_evidence_ref": {"ref_type": "DPM_PROOF_PACK_AI_EVIDENCE_INPUT"},
        "sections": [
            {"section_type": "reporting_refs", "state": "READY"},
            {"section_type": "ai_refs", "state": "READY"},
        ],
    }

    _assert_ready_handoff_pack(proof_pack)
    assert _section_states(proof_pack) == {"reporting_refs": "READY", "ai_refs": "READY"}

    proof_pack["sections"][0]["state"] = "DEGRADED"
    with pytest.raises(EvidenceError, match="reporting_refs section not READY"):
        _assert_ready_handoff_pack(proof_pack)


def test_rfc0040_evidence_script_builds_machine_readable_critical_review() -> None:
    ready_states = {
        "reporting_refs": "READY",
        "ai_refs": "READY",
        "selected_alternative": "READY",
        "mandate_context": "DEGRADED",
        "risk_impact": "DEGRADED",
    }
    review = build_critical_review(
        {
            "output_dir": "output/rfc0040-proof/test",
            "validation": {"ai_forbidden_field_guardrail": "passed"},
            "scenarios": {
                "direct_rebalance_run": {
                    "proof_pack_id": "dpp_direct",
                    "section_states": ready_states,
                    "source_hash_keys": ["rebalance_run"],
                },
                "selected_alternative": {
                    "proof_pack_id": "dpp_selected",
                    "section_states": ready_states,
                    "source_hash_keys": ["alternative_set", "selected_alternative"],
                },
                "missing_mandate_blocked": {
                    "proof_pack_id": "dpp_blocked",
                    "status": "BLOCKED",
                    "section_states": {**ready_states, "mandate_context": "BLOCKED"},
                },
            },
        }
    )

    assert review["result"] == "passed_with_controlled_downstream_boundaries"
    assert review["checks"]["direct_run_handoffs_ready"] is True
    assert review["checks"]["selected_alternative_trace_ready"] is True
    assert review["checks"]["mandate_context_source_honest"] is True
    assert review["checks"]["missing_mandate_blocks_promotion"] is True
    assert review["checks"]["full_front_office_claim_withheld"] is True
    assert {finding["status"] for finding in review["findings"]} == {
        "passed",
        "accepted_boundary",
    }
