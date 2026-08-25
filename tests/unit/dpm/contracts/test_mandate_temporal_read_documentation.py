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
