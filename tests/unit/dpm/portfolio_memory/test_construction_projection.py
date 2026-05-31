from datetime import datetime, timezone

from src.core.construction import build_alternative_set, build_do_nothing_baseline
from src.core.construction.models import ConstructionAlternativeSelection
from src.core.portfolio_memory.construction_projection import (
    construction_alternative_set_content_hash,
    construction_alternative_set_event,
    construction_selection_event,
)
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID
from tests.unit.dpm.construction.test_alternative_engine import _ready_rebalance_result


def _alternative_set():
    return build_alternative_set(
        alternative_set_id="cas_projection_001",
        portfolio_id=PORTFOLIO_ID,
        as_of="2026-05-31",
        alternatives=[build_do_nothing_baseline(result=_ready_rebalance_result())],
    ).model_copy(
        update={
            "request_hash": "sha256:construction-projection",
            "generated_at": datetime(2026, 5, 31, 9, 30, tzinfo=timezone.utc),
            "source_supportability_state": "READY",
        }
    )


def test_construction_alternative_set_event_preserves_hash_and_no_raw_payload_boundary() -> None:
    alternative_set = _alternative_set()

    event = construction_alternative_set_event(alternative_set)

    assert event.event_type == "CONSTRUCTION_ALTERNATIVE_SET"
    assert event.source_type == "DPM_CONSTRUCTION_ALTERNATIVE_SET"
    assert event.supportability_state == "READY"
    assert event.content_hash == "sha256:construction-projection"
    assert event.artifact_refs[0].content_hash == "sha256:construction-projection"
    assert event.metadata["method_counts"] == {"DO_NOTHING_BASELINE": 1}
    assert event.metadata["request_hash_available"] is True
    assert event.metadata["raw_request_payload_projected"] is False


def test_construction_selection_event_preserves_selection_and_set_artifact_refs() -> None:
    alternative_set = _alternative_set()
    selection = ConstructionAlternativeSelection(
        selection_id="casel_projection_001",
        alternative_set_id=alternative_set.alternative_set_id,
        alternative_id="alt_do_nothing_baseline",
        actor_id="pm_001",
        reason_code="MINIMIZE_TURNOVER",
        comment="Keep portfolio stable for review.",
        correlation_id="corr-construction-projection",
        selected_at=datetime(2026, 5, 31, 10, 30, tzinfo=timezone.utc),
    )

    event = construction_selection_event(
        alternative_set=alternative_set,
        selection=selection,
    )

    assert event.event_type == "CONSTRUCTION_ALTERNATIVE_SELECTED"
    assert event.supportability_state == "READY"
    assert event.reason_codes == ["MINIMIZE_TURNOVER"]
    assert event.artifact_refs[0].content_hash == construction_alternative_set_content_hash(
        alternative_set
    )
    assert event.artifact_refs[1].source_id == selection.selection_id
    assert event.metadata["selected_method"] == "DO_NOTHING_BASELINE"
    assert event.metadata["comment_projected"] is True
    assert event.metadata["raw_selection_payload_projected"] is False


def test_construction_alternative_set_content_hash_falls_back_when_request_hash_absent() -> None:
    alternative_set = _alternative_set().model_copy(update={"request_hash": None})

    assert construction_alternative_set_content_hash(alternative_set).startswith("sha256:")
