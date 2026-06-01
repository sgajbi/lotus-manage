from types import SimpleNamespace

from pytest import MonkeyPatch

from src.api.services import outcome_review_report_inputs, outcome_review_service
from src.api.services.outcome_review_report_inputs import (
    build_outcome_ai_evidence_input,
    build_outcome_report_input,
    portfolio_memory_context_for_report,
)
from tests.unit.infrastructure.test_outcome_review_repository import _review


def test_portfolio_memory_context_for_report_returns_none_without_required_repositories() -> None:
    assert (
        portfolio_memory_context_for_report(
            review=_review(),
            proof_pack_repository=None,
            wave_repository=object(),  # type: ignore[arg-type]
            outcome_review_repository=object(),  # type: ignore[arg-type]
            mandate_repository=None,
        )
        is None
    )
    assert (
        portfolio_memory_context_for_report(
            review=_review(),
            proof_pack_repository=object(),  # type: ignore[arg-type]
            wave_repository=None,
            outcome_review_repository=object(),  # type: ignore[arg-type]
            mandate_repository=None,
        )
        is None
    )


def test_portfolio_memory_context_for_report_uses_review_portfolio_id(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    context = SimpleNamespace(portfolio_id="PB_SG_GLOBAL_BAL_001")

    def _build(**kwargs: object) -> object:
        captured.update(kwargs)
        return context

    monkeypatch.setattr(
        outcome_review_report_inputs,
        "build_report_portfolio_memory_context",
        _build,
    )

    result = portfolio_memory_context_for_report(
        review=_review(),
        proof_pack_repository=object(),  # type: ignore[arg-type]
        wave_repository=object(),  # type: ignore[arg-type]
        outcome_review_repository=object(),  # type: ignore[arg-type]
        mandate_repository=object(),  # type: ignore[arg-type]
    )

    assert result is context
    assert captured["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"


def test_build_outcome_report_input_passes_portfolio_memory_context(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    report_input = SimpleNamespace(input_type="report")
    memory_context = SimpleNamespace(portfolio_id="PB_SG_GLOBAL_BAL_001")

    monkeypatch.setattr(
        outcome_review_report_inputs,
        "portfolio_memory_context_for_report",
        lambda **_kwargs: memory_context,
    )

    def _build(review: object, *, portfolio_memory_context: object) -> object:
        captured["review"] = review
        captured["portfolio_memory_context"] = portfolio_memory_context
        return report_input

    monkeypatch.setattr(outcome_review_report_inputs, "build_report_input", _build)
    review = _review()

    result = build_outcome_report_input(
        review=review,
        proof_pack_repository=object(),  # type: ignore[arg-type]
        wave_repository=object(),  # type: ignore[arg-type]
        outcome_review_repository=object(),  # type: ignore[arg-type]
        mandate_repository=None,
    )

    assert result is report_input
    assert captured == {"review": review, "portfolio_memory_context": memory_context}


def test_build_outcome_ai_evidence_input_passes_portfolio_memory_context(
    monkeypatch: MonkeyPatch,
) -> None:
    ai_input = SimpleNamespace(input_type="ai")
    memory_context = SimpleNamespace(portfolio_id="PB_SG_GLOBAL_BAL_001")

    monkeypatch.setattr(
        outcome_review_report_inputs,
        "portfolio_memory_context_for_report",
        lambda **_kwargs: memory_context,
    )
    monkeypatch.setattr(
        outcome_review_report_inputs,
        "build_ai_evidence_input",
        lambda review, *, portfolio_memory_context: (review, portfolio_memory_context, ai_input),
    )
    review = _review()

    result = build_outcome_ai_evidence_input(
        review=review,
        proof_pack_repository=object(),  # type: ignore[arg-type]
        wave_repository=object(),  # type: ignore[arg-type]
        outcome_review_repository=object(),  # type: ignore[arg-type]
        mandate_repository=None,
    )

    assert result == (review, memory_context, ai_input)


def test_outcome_review_report_inputs_exports_report_input_surface() -> None:
    assert outcome_review_report_inputs.__all__ == [
        "build_outcome_ai_evidence_input",
        "build_outcome_report_input",
        "portfolio_memory_context_for_report",
    ]


def test_service_preserves_portfolio_memory_context_alias() -> None:
    assert outcome_review_service._portfolio_memory_context_for_report is (
        portfolio_memory_context_for_report
    )
