from typing import List

from pydantic import BaseModel, Field
from pydantic.config import JsonDict

from src.core.models import (
    BatchRebalanceRequest,
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)

REBALANCE_REQUEST_EXAMPLE: JsonDict = {
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

BATCH_REBALANCE_REQUEST_EXAMPLE: JsonDict = {
    "portfolio_snapshot": {
        "portfolio_id": "pf_batch",
        "base_currency": "USD",
        "positions": [],
        "cash_balances": [{"currency": "USD", "amount": "10000"}],
    },
    "market_data_snapshot": {
        "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
        "fx_rates": [],
    },
    "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
    "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
    "scenarios": {
        "baseline": {"options": {}},
        "solver_case": {"options": {"target_method": "SOLVER"}},
    },
}


class RebalanceRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": REBALANCE_REQUEST_EXAMPLE}}

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


class StatelessRebalanceRequestEnvelope(BaseModel):
    model_config = {
        "json_schema_extra": {"example": {"stateless_input": REBALANCE_REQUEST_EXAMPLE}}
    }

    stateless_input: RebalanceRequest = Field(
        description=(
            "Complete inline discretionary mandate rebalance input. Use this stateless mode when "
            "the caller supplies governed portfolio, market-data, model, shelf, and option inputs "
            "directly in the request body."
        )
    )


class StatelessBatchRebalanceRequestEnvelope(BaseModel):
    model_config = {
        "json_schema_extra": {"example": {"stateless_input": BATCH_REBALANCE_REQUEST_EXAMPLE}}
    }

    stateless_input: BatchRebalanceRequest = Field(
        description=(
            "Complete inline multi-scenario discretionary mandate analysis input. Use this "
            "stateless mode when the caller supplies shared governed snapshots and scenario "
            "overrides directly in the request body."
        )
    )
