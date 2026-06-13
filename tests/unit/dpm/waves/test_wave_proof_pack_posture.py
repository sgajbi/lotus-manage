from src.api.services.wave_proof_pack_posture import (
    _degraded_proof_pack_count,
    _external_execution_claimed,
    _proof_pack_refs,
    _ready_proof_pack_count,
    proof_pack_posture_for_wave,
)
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveHandoffRef


def test_proof_pack_posture_counts_refs_and_preserves_boundaries() -> None:
    wave = DpmRebalanceWave.model_construct(
        wave_id="dwv_posture",
        state="HANDOFF_READY",
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_ready",
                portfolio_id="PB_SG_READY",
                state="HANDOFF_READY",
                proof_pack_id="dpp_ready",
                diagnostics={"proof_pack_state": "READY"},
                selected_alternative_id="alt_ready",
            ),
            DpmRebalanceWaveItem(
                wave_item_id="dwi_degraded",
                portfolio_id="PB_SG_DEGRADED",
                state="PROOF_PACK_READY",
                proof_pack_id="dpp_degraded",
                diagnostics={"proof_pack_state": "DEGRADED"},
                selected_alternative_id="alt_degraded",
            ),
        ],
        handoff_refs=[
            DpmWaveHandoffRef.model_construct(
                handoff_ref_id="dwh_unsafe",
                external_execution_claimed=True,
            )
        ],
    )

    posture = proof_pack_posture_for_wave(wave=wave)

    assert posture["wave_id"] == "dwv_posture"
    assert posture["item_count"] == 2
    assert posture["linked_item_count"] == 2
    assert posture["ready_proof_pack_count"] == 1
    assert posture["degraded_proof_pack_count"] == 1
    assert posture["external_execution_claimed"] is True
    assert (
        posture["external_execution_boundary"]["reason_code"] == "UNSAFE_EXTERNAL_EXECUTION_CLAIM"
    )
    assert (
        posture["client_communication_boundary"]["reason_code"]
        == "WAVE_CLIENT_COMMUNICATION_NOT_SUPPORTED"
    )
    assert [ref["wave_item_id"] for ref in posture["proof_pack_refs"]] == [
        "dwi_ready",
        "dwi_degraded",
    ]


def test_proof_pack_posture_omits_unlinked_items_without_state() -> None:
    wave = DpmRebalanceWave.model_construct(
        wave_id="dwv_posture",
        state="PREVIEWED",
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_unlinked",
                portfolio_id="PB_SG_UNLINKED",
                state="CANDIDATE",
            ),
            DpmRebalanceWaveItem(
                wave_item_id="dwi_state_only",
                portfolio_id="PB_SG_STATE_ONLY",
                state="PROOF_PACK_READY",
                diagnostics={"proof_pack_state": "READY"},
            ),
        ],
        handoff_refs=[],
    )

    posture = proof_pack_posture_for_wave(wave=wave)

    assert posture["item_count"] == 2
    assert posture["linked_item_count"] == 0
    assert posture["ready_proof_pack_count"] == 0
    assert posture["degraded_proof_pack_count"] == 0
    assert posture["external_execution_claimed"] is False
    assert posture["external_execution_boundary"]["reason_code"] == "NO_EXTERNAL_EXECUTION_OWNER"
    assert posture["proof_pack_refs"] == [
        {
            "wave_item_id": "dwi_state_only",
            "proof_pack_id": None,
            "item_state": "PROOF_PACK_READY",
            "proof_pack_state": "READY",
            "selected_alternative_id": None,
        }
    ]


def test_proof_pack_posture_helpers_project_refs_counts_and_execution_claims() -> None:
    wave = DpmRebalanceWave.model_construct(
        wave_id="dwv_posture",
        state="HANDOFF_READY",
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_ready",
                portfolio_id="PB_SG_READY",
                state="HANDOFF_READY",
                proof_pack_id="dpp_ready",
                diagnostics={"proof_pack_state": "READY"},
                selected_alternative_id="alt_ready",
            ),
            DpmRebalanceWaveItem(
                wave_item_id="dwi_degraded",
                portfolio_id="PB_SG_DEGRADED",
                state="PROOF_PACK_READY",
                proof_pack_id="dpp_degraded",
                diagnostics={"proof_pack_state": "DEGRADED"},
            ),
            DpmRebalanceWaveItem(
                wave_item_id="dwi_state_only",
                portfolio_id="PB_SG_STATE_ONLY",
                state="PROOF_PACK_READY",
                diagnostics={"proof_pack_state": "READY"},
            ),
            DpmRebalanceWaveItem(
                wave_item_id="dwi_unlinked",
                portfolio_id="PB_SG_UNLINKED",
                state="CANDIDATE",
            ),
        ],
        handoff_refs=[
            DpmWaveHandoffRef.model_construct(
                handoff_ref_id="dwh_safe",
                external_execution_claimed=False,
            ),
            DpmWaveHandoffRef.model_construct(
                handoff_ref_id="dwh_unsafe",
                external_execution_claimed=True,
            ),
        ],
    )

    refs = _proof_pack_refs(wave)

    assert [ref["wave_item_id"] for ref in refs] == [
        "dwi_ready",
        "dwi_degraded",
        "dwi_state_only",
    ]
    assert _ready_proof_pack_count(wave) == 1
    assert _degraded_proof_pack_count(wave) == 1
    assert _external_execution_claimed(wave) is True


def test_wave_proof_pack_posture_exports_only_posture_builder() -> None:
    from src.api.services import wave_proof_pack_posture

    assert wave_proof_pack_posture.__all__ == ["proof_pack_posture_for_wave"]
