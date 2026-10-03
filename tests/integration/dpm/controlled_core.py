"""Owned HTTP source-contract fixture, not execution of the real Core application."""

from contextlib import contextmanager
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from queue import Queue
import threading


AS_OF = "2026-04-10"
RESERVE_AUTHORITY = {
    "cash_reserve_scope": "TOTAL_PORTFOLIO_MARKET_VALUE",
    "cash_reserve_currency_basis": "PORTFOLIO_BASE_CURRENCY",
    "cash_reserve_authority": "MANDATE_BINDING",
    "consumer_override_allowed": False,
}


def _ready(reason, **counts):
    return {"state": "READY", "reason": reason, **counts}


def controlled_products(portfolio, reserve="0.02", price=100):
    common = {
        "product_version": "v1",
        "as_of_date": AS_OF,
        "lineage": {"source_system": "controlled-core", "contract_version": "rfc_087_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": f"{AS_OF}T09:00:00Z",
    }
    mandate = {
        **common,
        "product_name": "DiscretionaryMandateBinding",
        "portfolio_id": portfolio,
        "mandate_id": "mandate-reserve",
        "client_id": "client-reserve",
        "mandate_type": "discretionary",
        "discretionary_authority_status": "active",
        "booking_center_code": "SG",
        "jurisdiction_code": "SG",
        "model_portfolio_id": "model-reserve",
        "policy_pack_id": "dpm_standard_v1",
        "risk_profile": "balanced",
        "investment_horizon": "long_term",
        "leverage_allowed": False,
        "tax_awareness_allowed": False,
        "settlement_awareness_required": False,
        "rebalance_frequency": "monthly",
        "rebalance_bands": {
            "default_band": "0.025",
            "cash_reserve_weight": reserve,
            **RESERVE_AUTHORITY,
        },
        "effective_from": "2026-04-01",
        "effective_to": "2026-04-30",
        "binding_version": 7,
        "supportability": _ready("MANDATE_BINDING_READY", missing_data_families=[]),
        "lineage": {"source_record_id": "mandate-reserve-v7", "source_system": "controlled-core"},
    }
    return {
        "mandate-binding": mandate,
        "targets": {
            **common,
            "product_name": "DpmModelPortfolioTarget",
            "model_portfolio_id": "model-reserve",
            "model_portfolio_version": "7",
            "display_name": "Controlled reserve model",
            "base_currency": "USD",
            "risk_profile": "balanced",
            "mandate_type": "discretionary",
            "rebalance_frequency": "monthly",
            "approval_status": "approved",
            "effective_from": "2026-04-01",
            "targets": [
                {
                    "instrument_id": "EQ_1",
                    "target_weight": "1",
                    "target_status": "active",
                    "quality_status": "accepted",
                }
            ],
            "supportability": _ready(
                "MODEL_TARGETS_READY", target_count=1, total_target_weight="1"
            ),
        },
        "core-snapshot": {
            "portfolio_id": portfolio,
            "as_of_date": AS_OF,
            "snapshot_id": f"snapshot-{portfolio}",
            "valuation_context": {"portfolio_currency": "USD", "reporting_currency": "USD"},
            "sections": {
                "positions_baseline": [
                    {
                        "security_id": "EQ_1",
                        "quantity": "100",
                        "market_value_local": str(price * 100),
                        "currency": "USD",
                    },
                    {
                        "security_id": "CASH_USD_BOOK_OPERATING",
                        "quantity": str(100000 - price * 100),
                        "market_value_local": str(100000 - price * 100),
                        "currency": "USD",
                    },
                ],
                "portfolio_totals": {"baseline_total_market_value_base": "100000"},
            },
        },
        "eligibility-bulk": {
            **common,
            "product_name": "InstrumentEligibilityProfile",
            "eligibility": [
                {
                    "security_id": "EQ_1",
                    "found": True,
                    "eligibility_status": "APPROVED",
                    "product_shelf_status": "APPROVED",
                    "buy_allowed": True,
                    "sell_allowed": True,
                    "asset_class": "EQUITY",
                    "quality_status": "accepted",
                }
            ],
            "supportability": _ready(
                "INSTRUMENT_ELIGIBILITY_READY", requested_count=1, found_count=1
            ),
        },
        "coverage": {
            **common,
            "product_name": "MarketDataCoverageWindow",
            "valuation_currency": "USD",
            "price_coverage": [
                {
                    "instrument_id": "EQ_1",
                    "found": True,
                    "price_date": AS_OF,
                    "price": str(price),
                    "currency": "USD",
                    "age_days": 0,
                    "quality_status": "READY",
                }
            ],
            "fx_coverage": [],
            "supportability": _ready(
                "MARKET_DATA_READY",
                requested_price_count=1,
                resolved_price_count=1,
                requested_fx_count=0,
                resolved_fx_count=0,
            ),
        },
        "dpm-source-readiness": {
            **common,
            "product_name": "DpmSourceReadiness",
            "portfolio_id": portfolio,
            "mandate_id": "mandate-reserve",
            "model_portfolio_id": "model-reserve",
            "families": [
                {
                    "family": name,
                    "product_name": product,
                    "state": "READY",
                    "reason": "CONTROLLED_SOURCE_READY",
                    "evidence_count": 1,
                }
                for name, product in [
                    ("mandate", "DiscretionaryMandateBinding"),
                    ("model_targets", "DpmModelPortfolioTarget"),
                    ("eligibility", "InstrumentEligibilityProfile"),
                    ("market_data", "MarketDataCoverageWindow"),
                ]
            ],
            "supportability": _ready(
                "DPM_SOURCE_READINESS_READY",
                ready_family_count=4,
                degraded_family_count=0,
                incomplete_family_count=0,
                unavailable_family_count=0,
            ),
        },
        "client-restriction-profile": {
            **common,
            "product_name": "ClientRestrictionProfile",
            "portfolio_id": portfolio,
            "mandate_id": "mandate-reserve",
            "client_id": "client-reserve",
            "restrictions": [],
            "supportability": _ready(
                "CLIENT_RESTRICTION_PROFILE_READY", restriction_count=0, missing_data_families=[]
            ),
        },
    }


@contextmanager
def controlled_core(
    *,
    portfolio,
    reserve="0.02",
    price=100,
    invalid_legacy=False,
    starting_shares=100,
    product_overrides=None,
    response_hook=None,
):
    products = deepcopy(controlled_products(portfolio, reserve, price))
    positions = products["core-snapshot"]["sections"]["positions_baseline"]
    positions[0].update(
        quantity=str(starting_shares), market_value_local=str(price * starting_shares)
    )
    cash = str(100000 - price * starting_shares)
    positions[1].update(quantity=cash, market_value_local=cash)
    if invalid_legacy:
        products["mandate-binding"]["supportability"] = {
            "state": "INCOMPLETE",
            "reason": "MANDATE_CASH_RESERVE_INVALID",
            "missing_data_families": ["cash_reserve_target"],
        }
    observations = Queue()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            self.respond(body)

        def do_GET(self):
            self.respond(None)

        def respond(self, body):
            path = self.path.split("?")[0]
            key = path.rsplit("/", 1)[-1]
            payload = (product_overrides or {}).get(key, products.get(key))
            observations.put((path, body, self.headers.get("X-Tenant-Id")))
            if response_hook is not None:
                response_hook(path, payload)
            self.send_response(200 if payload else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(payload or {"detail": "CONTROLLED_PRODUCT_UNAVAILABLE"}).encode()
            )

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", observations
    finally:
        server.shutdown()
        server.server_close()
        worker.join(5)
        assert not worker.is_alive(), "Owned controlled producer survived teardown"
