from types import SimpleNamespace

from pytest import MonkeyPatch

from src.api.services import proof_pack_report_inputs
from src.api.services.proof_pack_report_inputs import (
    build_proof_pack_ai_evidence_input,
    build_proof_pack_report_input,
    portfolio_memory_context_for_report,
)
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


def test_portfolio_memory_context_for_report_returns_none_without_required_repositories() -> None:
    assert (
        portfolio_memory_context_for_report(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            proof_pack_repository=object(),  # type: ignore[arg-type]
            wave_repository=None,
            outcome_review_repository=object(),  # type: ignore[arg-type]
            mandate_repository=None,
        )
        is None
    )
    assert (
        portfolio_memory_context_for_report(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            proof_pack_repository=object(),  # type: ignore[arg-type]
            wave_repository=object(),  # type: ignore[arg-type]
            outcome_review_repository=None,
            mandate_repository=None,
        )
        is None
    )


def test_portfolio_memory_context_for_report_uses_proof_pack_portfolio_id(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    context = SimpleNamespace(portfolio_id="PB_SG_GLOBAL_BAL_001")

    def _build(**kwargs: object) -> object:
        captured.update(kwargs)
        return context

    monkeypatch.setattr(
        proof_pack_report_inputs,
        "build_report_portfolio_memory_context",
        _build,
    )

    result = portfolio_memory_context_for_report(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        proof_pack_repository=object(),  # type: ignore[arg-type]
        wave_repository=object(),  # type: ignore[arg-type]
        outcome_review_repository=object(),  # type: ignore[arg-type]
        mandate_repository=object(),  # type: ignore[arg-type]
    )

    assert result is context
    assert captured["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"


def test_build_proof_pack_report_input_passes_portfolio_memory_context(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    report_input = SimpleNamespace(input_type="report")
    memory_context = SimpleNamespace(portfolio_id="PB_SG_GLOBAL_BAL_001")
    proof_pack = _proof_pack()

    monkeypatch.setattr(
        proof_pack_report_inputs,
        "portfolio_memory_context_for_report",
        lambda **_kwargs: memory_context,
    )

    def _build(proof_pack_arg: object, *, portfolio_memory_context: object) -> object:
        captured["proof_pack"] = proof_pack_arg
        captured["portfolio_memory_context"] = portfolio_memory_context
        return report_input

    monkeypatch.setattr(proof_pack_report_inputs, "build_report_input", _build)

    result = build_proof_pack_report_input(
        proof_pack=proof_pack,
        proof_pack_repository=object(),  # type: ignore[arg-type]
        wave_repository=object(),  # type: ignore[arg-type]
        outcome_review_repository=object(),  # type: ignore[arg-type]
        mandate_repository=None,
    )

    assert result is report_input
    assert captured == {"proof_pack": proof_pack, "portfolio_memory_context": memory_context}


def test_build_proof_pack_ai_evidence_input_passes_portfolio_memory_context(
    monkeypatch: MonkeyPatch,
) -> None:
    ai_input = SimpleNamespace(input_type="ai")
    memory_context = SimpleNamespace(portfolio_id="PB_SG_GLOBAL_BAL_001")
    proof_pack = _proof_pack()

    monkeypatch.setattr(
        proof_pack_report_inputs,
        "portfolio_memory_context_for_report",
        lambda **_kwargs: memory_context,
    )
    monkeypatch.setattr(
        proof_pack_report_inputs,
        "build_ai_evidence_input",
        lambda proof_pack_arg, *, portfolio_memory_context: (
            proof_pack_arg,
            portfolio_memory_context,
            ai_input,
        ),
    )

    result = build_proof_pack_ai_evidence_input(
        proof_pack=proof_pack,
        proof_pack_repository=object(),  # type: ignore[arg-type]
        wave_repository=object(),  # type: ignore[arg-type]
        outcome_review_repository=object(),  # type: ignore[arg-type]
        mandate_repository=None,
    )

    assert result == (proof_pack, memory_context, ai_input)


def test_proof_pack_report_inputs_exports_report_input_surface() -> None:
    assert proof_pack_report_inputs.__all__ == [
        "build_proof_pack_ai_evidence_input",
        "build_proof_pack_report_input",
        "portfolio_memory_context_for_report",
    ]
