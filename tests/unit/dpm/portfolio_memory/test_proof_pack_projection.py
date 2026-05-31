from src.core.portfolio_memory.proof_pack_projection import proof_pack_events
from src.core.proof_packs import DpmProofPackEvidenceRef
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


def test_proof_pack_created_event_projects_source_refs_and_artifact_refs() -> None:
    proof_pack = _proof_pack().model_copy(
        update={
            "markdown_summary_ref": DpmProofPackEvidenceRef(
                source_system="lotus-report",
                ref_type="MARKDOWN_SUMMARY",
                ref_id="dpm-proof-pack-summary-001",
                content_hash="sha256:proof-pack-summary",
            )
        }
    )

    event = proof_pack_events(proof_pack)[0]

    assert event.event_type == "PROOF_PACK_CREATED"
    assert event.source_type == "DPM_PRE_TRADE_PROOF_PACK"
    assert event.source_id == proof_pack.proof_pack_id
    assert event.supportability_state == "DEGRADED"
    assert event.reason_codes == proof_pack.supportability.reason_codes
    assert event.source_refs
    assert event.artifact_refs[0].source_system == "lotus-report"
    assert event.artifact_refs[0].source_type == "MARKDOWN_SUMMARY"
    assert event.content_hash == proof_pack.content_hash
    assert event.metadata["rebalance_run_id"] == proof_pack.rebalance_run_id


def test_proof_pack_timeline_event_reuses_source_refs_and_evidence_artifacts() -> None:
    proof_pack = _proof_pack()
    timeline_event = proof_pack.decision_timeline.events[0].model_copy(
        update={
            "artifact_refs": [
                DpmProofPackEvidenceRef(
                    source_system="lotus-report",
                    ref_type="REPORT_INPUT",
                    ref_id="dpm-report-input-001",
                    content_hash="sha256:report-input",
                )
            ]
        }
    )
    proof_pack = proof_pack.model_copy(
        update={
            "decision_timeline": proof_pack.decision_timeline.model_copy(
                update={"events": [timeline_event]}
            )
        }
    )

    events = proof_pack_events(proof_pack)
    timeline_memory_event = events[1]

    assert timeline_memory_event.event_type == "PROOF_PACK_TIMELINE_EVENT"
    assert timeline_memory_event.source_type == timeline_event.event_type
    assert timeline_memory_event.supportability_state == "READY"
    assert timeline_memory_event.source_refs == events[0].source_refs
    assert timeline_memory_event.artifact_refs[0].source_id == "dpm-report-input-001"
    assert timeline_memory_event.metadata == {"proof_pack_id": proof_pack.proof_pack_id}
