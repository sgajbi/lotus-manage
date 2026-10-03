"""Core binding authority cannot authorize another portfolio, mandate or model."""

from datetime import date

import httpx
import pytest

from src.core.dpm_source_context import DpmCoreContextIncompleteError, DpmStatefulInput
from src.infrastructure.core_sourcing import DpmCoreResolverClient, DpmCoreResolverConfig
from tests.integration.dpm.controlled_core import controlled_products


@pytest.mark.parametrize("field", [None, "portfolio_id", "mandate_id", "model_portfolio_id"])
def test_binding_scope_validated_before_downstream_resolution(field):
    binding = controlled_products("portfolio-contract")["mandate-binding"]
    if field:
        binding[field] = "foreign"
    observed = []

    def respond(request):
        observed.append(request.url.path)
        assert request.url.path.endswith("/mandate-binding"), "Mismatch must stop before model IO"
        return httpx.Response(200, json=binding)

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        resolver = DpmCoreResolverClient(
            config=DpmCoreResolverConfig(base_url="http://controlled-core"), client=http
        )
        if field:
            with pytest.raises(DpmCoreContextIncompleteError, match="IDENTITY_MISMATCH"):
                resolver.resolve_execution_context(
                    stateful_input=DpmStatefulInput(
                        portfolio_id="portfolio-contract",
                        mandate_id="mandate-reserve",
                        model_portfolio_id="model-reserve",
                        tenant_id="tenant-contract",
                        as_of=date(2026, 4, 10),
                    ),
                    correlation_id="corr",
                )
        else:
            result = resolver.resolve_mandate_binding(
                portfolio_id="portfolio-contract",
                mandate_id="mandate-reserve",
                as_of_date=date(2026, 4, 10),
                correlation_id="corr",
            )
            assert result.binding_version == 7
    assert len(observed) == 1
