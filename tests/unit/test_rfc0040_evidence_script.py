import json

import pytest

from scripts.generate_rfc0040_proof_pack_evidence import (
    EvidenceError,
    _assert_ready_handoff_pack,
    _contains_forbidden_ai_field,
    _content_hash,
    _section_states,
    _stable_json,
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
