import pytest
from pytest import MonkeyPatch

from src.api.services import wave_selection_item
from src.api.services.wave_selection_item import with_selection_and_proof_pack
from src.core.proof_packs import ProofPackSourceValidationError
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.waves import DpmRebalanceWaveItem
from src.core.construction import (
    build_alternative_set,
    build_rebalance_result_alternative,
    build_do_nothing_baseline,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from tests.unit.dpm.construction.test_alternative_engine import _ready_rebalance_result


def _construction_repository() -> InMemoryConstructionRepository:
    repository = InMemoryConstructionRepository()
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result, alternative_id="alt_selected")
    alternative_set = build_alternative_set(
        alternative_set_id="cas_select",
        portfolio_id="PB_SG_SELECT",
        as_of="2026-05-03",
        alternatives=[alternative, build_do_nothing_baseline(result=result)],
    ).model_copy(update={"tenant_id": "tenant-test"})
    repository.save_alternative_set(alternative_set=alternative_set, idempotency_key=None)
    return repository


def _item() -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_select",
        portfolio_id="PB_SG_SELECT",
        mandate_id="MANDATE_PB_SG_SELECT",
        state="SIMULATED",
        alternative_set_id="cas_select",
        diagnostics={"existing": "value"},
    )


def _select(*, generate_proof_pack: bool = True) -> DpmRebalanceWaveItem:
    return with_selection_and_proof_pack(
        item=_item(),
        alternative_id="alt_selected",
        actor_id="pm_001",
        reason_code="LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
        comment="Selected by PM desk.",
        correlation_id="corr-select",
        generate_proof_pack=generate_proof_pack,
        construction_repository=_construction_repository(),
        proof_pack_repository=object(),  # type: ignore[arg-type]
        mandate_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        tenant_id="tenant-test",
    )


def test_selection_without_proof_pack_records_degraded_proof_pack_state() -> None:
    updated = _select(generate_proof_pack=False)

    assert updated.state == "SELECTED"
    assert updated.selected_alternative_id == "alt_selected"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVE_SELECTED"]
    assert updated.diagnostics == {
        "existing": "value",
        "proposed_changes": _construction_repository()
        .get_alternative_set(alternative_set_id="cas_select", tenant_id="tenant-test")
        .alternatives[0]
        .diagnostics["proposed_changes"],
        "selection_actor_id": "pm_001",
        "selection_reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
        "selection_comment": "Selected by PM desk.",
        "proof_pack_state": "DEGRADED",
        "proof_pack_reason_code": "PROOF_PACK_GENERATION_NOT_REQUESTED",
    }


def test_no_action_selection_clears_heuristic_proposals_and_prior_proof() -> None:
    item = _item().model_copy(
        update={
            "proof_pack_id": "dpp_heuristic",
            "diagnostics": {"proposed_changes": [{"action": "BUY"}], "proof_pack_state": "READY"},
        }
    )
    updated = with_selection_and_proof_pack(
        item=item,
        alternative_id="alt_do_nothing_baseline",
        actor_id="pm-test",
        reason_code="NO_ACTION",
        comment=None,
        correlation_id="corr-no-action",
        tenant_id="tenant-test",
        generate_proof_pack=False,
        construction_repository=_construction_repository(),
        proof_pack_repository=object(),
        mandate_repository=object(),
        run_service=object(),
    )
    assert updated.selected_alternative_id == "alt_do_nothing_baseline"
    assert updated.diagnostics["proposed_changes"] == []
    assert updated.proof_pack_id is None
    assert updated.diagnostics["proof_pack_state"] == "DEGRADED"


