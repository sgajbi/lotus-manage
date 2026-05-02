from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator
from pydantic.config import JsonDict

from src.core.dpm_source_context import DpmStatefulInput
from src.core.models import (
    BatchRebalanceRequest,
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
    SimulationScenario,
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


class RebalanceExecutionRequestEnvelope(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "input_mode": "stateless",
                "stateless_input": REBALANCE_REQUEST_EXAMPLE,
            }
        }
    }

    input_mode: Literal["stateless", "stateful"] = Field(
        default="stateless",
        description=(
            "Execution input mode. Use `stateless` for complete inline bundles and `stateful` "
            "for governed lotus-core portfolio-context resolution."
        ),
        examples=["stateless"],
    )
    stateless_input: Optional[RebalanceRequest] = Field(
        default=None,
        description="Complete inline execution bundle required when input_mode is `stateless`.",
    )
    stateful_input: Optional[DpmStatefulInput] = Field(
        default=None,
        description="Core source-data selectors required when input_mode is `stateful`.",
    )
    options_override: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional engine option overrides applied after stateful source-data resolution.",
    )

    @model_validator(mode="after")
    def validate_mode_payload(self) -> "RebalanceExecutionRequestEnvelope":
        if self.input_mode == "stateless" and self.stateless_input is None:
            raise ValueError("DPM_STATELESS_INPUT_REQUIRED")
        if self.input_mode == "stateful" and self.stateful_input is None:
            raise ValueError("DPM_STATEFUL_INPUT_REQUIRED")
        return self


class BatchExecutionRequestEnvelope(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "input_mode": "stateless",
                "stateless_input": BATCH_REBALANCE_REQUEST_EXAMPLE,
            }
        }
    }

    input_mode: Literal["stateless", "stateful"] = Field(
        default="stateless",
        description=(
            "Execution input mode. Use `stateless` for complete inline scenario bundles and "
            "`stateful` for shared lotus-core context with scenario option overrides."
        ),
        examples=["stateless"],
    )
    stateless_input: Optional[BatchRebalanceRequest] = Field(
        default=None,
        description="Complete inline batch scenario bundle required when input_mode is `stateless`.",
    )
    stateful_input: Optional[DpmStatefulInput] = Field(
        default=None,
        description="Core source-data selectors required when input_mode is `stateful`.",
    )
    scenarios: dict[str, SimulationScenario] = Field(
        default_factory=dict,
        description="Named scenario map required when input_mode is `stateful`.",
    )

    @model_validator(mode="after")
    def validate_mode_payload(self) -> "BatchExecutionRequestEnvelope":
        if self.input_mode == "stateless" and self.stateless_input is None:
            raise ValueError("DPM_STATELESS_INPUT_REQUIRED")
        if self.input_mode == "stateful":
            if self.stateful_input is None:
                raise ValueError("DPM_STATEFUL_INPUT_REQUIRED")
            if not self.scenarios:
                raise ValueError("DPM_STATEFUL_SCENARIOS_REQUIRED")
        return self
