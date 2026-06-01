from pytest import MonkeyPatch

from src.api.services import proof_pack_generation
from src.api.services.proof_pack_generation import (
    build_run_proof_pack,
    build_selected_alternative_proof_pack,
)
from src.api.services.proof_pack_mandate_evidence import ProofPackMandateEvidence
from src.api.services.proof_pack_selected_source import ProofPackSelectedAlternativeSource
from src.core.construction import build_alternative_set, build_rebalance_result_alternative
from tests.unit.dpm.proof_packs.test_proof_pack_builder import (
    _ready_rebalance_result,
    _run_record,
)
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


def test_build_run_proof_pack_passes_resolved_mandate_and_workflow_inputs(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    proof_pack = _proof_pack()
    run = _run_record()
    workflow_decisions: list[object] = []
    mandate_evidence = ProofPackMandateEvidence(
        twin=object(),  # type: ignore[arg-type]
        health=object(),  # type: ignore[arg-type]
        gap_codes=["MANDATE_GAP"],
    )

    def _build(**kwargs: object) -> object:
        captured.update(kwargs)
        return proof_pack

    monkeypatch.setattr(proof_pack_generation, "build_proof_pack_from_run", _build)

    result = build_run_proof_pack(
        run=run,
        workflow_decisions=workflow_decisions,  # type: ignore[arg-type]
        actor_id="pm_generation",
        reason="Generate proof pack.",
        correlation_id="corr_generation",
        mandate_id="mandate_generation",
        mandate_evidence=mandate_evidence,
        direct_regime_stress_context=None,
    )

    assert result is proof_pack
    assert captured["run"] is run
    assert captured["workflow_decisions"] is workflow_decisions
    assert captured["created_by"] == "pm_generation"
    assert captured["mandate_twin"] is mandate_evidence.twin
    assert captured["mandate_health"] is mandate_evidence.health
    assert captured["mandate_evidence_gap_codes"] == ["MANDATE_GAP"]


def test_build_selected_alternative_proof_pack_passes_resolved_source_inputs(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_generation_001",
        portfolio_id="pf_generation_001",
        as_of="2026-06-01",
        alternatives=[alternative],
    )
    selected_source = ProofPackSelectedAlternativeSource(
        alternative_set=alternative_set,
        selection=None,
        run=_run_record(),
        workflow_decisions=[],
    )
    proof_pack = _proof_pack()
    mandate_evidence = ProofPackMandateEvidence(twin=None, health=None, gap_codes=[])

    def _build(**kwargs: object) -> object:
        captured.update(kwargs)
        return proof_pack

    monkeypatch.setattr(
        proof_pack_generation,
        "build_proof_pack_from_selected_alternative",
        _build,
    )

    result_pack = build_selected_alternative_proof_pack(
        selected_source=selected_source,
        selected_alternative_id=alternative.alternative_id,
        actor_id="pm_generation",
        reason=None,
        correlation_id="corr_generation",
        mandate_id=None,
        mandate_evidence=mandate_evidence,
        direct_regime_stress_context=None,
    )

    assert result_pack is proof_pack
    assert captured["alternative_set"] is alternative_set
    assert captured["selected_alternative_id"] == alternative.alternative_id
    assert captured["run"] is selected_source.run
    assert captured["selection"] is None
    assert captured["created_by"] == "pm_generation"
    assert captured["workflow_decisions"] == []


def test_proof_pack_generation_exports_builder_surface() -> None:
    assert proof_pack_generation.__all__ == [
        "build_run_proof_pack",
        "build_selected_alternative_proof_pack",
    ]
