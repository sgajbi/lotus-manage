"""Deterministic Markdown rendering for RFC-0040 proof packs."""

from src.core.proof_packs.models import DpmPreTradeProofPack, DpmProofPackSection


def render_proof_pack_markdown(proof_pack: DpmPreTradeProofPack) -> str:
    """Render a human-readable proof-pack summary without changing evidence truth."""

    lines = [
        f"# Pre-Trade Proof Pack {proof_pack.proof_pack_id}",
        "",
        "## Decision Summary",
        "",
        f"- Portfolio: `{proof_pack.portfolio_id}`",
        f"- Mandate: `{proof_pack.mandate_id or 'MISSING'}`",
        f"- Source type: `{proof_pack.source_type}`",
        f"- Status: `{proof_pack.status}`",
        f"- Correlation id: `{proof_pack.correlation_id}`",
        f"- Created at: `{proof_pack.created_at.isoformat()}`",
        f"- Created by: `{proof_pack.created_by}`",
        f"- Recommended action: `{proof_pack.decision_summary.recommended_action}`",
        f"- Rationale: {proof_pack.decision_summary.business_rationale}",
        "",
        "## Supportability",
        "",
        "| State | Count |",
        "| --- | ---: |",
    ]
    for state, count in sorted(proof_pack.supportability.section_state_counts.items()):
        lines.append(f"| `{state}` | {count} |")

    lines.extend(
        [
            "",
            "## Section Matrix",
            "",
            "| Section | State | Summary | Reason codes |",
            "| --- | --- | --- | --- |",
        ]
    )
    for section in proof_pack.sections:
        lines.append(_section_row(section))

    lines.extend(
        [
            "",
            "## Timeline",
            "",
            "| Time | Event | Actor | Status | Reason codes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for event in proof_pack.decision_timeline.events:
        lines.append(
            "| "
            f"`{event.event_time}` | `{event.event_type}` | `{event.actor}` | "
            f"`{event.status}` | {_codes(event.reason_codes)} |"
        )

    if proof_pack.supportability.reason_codes:
        lines.extend(["", "## Evidence Gaps", ""])
        for code in proof_pack.supportability.reason_codes:
            lines.append(f"- `{code}`")

    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- Content hash: `{proof_pack.content_hash}`",
            "- Source hashes:",
        ]
    )
    for key, value in sorted(proof_pack.source_hashes.items()):
        lines.append(f"  - `{key}`: `{value}`")

    return "\n".join(lines).rstrip() + "\n"


def _section_row(section: DpmProofPackSection) -> str:
    return (
        f"| `{section.section_type}` | `{section.state}` | "
        f"{_escape_table(section.summary)} | {_codes(section.reason_codes)} |"
    )


def _codes(reason_codes: list[str]) -> str:
    if not reason_codes:
        return "`NONE`"
    return ", ".join(f"`{code}`" for code in sorted(reason_codes))


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")
