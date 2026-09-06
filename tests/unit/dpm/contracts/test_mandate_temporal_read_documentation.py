from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def _normalized(path: str) -> str:
    content = (ROOT / path).read_text(encoding="utf-8")
    return " ".join(content.lower().split())


def test_temporal_mandate_documentation_preserves_source_dates_and_fail_closed_posture() -> None:
    documents = (
        _normalized("docs/architecture/dpm-command-center-gateway-workbench-handoff.md"),
        _normalized("wiki/Endpoint-Certification.md"),
        _normalized("wiki/Current-State.md"),
        _normalized("REPOSITORY-ENGINEERING-CONTEXT.md"),
    )

    for content in documents:
        assert "as_of_date" in content
        assert "historical" in content

    handoff, endpoint, _, context = documents
    assert "never relabels the resolved source date" in handoff
    assert "returns `404` before the first qualifying snapshot" in endpoint
    assert "without allowing gateway or workbench to reconstruct or relabel" in context


def test_published_diff_semantics_match_the_implemented_selection_and_refusal() -> None:
    """The published contract must state what the diff actually compares.

    The diff selects the most recent observation of each of the latest two
    DISTINCT versions, and refuses a single-distinct-version history rather
    than diffing it against itself. An operator reading "the latest two
    versions" would expect a re-observed binding to produce an empty diff and
    a one-version history to produce a 200, and would be wrong on both.
    """

    endpoint = _normalized("wiki/Endpoint-Certification.md")

    assert "latest two distinct versions" in endpoint
    assert "most recent observation of each version" in endpoint
    # The refusal is the behaviour an integrator must handle, so it is named
    # with its status code rather than described in prose alone.
    assert "only one distinct version" in endpoint
    assert "refused with `409`" in endpoint
    # Business dates travel with the comparison; version numbers are not dates.
    assert "from_as_of_date" in endpoint
    assert "to_as_of_date" in endpoint


def test_supported_features_discloses_the_unconditional_mandate_limit_gaps() -> None:
    """Operators must be told the two limits are unassessable, not discover it.

    No source product states a mandate cash band or turnover budget, and Manage
    no longer derives them, so CASH_LIQUIDITY and TAX_TURNOVER reach pending
    review for every Core-compiled twin. The supported-feature contract is the
    operator-facing surface for that, and it previously described the health
    engine as though both dimensions were assessable.
    """

    supported = _normalized("wiki/Supported-Features.md")

    assert "mandate_cash_band_not_yet_sourced" in supported
    assert "mandate_turnover_budget_not_yet_sourced" in supported
    # The consequence, not only the code: pending review with a source-data
    # action, rather than a ready result.
    assert "`fix_source_data` action rather than a ready result" in supported
    # And that the reserve is not quietly reused as a band boundary.
    assert "never reinterpreted as a band boundary" in supported
