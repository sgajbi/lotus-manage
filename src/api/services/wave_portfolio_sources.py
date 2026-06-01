from src.core.waves import DpmWaveSourceRef


def trigger_source_refs(portfolios: list[dict[str, object]]) -> list[DpmWaveSourceRef]:
    refs: list[DpmWaveSourceRef] = []
    for portfolio in portfolios:
        refs.extend(source_refs_from_portfolio(portfolio))
    return refs


def source_refs_from_portfolio(portfolio: dict[str, object]) -> list[DpmWaveSourceRef]:
    source_refs = portfolio.get("source_refs", [])
    if not isinstance(source_refs, list):
        return []
    return [
        DpmWaveSourceRef.model_validate(source_ref)
        for source_ref in source_refs
        if isinstance(source_ref, dict)
    ]


def diagnostics_from_portfolio(portfolio: dict[str, object]) -> dict[str, object]:
    diagnostics = portfolio.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        return {}
    return {str(key): value for key, value in diagnostics.items() if isinstance(key, str)}


def optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "diagnostics_from_portfolio",
    "optional_str",
    "source_refs_from_portfolio",
    "trigger_source_refs",
]