def test_selection_links_generated_proof_pack(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _generate(**kwargs: object) -> DpmPreTradeProofPack:
        captured.update(kwargs)
        return DpmPreTradeProofPack.model_construct(
            proof_pack_id="dpp_selected",
            status="READY",
        )

    monkeypatch.setattr(
        wave_selection_item.proof_pack_service,
        "generate_proof_pack_from_selected_alternative",
        _generate,
    )

    updated = _select()

    assert captured["alternative_set_id"] == "cas_select"
    assert captured["selected_alternative_id"] == "alt_selected"
    assert captured["idempotency_key"] == "wave:dwi_select:proof-pack:alt_selected"
    assert captured["mandate_id"] == "MANDATE_PB_SG_SELECT"
    assert updated.state == "PROOF_PACK_READY"
    assert updated.proof_pack_id == "dpp_selected"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVE_SELECTED", "PROOF_PACK_READY"]
    assert updated.diagnostics["proof_pack_state"] == "READY"


def test_blocked_proof_pack_stays_selected_and_cannot_advance(monkeypatch: MonkeyPatch) -> None:
    from src.api.services.wave_item_transitions import approve_item, stage_item, handoff_item
    from src.api.services.wave_supportability_diagnostics import supportability_issue

    monkeypatch.setattr(
        wave_selection_item.proof_pack_service,
        "generate_proof_pack_from_selected_alternative",
        lambda **kwargs: DpmPreTradeProofPack.model_construct(
            proof_pack_id="dpp_blocked", status="BLOCKED"
        ),
    )
    updated = _select()
    assert updated.state == "SELECTED"
    assert updated.proof_pack_id == "dpp_blocked"
    assert "PROOF_PACK_BLOCKED" in updated.reason_codes
    assert "PROOF_PACK_READY" not in updated.reason_codes
    assert approve_item(updated, "pm", "APPROVE", None) == updated
    for state, transition in [
        ("PROOF_PACK_READY", approve_item),
        ("APPROVED", stage_item),
        ("STAGED", handoff_item),
        ("HANDOFF_READY", handoff_item),
    ]:
        retained = updated.model_copy(update={"state": state, "reason_codes": ["OLD_READY"]})
        assert transition(retained, "pm", "ADVANCE", None) == retained
        issue = supportability_issue(wave_id="wave", item=retained, item_index=0)
        assert issue is not None
        assert issue["severity"] == "CRITICAL"
        assert "PROOF_PACK_BLOCKED" in issue["reason_codes"]
        assert issue["remediation_route"] == "REPAIR_BLOCKED_PROOF_PACK"


@pytest.mark.parametrize("target", ["APPROVED", "STAGED", "HANDOFF_READY"])
def test_retained_blocked_target_state_is_not_eligible_for_wave_transition(target: str) -> None:
    from src.api.services.wave_approval_transition import build_approved_wave
    from src.api.services.wave_stage_transition import build_staged_wave
    from src.api.services.wave_handoff_transition import build_handoff_ready_wave
    from src.api.services.wave_errors import DpmWaveValidationError
    from src.core.waves import DpmRebalanceWave

    builders = {
        "APPROVED": build_approved_wave,
        "STAGED": build_staged_wave,
        "HANDOFF_READY": build_handoff_ready_wave,
    }
    retained = _item().model_copy(
        update={"state": target, "diagnostics": {"proof_pack_state": "BLOCKED"}}
    )
    wave = DpmRebalanceWave.model_construct(wave_id="wave_blocked", items=[retained])
    with pytest.raises(DpmWaveValidationError) as rejected:
        builders[target](
            wave=wave,
            actor_id="pm",
            reason_code="ADVANCE",
            comment=None,
            correlation_id="corr-blocked",
        )
    assert rejected.value.code.endswith("NO_ELIGIBLE_ITEMS")


def test_selection_records_degraded_proof_pack_generation_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    def _generate(**_kwargs: object) -> DpmPreTradeProofPack:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_NOT_FOUND")

    monkeypatch.setattr(
        wave_selection_item.proof_pack_service,
        "generate_proof_pack_from_selected_alternative",
        _generate,
    )

    updated = _select()

    assert updated.state == "SELECTED"
    assert updated.selected_alternative_id == "alt_selected"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVE_SELECTED"]
    assert updated.diagnostics["proof_pack_state"] == "DEGRADED"
    assert updated.diagnostics["proof_pack_reason_code"] == "PROOF_PACK_GENERATION_FAILED"
    assert updated.diagnostics["proof_pack_error"] == "ProofPackSourceValidationError"


def test_selection_does_not_hide_unexpected_proof_pack_generation_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    def _generate(**_kwargs: object) -> DpmPreTradeProofPack:
        raise RuntimeError("proof pack repository side effect failed")

    monkeypatch.setattr(
        wave_selection_item.proof_pack_service,
        "generate_proof_pack_from_selected_alternative",
        _generate,
    )

    with pytest.raises(RuntimeError, match="proof pack repository side effect failed"):
        _select()


def test_wave_selection_item_exports_only_selection_builder() -> None:
    assert wave_selection_item.__all__ == ["with_selection_and_proof_pack"]
