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
