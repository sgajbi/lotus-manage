from typing import List

from pydantic import BaseModel, Field

from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)


class RebalanceRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_1",
                    "base_currency": "USD",
                    "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
                    "cash_balances": [{"currency": "USD", "amount": "5000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.6"}]},
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {
                    "target_method": "HEURISTIC",
                    "enable_tax_awareness": False,
                    "enable_settlement_awareness": False,
                },
            }
        }
    }

    portfolio_snapshot: PortfolioSnapshot = Field(
        description="Current portfolio holdings and cash balances."
    )
    market_data_snapshot: MarketDataSnapshot = Field(
        description="Price and FX snapshot used for valuation and intent generation."
    )
    model_portfolio: ModelPortfolio = Field(description="Target model weights by instrument.")
    shelf_entries: List[ShelfEntry] = Field(
        description=(
            "Instrument eligibility and policy metadata (status, attributes, settlement days)."
        )
    )
    options: EngineOptions = Field(description="Request-level engine behavior and feature toggles.")
