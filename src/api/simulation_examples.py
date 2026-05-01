from typing import Any


def _state_example(*, cash_amount: str) -> dict[str, Any]:
    return {
        "total_value": {"amount": "11000.00", "currency": "USD"},
        "cash_balances": [{"currency": "USD", "amount": cash_amount}],
        "positions": [
            {
                "instrument_id": "EQ_1",
                "quantity": "100",
                "instrument_currency": "USD",
                "asset_class": "EQUITY",
                "price": {"amount": "100.00", "currency": "USD"},
                "value_in_instrument_ccy": {"amount": "10000.00", "currency": "USD"},
                "value_in_base_ccy": {"amount": "10000.00", "currency": "USD"},
                "weight": "0.9091",
            }
        ],
        "allocation_by_asset_class": [
            {
                "key": "EQUITY",
                "weight": "0.9091",
                "value": {"amount": "10000.00", "currency": "USD"},
            }
        ],
        "allocation_by_instrument": [
            {"key": "EQ_1", "weight": "0.9091", "value": {"amount": "10000.00", "currency": "USD"}}
        ],
        "allocation": [
            {"key": "EQ_1", "weight": "0.9091", "value": {"amount": "10000.00", "currency": "USD"}}
        ],
        "allocation_by_attribute": {
            "sector": [
                {
                    "key": "TECH",
                    "weight": "0.9091",
                    "value": {"amount": "10000.00", "currency": "USD"},
                }
            ]
        },
    }


def _diagnostics_example(
    *,
    warnings: list[str],
    cash_ladder_breaches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "warnings": warnings,
        "suppressed_intents": [],
        "dropped_intents": [],
        "group_constraint_events": [],
        "tax_budget_constraint_events": [],
        "cash_ladder": [],
        "cash_ladder_breaches": cash_ladder_breaches or [],
        "missing_fx_pairs": [],
        "funding_plan": [],
        "insufficient_cash": [],
        "data_quality": {"price_missing": [], "fx_missing": []},
    }


def _gate_decision_example(
    *,
    gate: str,
    recommended_next_step: str,
    hard_fail_count: int,
    soft_fail_count: int,
    new_high_suitability_count: int = 0,
    new_medium_suitability_count: int = 0,
) -> dict[str, Any]:
    return {
        "gate": gate,
        "recommended_next_step": recommended_next_step,
        "reasons": [],
        "summary": {
            "hard_fail_count": hard_fail_count,
            "soft_fail_count": soft_fail_count,
            "new_high_suitability_count": new_high_suitability_count,
            "new_medium_suitability_count": new_medium_suitability_count,
        },
    }


def _simulate_result_example(
    *,
    correlation_id: str,
    status: str,
    rebalance_run_id: str,
    warnings: list[str],
    gate_decision: dict[str, Any],
    request_hash: str,
    idempotency_key: str | None = "demo-idem-001",
    rule_results: list[dict[str, Any]] | None = None,
    cash_ladder_breaches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "correlation_id": correlation_id,
        "status": status,
        "rebalance_run_id": rebalance_run_id,
        "before": _state_example(cash_amount="1000.00"),
        "universe": {
            "universe_id": f"uni_{rebalance_run_id}",
            "eligible_for_buy": ["EQ_1"],
            "eligible_for_sell": ["EQ_1"],
            "excluded": [],
            "coverage": {"price_coverage_pct": "1.0", "fx_coverage_pct": "1.0"},
        },
        "target": {
            "target_id": f"target_{rebalance_run_id}",
            "strategy": {"target_method": "HEURISTIC"},
            "targets": [
                {
                    "instrument_id": "EQ_1",
                    "model_weight": "0.60",
                    "final_weight": "0.60",
                    "final_value": {"amount": "6600.00", "currency": "USD"},
                    "tags": [],
                }
            ],
        },
        "intents": [],
        "after_simulated": _state_example(cash_amount="1000.00"),
        "reconciliation": {
            "before_total_value": {"amount": "11000.00", "currency": "USD"},
            "after_total_value": {"amount": "11000.00", "currency": "USD"},
            "delta": {"amount": "0.00", "currency": "USD"},
            "tolerance": {"amount": "0.01", "currency": "USD"},
            "status": "OK",
        },
        "tax_impact": None,
        "rule_results": rule_results or [],
        "explanation": {},
        "diagnostics": _diagnostics_example(
            warnings=warnings,
            cash_ladder_breaches=cash_ladder_breaches,
        ),
        "gate_decision": gate_decision,
        "lineage": {
            "portfolio_snapshot_id": "pf_demo",
            "market_data_snapshot_id": "md_demo",
            "request_hash": request_hash,
            **({"idempotency_key": idempotency_key} if idempotency_key is not None else {}),
        },
    }


