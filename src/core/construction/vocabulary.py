"""Bounded RFC-0039 vocabulary for construction alternatives.

The construction package is intentionally separate from the existing rebalance engine. Rebalance
modules own deterministic execution mechanics; construction modules own comparable alternatives,
method posture, and source-aware decision evidence.
"""

from enum import StrEnum


class ConstructionMethod(StrEnum):
    """Supported and proposed construction method identifiers."""

    DO_NOTHING_BASELINE = "DO_NOTHING_BASELINE"
    HEURISTIC_EXPLAINABLE = "HEURISTIC_EXPLAINABLE"
    MIN_TURNOVER = "MIN_TURNOVER"
    COST_AWARE = "COST_AWARE"
    TAX_AWARE = "TAX_AWARE"
    LIQUIDITY_AWARE = "LIQUIDITY_AWARE"
    SOLVER_CONSTRAINED = "SOLVER_CONSTRAINED"
    RISK_AWARE = "RISK_AWARE"
    ESG_AWARE = "ESG_AWARE"
    CURRENCY_OVERLAY = "CURRENCY_OVERLAY"
    REGIME_STRESS_AWARE = "REGIME_STRESS_AWARE"


class ConstructionMethodStatus(StrEnum):
    """Bounded method-level supportability posture."""

    READY = "READY"
    PENDING_REVIEW = "PENDING_REVIEW"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"


class ConstructionSourceFamily(StrEnum):
    """Source families that can affect alternative readiness."""

    PORTFOLIO_STATE = "PORTFOLIO_STATE"
    MODEL_TARGETS = "MODEL_TARGETS"
    MANDATE_BINDING = "MANDATE_BINDING"
    INSTRUMENT_ELIGIBILITY = "INSTRUMENT_ELIGIBILITY"
    MARKET_DATA = "MARKET_DATA"
    TAX_LOTS = "TAX_LOTS"
    LIQUIDITY_PROFILE = "LIQUIDITY_PROFILE"
    CASHFLOW_PROJECTION = "CASHFLOW_PROJECTION"
    TRANSACTION_COST = "TRANSACTION_COST"
    RISK_ENRICHMENT = "RISK_ENRICHMENT"
    PERFORMANCE_CONTEXT = "PERFORMANCE_CONTEXT"
    ESG_PROFILE = "ESG_PROFILE"
    CURRENCY_POLICY = "CURRENCY_POLICY"
    REGIME_SCENARIO = "REGIME_SCENARIO"


class ConstructionTraceTerm(StrEnum):
    """Bounded objective and constraint trace term identifiers."""

    DRIFT = "DRIFT"
    TURNOVER = "TURNOVER"
    TAX_IMPACT = "TAX_IMPACT"
    ESTIMATED_COST = "ESTIMATED_COST"
    CASH_BAND = "CASH_BAND"
    ELIGIBILITY = "ELIGIBILITY"
    TAX_BUDGET = "TAX_BUDGET"
    TURNOVER_BUDGET = "TURNOVER_BUDGET"
    SOLVER = "SOLVER"
    SOURCE_SUPPORTABILITY = "SOURCE_SUPPORTABILITY"


FIRST_WAVE_CONSTRUCTION_METHODS: tuple[ConstructionMethod, ...] = (
    ConstructionMethod.DO_NOTHING_BASELINE,
    ConstructionMethod.HEURISTIC_EXPLAINABLE,
    ConstructionMethod.MIN_TURNOVER,
    ConstructionMethod.TAX_AWARE,
)

SOURCE_AWARE_CONSTRUCTION_METHODS: frozenset[ConstructionMethod] = frozenset(
    {
        ConstructionMethod.TAX_AWARE,
        ConstructionMethod.COST_AWARE,
        ConstructionMethod.LIQUIDITY_AWARE,
        ConstructionMethod.RISK_AWARE,
        ConstructionMethod.ESG_AWARE,
        ConstructionMethod.CURRENCY_OVERLAY,
        ConstructionMethod.REGIME_STRESS_AWARE,
    }
)
