"""Source-reference projection helpers for portfolio memory."""

from src.core.mandates import DpmSourceProductLineage
from src.core.outcomes.models import DpmOutcomeSourceRef
from src.core.portfolio_memory.models import DpmPortfolioMemorySourceRef
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackSourceRef,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.models import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveSourceRef


def proof_pack_source_refs(
    proof_pack: DpmPreTradeProofPack,
) -> list[DpmPortfolioMemorySourceRef]:
    refs: dict[tuple[str, str, str], DpmPortfolioMemorySourceRef] = {}
    for section in proof_pack.sections:
        for ref in section.source_refs:
            memory_ref = from_proof_pack_source_ref(ref)
            refs[(memory_ref.source_system, memory_ref.source_type, memory_ref.source_id)] = (
                memory_ref
            )
    return sorted(
        refs.values(), key=lambda ref: (ref.source_system, ref.source_type, ref.source_id)
    )


def proof_pack_artifact_refs(
    proof_pack: DpmPreTradeProofPack,
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [
        ref
        for ref in [
            proof_pack.markdown_summary_ref,
            proof_pack.report_input_ref,
            proof_pack.ai_evidence_ref,
        ]
        if ref is not None
    ]
    return [from_proof_pack_evidence_ref(ref) for ref in refs]


def wave_source_refs(
    *,
    wave: DpmRebalanceWave,
    items: list[DpmRebalanceWaveItem],
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [from_wave_source_ref(ref) for ref in wave.trigger.source_refs]
    for item in items:
        refs.extend(from_wave_source_ref(ref) for ref in item.source_refs)
    return sorted(refs, key=lambda ref: (ref.source_system, ref.source_type, ref.source_id))


def campaign_definition_source_refs(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    portfolio_id: str,
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [from_wave_source_ref(ref) for ref in definition.source_refs]
    if definition.governance is not None:
        refs.extend(from_wave_source_ref(ref) for ref in definition.governance.source_refs)
    for candidate in definition.candidates:
        if candidate.portfolio_id == portfolio_id:
            refs.extend(from_wave_source_ref(ref) for ref in candidate.source_refs)
    unique = {
        (ref.source_system, ref.source_type, ref.source_id, ref.source_version): ref for ref in refs
    }
    return sorted(
        unique.values(),
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )


def campaign_definition_artifact_ref(
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignDefinition",
        source_id=f"{definition.campaign_id}:{definition.campaign_version}",
        source_version=definition.product_version,
        content_hash=definition.content_hash,
    )


def from_proof_pack_source_ref(ref: DpmProofPackSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        supportability_state=ref.supportability_state,
        content_hash=ref.content_hash,
    )


def from_proof_pack_evidence_ref(ref: DpmProofPackEvidenceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.ref_type,
        source_id=ref.ref_id,
        content_hash=ref.content_hash,
    )


def from_wave_source_ref(ref: DpmWaveSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        source_version=ref.source_version,
        supportability_state=ref.supportability_state,
        content_hash=ref.content_hash,
    )


def from_outcome_source_ref(ref: DpmOutcomeSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        source_version=ref.source_version,
        content_hash=ref.content_hash,
    )


def from_source_product_lineage(ref: DpmSourceProductLineage) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.product_name,
        source_id=ref.source_record_id or ref.product_name,
        source_version=ref.product_version,
        supportability_state=ref.data_quality_status,
    )
