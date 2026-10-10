"""Explicit subprocess-only controlled trust injection; never imported by production."""

from dataclasses import replace

from fastapi import Depends

from src.api.composition.composite_source_service import build_composite_monthly_service
from src.api.dependencies import get_composite_monthly_eligibility_service, get_composite_repository
from tests.composite_historical_policy_helpers import historical_contract_material


def configure_app(app):
    port = historical_contract_material()[0]

    def service(repository=Depends(get_composite_repository)):
        return replace(
            build_composite_monthly_service(repository),
            historical_admission=port,
            clock=lambda: "2026-10-10T04:00:00.000000Z",
        )

    app.dependency_overrides[get_composite_monthly_eligibility_service] = service
