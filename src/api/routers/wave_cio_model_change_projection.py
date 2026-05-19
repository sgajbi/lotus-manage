from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from src.api.routers.wave_source_refs import (
    cio_model_change_affected_mandate_ref,
    cio_model_change_cohort_ref,
    cio_model_change_event_ref,
)


class CioModelChangeSupportability(Protocol):
    @property
    def state(self) -> str: ...


class CioModelChangeAffectedMandate(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def mandate_id(self) -> str: ...

    @property
    def source_record_id(self) -> str | None: ...

    @property
    def binding_version(self) -> object: ...


class CioModelChangeAffectedCohort(Protocol):
    @property
    def snapshot_id(self) -> str | None: ...

    @property
    def source_batch_fingerprint(self) -> str | None: ...

    @property
    def model_change_event_id(self) -> str: ...

    @property
    def product_version(self) -> str: ...

    @property
    def supportability(self) -> CioModelChangeSupportability: ...

    @property
    def model_portfolio_version(self) -> str: ...

    @property
    def affected_mandates(self) -> Sequence[CioModelChangeAffectedMandate]: ...


def build_cio_model_change_resolved_portfolios(
    cohort: CioModelChangeAffectedCohort,
) -> list[dict[str, object]]:
    source_id = (
        cohort.snapshot_id or cohort.source_batch_fingerprint or cohort.model_change_event_id
    )
    cohort_ref = cio_model_change_cohort_ref(
        source_id=source_id,
        product_version=cohort.product_version,
        supportability_state=cohort.supportability.state,
        content_hash=cohort.source_batch_fingerprint,
    )
    event_ref = cio_model_change_event_ref(
        model_change_event_id=cohort.model_change_event_id,
        model_portfolio_version=cohort.model_portfolio_version,
        supportability_state=cohort.supportability.state,
        content_hash=cohort.source_batch_fingerprint,
    )
    return [
        {
            "portfolio_id": mandate.portfolio_id,
            "mandate_id": mandate.mandate_id,
            "source_refs": [
                cohort_ref,
                event_ref,
                cio_model_change_affected_mandate_ref(
                    source_record_id=mandate.source_record_id,
                    mandate_id=mandate.mandate_id,
                    binding_version=mandate.binding_version,
                ),
            ],
        }
        for mandate in cohort.affected_mandates
    ]
