from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.api.request_models import RebalanceExecutionRequestEnvelope, RebalanceRequest
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod
from src.core.dpm_source_context import DpmStatefulInput


CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE = {
    "alternative_set_id": "cas_001",
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    "as_of": "2026-05-03",
    "status": "PENDING_REVIEW",
    "generated_at": "2026-05-03T08:30:00Z",
    "request_hash": "sha256:example",
    "input_mode": "stateful",
    "source_supportability_state": "READY",
    "alternatives": [
        {
            "alternative_id": "alt_do_nothing_baseline",
            "method": "DO_NOTHING_BASELINE",
            "method_status": "READY",
            "summary": "No-action baseline keeps current holdings unchanged for comparison.",
            "rebalance_run_id": "rr_001",
            "objective_trace": [],
            "constraint_trace": [],
            "comparison_metrics": {
                "drift_before": "0.2500",
                "drift_after": "0.2500",
                "drift_reduction": "0.0000",
                "turnover_weight": "0.0000",
                "trade_count": 0,
                "estimated_transaction_cost": None,
                "cash_weight_after": "0.0500",
            },
            "intent_ids": [],
            "diagnostics": {"warnings": [], "data_quality": {}, "rule_result_count": 0},
        }
    ],
}


class ConstructionAlternativeSetGenerateRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "input_mode": "stateless",
                "stateless_input": {
                    "portfolio_snapshot": {
                        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                        "base_currency": "SGD",
                        "positions": [],
                        "cash_balances": [{"currency": "SGD", "amount": "10000.00"}],
                    },
                    "market_data_snapshot": {
                        "prices": [{"instrument_id": "EQ_1", "price": "100.00", "currency": "SGD"}],
                        "fx_rates": [],
                    },
                    "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
                    "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                    "options": {},
                },
                "methods": [
                    "DO_NOTHING_BASELINE",
                    "HEURISTIC_EXPLAINABLE",
                    "MIN_TURNOVER",
                    "COST_AWARE",
                    "TAX_AWARE",
                ],
            }
        }
    }

    input_mode: Literal["stateless", "stateful"] = Field(
        default="stateless",
        description=(
            "Execution input mode. Use `stateless` for complete inline bundles and `stateful` "
            "for governed lotus-core source-data resolution."
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
    options_override: dict[str, object] = Field(
        default_factory=dict,
        description="Optional engine option overrides applied after stateful source-data resolution.",
    )
    methods: list[ConstructionMethod] | None = Field(
        default=None,
        description=(
            "Optional RFC-0039 construction methods to generate. Omit for the default first-wave "
            "set, or include second-wave methods when the caller needs solver, cost, risk, ESG, "
            "currency, liquidity, or regime-aware alternatives with explicit supportability."
        ),
        examples=[
            [
                "DO_NOTHING_BASELINE",
                "HEURISTIC_EXPLAINABLE",
                "MIN_TURNOVER",
                "COST_AWARE",
                "TAX_AWARE",
            ]
        ],
    )
    authority_context: ConstructionAuthorityContext | None = Field(
        default=None,
        description=(
            "Optional source-backed authority context for advanced RFC-0039 methods. "
            "`RISK_AWARE` may also resolve lotus-risk concentration authority when "
            "`DPM_RISK_BASE_URL` is configured. `COST_AWARE` consumes source-owned "
            "`TransactionCostCurve:v1` observed cost evidence for comparison only. "
            "`LIQUIDITY_AWARE`, `CURRENCY_OVERLAY`, and `REGIME_STRESS_AWARE` require "
            "source-backed policy/scenario context to be certified READY; otherwise they "
            "degrade or block with explicit reason codes."
        ),
    )

    def to_execution_envelope(self) -> RebalanceExecutionRequestEnvelope:
        return RebalanceExecutionRequestEnvelope(
            input_mode=self.input_mode,
            stateless_input=self.stateless_input,
            stateful_input=self.stateful_input,
            options_override=self.options_override,
        )


class ConstructionAlternativeSelectionRequest(BaseModel):
    alternative_id: str = Field(
        description="Alternative identifier selected by the portfolio manager or workflow actor.",
        examples=["alt_min_turnover"],
    )
    actor_id: str = Field(
        description="Human or service actor recording the selection decision.",
        examples=["pm_001"],
    )
    reason_code: str = Field(
        description="Bounded business reason for selecting the alternative.",
        examples=["LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT"],
    )
    comment: Optional[str] = Field(
        default=None,
        description="Optional selection note for audit and review.",
        examples=["Chosen for lower turnover before month-end execution window."],
    )
