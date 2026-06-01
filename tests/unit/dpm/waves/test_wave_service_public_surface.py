from src.api.services import wave_service


def test_wave_service_does_not_reexport_owned_helper_functions() -> None:
    retired_helper_aliases = [
        "approve_persisted_wave",
        "build_preview_wave",
        "cancel_persisted_wave",
        "create_persisted_wave",
        "handoff_persisted_wave",
        "search_wave_summaries",
        "select_persisted_wave_item_alternative",
        "simulate_persisted_wave",
        "source_check_persisted_wave",
        "stage_persisted_wave",
        "wave_detail_for_id",
        "wave_items_for_id",
        "wave_proof_pack_posture_for_id",
        "wave_report_input_for_id",
        "wave_supportability_for_id",
    ]

    assert [
        helper_alias
        for helper_alias in retired_helper_aliases
        if hasattr(wave_service, helper_alias)
    ] == []
