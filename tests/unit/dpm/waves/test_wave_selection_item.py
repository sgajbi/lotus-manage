from pytest import MonkeyPatch

from src.api.services import wave_selection_item
from src.api.services.wave_selection_item import with_selection_and_proof_pack
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.waves import DpmRebalanceWaveItem


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
        construction_repository=object(),  # type: ignore[arg-type]
        proof_pack_repository=object(),  # type: ignore[arg-type]
        mandate_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
    )


def test_selection_without_proof_pack_records_degraded_proof_pack_state() -> None:
    updated = _select(generate_proof_pack=False)

    assert updated.state == "SELECTED"
    assert updated.selected_alternative_id == "alt_selected"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVE_SELECTED"]
    assert updated.diagnostics == {
        "existing": "value",
        "selection_actor_id": "pm_001",
        "selection_reason_code": "LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
        "selection_comment": "Selected by PM desk.",
        "proof_pack_state": "DEGRADED",
        "proof_pack_reason_code": "PROOF_PACK_GENERATION_NOT_REQUESTED",
    }


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


def test_selection_records_degraded_proof_pack_generation_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    def _generate(**_kwargs: object) -> DpmPreTradeProofPack:
        raise RuntimeError("proof pack unavailable")

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
    assert updated.diagnostics["proof_pack_error"] == "RuntimeError"


def test_wave_selection_item_exports_only_selection_builder() -> None:
    assert wave_selection_item.__all__ == ["with_selection_and_proof_pack"]
