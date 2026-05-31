"""Construction alternative portfolio-memory event projection."""

from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.search_filters import count_values
from src.core.portfolio_memory.supportability import source_supportability_state


def construction_alternative_set_event(
    alternative_set: ConstructionAlternativeSet,
) -> DpmPortfolioMemoryEvent:
    method_counts = count_values(
        alternative.method.value for alternative in alternative_set.alternatives
    )
    reason_codes = sorted(
        {
            "CONSTRUCTION_ALTERNATIVE_SET_READY",
            alternative_set.status.value,
            *(
                alternative.method_status.value
                for alternative in alternative_set.alternatives
                if alternative.method_status.value != alternative_set.status.value
            ),
        }
    )
    content_hash = construction_alternative_set_content_hash(alternative_set)
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:construction:{alternative_set.alternative_set_id}:generated",
        event_type="CONSTRUCTION_ALTERNATIVE_SET",
        event_time=alternative_set.generated_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
        source_id=alternative_set.alternative_set_id,
        status=alternative_set.status.value,
        supportability_state=source_supportability_state(alternative_set.status.value),
        summary=(
            f"Construction alternative set {alternative_set.alternative_set_id} generated "
            f"with {len(alternative_set.alternatives)} alternatives."
        ),
        reason_codes=reason_codes,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
                source_id=alternative_set.alternative_set_id,
                content_hash=content_hash,
            )
        ],
        content_hash=content_hash,
        metadata={
            "as_of": alternative_set.as_of,
            "alternative_count": len(alternative_set.alternatives),
            "method_counts": method_counts,
            "input_mode": alternative_set.input_mode,
            "source_supportability_state": alternative_set.source_supportability_state,
            "request_hash_available": alternative_set.request_hash is not None,
            "raw_request_payload_projected": False,
        },
    )


def construction_selection_event(
    *,
    alternative_set: ConstructionAlternativeSet,
    selection: ConstructionAlternativeSelection,
) -> DpmPortfolioMemoryEvent:
    selected_alternative = next(
        (
            alternative
            for alternative in alternative_set.alternatives
            if alternative.alternative_id == selection.alternative_id
        ),
        None,
    )
    content_hash = hash_canonical_payload(selection.model_dump(mode="json"))
    alternative_set_content_hash = construction_alternative_set_content_hash(alternative_set)
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:construction:{alternative_set.alternative_set_id}:selection:{selection.selection_id}",
        event_type="CONSTRUCTION_ALTERNATIVE_SELECTED",
        event_time=selection.selected_at.isoformat(),
        actor=selection.actor_id,
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE_SELECTION",
        source_id=selection.selection_id,
        status="SELECTED",
        supportability_state="READY",
        summary=(
            f"Construction alternative {selection.alternative_id} selected from "
            f"{alternative_set.alternative_set_id}."
        ),
        reason_codes=[selection.reason_code],
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
                source_id=alternative_set.alternative_set_id,
                content_hash=alternative_set_content_hash,
            ),
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE_SELECTION",
                source_id=selection.selection_id,
                content_hash=content_hash,
            ),
        ],
        content_hash=content_hash,
        metadata={
            "alternative_set_id": alternative_set.alternative_set_id,
            "alternative_id": selection.alternative_id,
            "selected_method": selected_alternative.method.value
            if selected_alternative is not None
            else None,
            "selected_method_status": selected_alternative.method_status.value
            if selected_alternative is not None
            else None,
            "correlation_id": selection.correlation_id,
            "comment_projected": selection.comment is not None,
            "raw_selection_payload_projected": False,
        },
    )


def construction_alternative_set_content_hash(
    alternative_set: ConstructionAlternativeSet,
) -> str:
    return alternative_set.request_hash or hash_canonical_payload(
        alternative_set.model_dump(mode="json")
    )