def _analyze_baseline_result_example() -> dict[str, Any]:
    result = _simulate_result_example(
        correlation_id="corr-batch-sync-1:baseline",
        status="READY",
        rebalance_run_id="rr_batch_baseline_001",
        warnings=[],
        gate_decision=_gate_decision_example(
            gate="EXECUTION_READY",
            recommended_next_step="EXECUTE",
            hard_fail_count=0,
            soft_fail_count=0,
        ),
        request_hash="sha256:batch-baseline",
        idempotency_key=None,
    )
    result["universe"]["universe_id"] = "uni_batch_baseline_001"
    result["target"]["target_id"] = "target_batch_baseline_001"
    result["intents"] = [
        {
            "intent_type": "SECURITY_TRADE",
            "intent_id": "oi_batch_001",
            "instrument_id": "EQ_1",
            "side": "SELL",
            "quantity": "45",
            "notional": {"amount": "4500.00", "currency": "USD"},
            "notional_base": {"amount": "4500.00", "currency": "USD"},
            "dependencies": [],
            "rationale": {
                "code": "ALIGN_TO_TARGET",
                "message": "Sell down to model target weight.",
            },
            "constraints_applied": [],
        }
    ]
    result["after_simulated"] = _state_example(cash_amount="5500.00")
    result["lineage"] = {
        "portfolio_snapshot_id": "pf_batch",
        "market_data_snapshot_id": "md",
        "request_hash": "sha256:batch-baseline",
    }
    return result


SIMULATE_READY_EXAMPLE = {
    "summary": "Ready run",
    "value": _simulate_result_example(
        correlation_id="corr-1234-abcd",
        status="READY",
        rebalance_run_id="rr_demo1234",
        warnings=[],
        gate_decision=_gate_decision_example(
            gate="EXECUTION_READY",
            recommended_next_step="EXECUTE",
            hard_fail_count=0,
            soft_fail_count=0,
        ),
        request_hash="sha256:demo-ready",
    ),
}
SIMULATE_PENDING_EXAMPLE = {
    "summary": "Pending review run",
    "value": _simulate_result_example(
        correlation_id="corr-5678-pending",
        status="PENDING_REVIEW",
        rebalance_run_id="rr_demo5678",
        warnings=["CAPPED_BY_GROUP_LIMIT_sector:TECH"],
        gate_decision=_gate_decision_example(
            gate="RISK_REVIEW_REQUIRED",
            recommended_next_step="RISK_REVIEW",
            hard_fail_count=0,
            soft_fail_count=1,
            new_medium_suitability_count=1,
        ),
        request_hash="sha256:demo-pending",
        rule_results=[
            {
                "rule_id": "GROUP_LIMIT",
                "severity": "SOFT",
                "status": "FAIL",
                "measured": "0.35",
                "threshold": {"max_weight": "0.30"},
                "reason_code": "GROUP_LIMIT_SOFT_FAIL",
                "remediation_hint": "Reduce exposure or request risk review.",
            }
        ],
    ),
}
SIMULATE_BLOCKED_EXAMPLE = {
    "summary": "Blocked run",
    "value": _simulate_result_example(
        correlation_id="corr-9999-blocked",
        status="BLOCKED",
        rebalance_run_id="rr_demo9999",
        warnings=["OVERDRAFT_ON_T_PLUS_1"],
        gate_decision=_gate_decision_example(
            gate="BLOCKED",
            recommended_next_step="FIX_INPUT",
            hard_fail_count=1,
            soft_fail_count=0,
        ),
        request_hash="sha256:demo-blocked",
        cash_ladder_breaches=[
            {
                "date_offset": 1,
                "currency": "USD",
                "projected_balance": "-1500.00",
                "allowed_floor": "0.00",
                "reason_code": "OVERDRAFT_ON_T_PLUS_1",
            }
        ],
    ),
}
SIMULATE_409_EXAMPLE = {
    "summary": "Idempotency hash conflict",
    "value": {"detail": "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"},
}

BATCH_EXAMPLE = {
    "summary": "Batch what-if request",
    "value": {
        "portfolio_snapshot": {
            "portfolio_id": "pf_batch",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.5"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "scenarios": {
            "baseline": {"options": {}},
            "solver_case": {"options": {"target_method": "SOLVER"}},
        },
    },
}

ANALYZE_RESPONSE_EXAMPLE = {
    "summary": "Batch result",
    "value": {
        "batch_run_id": "batch_ab12cd34",
        "run_at_utc": "2026-02-18T10:00:00+00:00",
        "base_snapshot_ids": {"portfolio_snapshot_id": "pf_batch", "market_data_snapshot_id": "md"},
        "results": {"baseline": _analyze_baseline_result_example()},
        "comparison_metrics": {
            "baseline": {
                "status": "READY",
                "security_intent_count": 1,
                "gross_turnover_notional_base": {"amount": "4500.00", "currency": "USD"},
            }
        },
        "failed_scenarios": {
            "invalid_case": "INVALID_OPTIONS: group constraint keys must match <attribute_key>:<attribute_value>"
        },
        "warnings": ["PARTIAL_BATCH_FAILURE"],
    },
}
ANALYZE_ASYNC_ACCEPTED_EXAMPLE = {
    "summary": "Async batch accepted",
    "value": {
        "operation_id": "dop_abc12345",
        "operation_type": "ANALYZE_SCENARIOS",
        "status": "PENDING",
        "correlation_id": "corr-batch-async-1",
        "created_at": "2026-02-20T12:00:00+00:00",
        "status_url": "/api/v1/rebalance/operations/dop_abc12345",
        "execute_url": "/api/v1/rebalance/operations/dop_abc12345/execute",
    },
}
ANALYZE_ASYNC_409_EXAMPLE = {
    "summary": "Correlation conflict",
    "value": {"detail": "DPM_ASYNC_OPERATION_CORRELATION_CONFLICT"},
}
