from src.core.outcomes import DpmOutcomeSourceRef
from src.core.portfolio_memory.pm_quality_projection import score_run_includes_portfolio
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID, _pm_quality_score_run


def test_score_run_includes_portfolio_from_member_portfolio_ids() -> None:
    score_run = _pm_quality_score_run()

    assert score_run_includes_portfolio(score_run=score_run, portfolio_id=PORTFOLIO_ID)
    assert not score_run_includes_portfolio(
        score_run=score_run,
        portfolio_id="PB_NOT_IN_PM_BOOK",
    )


def test_score_run_includes_portfolio_from_pm_book_member_source_ref() -> None:
    score_run = _pm_quality_score_run().model_copy(
        update={
            "book_scope_evidence": _pm_quality_score_run().book_scope_evidence.model_copy(
                update={
                    "member_portfolio_ids": [],
                    "source_refs": [
                        DpmOutcomeSourceRef(
                            source_system="lotus-core",
                            source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
                            source_id=f"pm-book:{PORTFOLIO_ID}",
                        )
                    ],
                }
            )
        }
    )

    assert score_run_includes_portfolio(score_run=score_run, portfolio_id=PORTFOLIO_ID)


def test_score_run_without_book_scope_does_not_project_to_portfolio() -> None:
    score_run = _pm_quality_score_run().model_copy(update={"book_scope_evidence": None})

    assert not score_run_includes_portfolio(score_run=score_run, portfolio_id=PORTFOLIO_ID)
