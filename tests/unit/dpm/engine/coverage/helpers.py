from src.core.models import DiagnosticsData
from tests.shared.factories import cash, portfolio_snapshot


def usd_cash_portfolio(portfolio_id: str, amount: str = "1000"):
    return portfolio_snapshot(
        portfolio_id=portfolio_id,
        base_currency="USD",
        cash_balances=[cash("USD", amount)],
    )


def empty_diagnostics() -> DiagnosticsData:
    return DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
