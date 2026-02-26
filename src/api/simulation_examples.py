SIMULATE_READY_EXAMPLE = {
    "summary": "Ready run",
    "value": {
        "status": "READY",
        "rebalance_run_id": "rr_demo1234",
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
    },
}
SIMULATE_PENDING_EXAMPLE = {
    "summary": "Pending review run",
    "value": {
        "status": "PENDING_REVIEW",
        "rebalance_run_id": "rr_demo5678",
        "diagnostics": {"warnings": ["CAPPED_BY_GROUP_LIMIT_sector:TECH"]},
    },
}
SIMULATE_BLOCKED_EXAMPLE = {
    "summary": "Blocked run",
    "value": {
        "status": "BLOCKED",
        "rebalance_run_id": "rr_demo9999",
        "diagnostics": {"warnings": ["OVERDRAFT_ON_T_PLUS_1"]},
    },
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
        "results": {},
        "comparison_metrics": {},
        "failed_scenarios": {},
        "warnings": [],
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
        "status_url": "/rebalance/operations/dop_abc12345",
    },
}

PROPOSAL_READY_EXAMPLE = {
    "summary": "Proposal simulation ready",
    "value": {
        "status": "READY",
        "proposal_run_id": "pr_demo1234",
        "correlation_id": "corr_demo1234",
        "intents": [
            {"intent_type": "CASH_FLOW", "currency": "USD", "amount": "2000.00"},
            {
                "intent_type": "SECURITY_TRADE",
                "side": "BUY",
                "instrument_id": "EQ_GROWTH",
                "quantity": "40",
            },
        ],
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
    },
}

PROPOSAL_PENDING_EXAMPLE = {
    "summary": "Proposal simulation pending review",
    "value": {
        "status": "PENDING_REVIEW",
        "proposal_run_id": "pr_demo5678",
        "correlation_id": "corr_demo5678",
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
        "rule_results": [{"rule_id": "CASH_BAND", "severity": "SOFT", "status": "FAIL"}],
    },
}

PROPOSAL_BLOCKED_EXAMPLE = {
    "summary": "Proposal simulation blocked",
    "value": {
        "status": "BLOCKED",
        "proposal_run_id": "pr_demo9999",
        "correlation_id": "corr_demo9999",
        "diagnostics": {
            "warnings": ["PROPOSAL_WITHDRAWAL_NEGATIVE_CASH"],
            "data_quality": {"price_missing": [], "fx_missing": []},
        },
    },
}

PROPOSAL_409_EXAMPLE = {
    "summary": "Idempotency hash conflict",
    "value": {"detail": "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"},
}
