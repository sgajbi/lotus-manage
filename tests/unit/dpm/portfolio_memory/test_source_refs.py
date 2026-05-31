from src.core.mandates import DpmSourceProductLineage
from src.core.outcomes import DpmOutcomeSourceRef
from src.core.portfolio_memory.source_refs import (
    from_outcome_source_ref,
    from_proof_pack_evidence_ref,
    from_proof_pack_source_ref,
    from_source_product_lineage,
    from_wave_source_ref,
    proof_pack_source_refs,
)
from src.core.proof_packs import DpmProofPackEvidenceRef, DpmProofPackSourceRef
from src.core.waves.models import DpmWaveSourceRef
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


def test_portfolio_memory_source_ref_mappers_preserve_source_owned_identity() -> None:
    proof_source_ref = from_proof_pack_source_ref(
        DpmProofPackSourceRef(
            source_system="lotus-risk",
            source_type="RegimeScenarioPackEvaluation",
            source_id="scenario-pack-001",
            supportability_state="READY",
            content_hash="sha256:risk-scenario",
        )
    )
    assert proof_source_ref.source_system == "lotus-risk"
    assert proof_source_ref.source_type == "RegimeScenarioPackEvaluation"
    assert proof_source_ref.source_id == "scenario-pack-001"
    assert proof_source_ref.supportability_state == "READY"
    assert proof_source_ref.content_hash == "sha256:risk-scenario"

    proof_evidence_ref = from_proof_pack_evidence_ref(
        DpmProofPackEvidenceRef(
            source_system="lotus-report",
            ref_type="REPORT_INPUT",
            ref_id="report-input-001",
            content_hash="sha256:report-input",
        )
    )
    assert proof_evidence_ref.source_type == "REPORT_INPUT"
    assert proof_evidence_ref.source_id == "report-input-001"
    assert proof_evidence_ref.content_hash == "sha256:report-input"

    wave_ref = from_wave_source_ref(
        DpmWaveSourceRef(
            source_system="lotus-core",
            source_type="PortfolioManagerBookMembership",
            source_id="pm-book-001",
            source_version="v1",
            supportability_state="READY",
            content_hash="sha256:pm-book",
        )
    )
    assert wave_ref.source_version == "v1"
    assert wave_ref.content_hash == "sha256:pm-book"

    outcome_ref = from_outcome_source_ref(
        DpmOutcomeSourceRef(
            source_system="lotus-performance",
            source_type="MandatePerformanceHealthContext",
            source_id="performance-health-001",
            source_version="v1",
            content_hash="sha256:performance-health",
        )
    )
    assert outcome_ref.source_system == "lotus-performance"
    assert outcome_ref.source_type == "MandatePerformanceHealthContext"


def test_source_product_lineage_ref_falls_back_to_product_name_for_missing_record_id() -> None:
    lineage_ref = from_source_product_lineage(
        DpmSourceProductLineage(
            product_name="DiscretionaryMandateBinding",
            product_version="v1",
            source_system="lotus-core",
            source_record_id=None,
            data_quality_status="READY",
        )
    )

    assert lineage_ref.source_id == "DiscretionaryMandateBinding"
    assert lineage_ref.source_type == "DiscretionaryMandateBinding"
    assert lineage_ref.supportability_state == "READY"


def test_proof_pack_source_refs_dedupe_and_sort_source_evidence() -> None:
    proof_pack = _proof_pack()
    source_refs = proof_pack_source_refs(proof_pack)
    source_ref_keys = [(ref.source_system, ref.source_type, ref.source_id) for ref in source_refs]

    assert source_ref_keys == sorted(set(source_ref_keys))
    assert source_refs
