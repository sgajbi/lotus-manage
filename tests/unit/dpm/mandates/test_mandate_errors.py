from src.api.services import mandate_service
from src.api.services.mandate_errors import (
    DpmMandateDiffUnavailableError,
    DpmMandateHealthNotFoundError,
    DpmMandateNotFoundError,
    DpmMandateSourceIncompleteError,
    DpmMandateSourceUnavailableError,
    DpmMonitoringRunNotFoundError,
)


def test_mandate_service_preserves_imported_error_surface() -> None:
    assert mandate_service.DpmMandateNotFoundError is DpmMandateNotFoundError
    assert mandate_service.DpmMandateDiffUnavailableError is DpmMandateDiffUnavailableError
    assert mandate_service.DpmMandateSourceUnavailableError is DpmMandateSourceUnavailableError
    assert mandate_service.DpmMandateSourceIncompleteError is DpmMandateSourceIncompleteError
    assert mandate_service.DpmMandateHealthNotFoundError is DpmMandateHealthNotFoundError
    assert mandate_service.DpmMonitoringRunNotFoundError is DpmMonitoringRunNotFoundError


def test_mandate_error_types_keep_exception_families() -> None:
    assert issubclass(DpmMandateNotFoundError, LookupError)
    assert issubclass(DpmMandateDiffUnavailableError, LookupError)
    assert issubclass(DpmMandateHealthNotFoundError, LookupError)
    assert issubclass(DpmMonitoringRunNotFoundError, LookupError)
    assert issubclass(DpmMandateSourceUnavailableError, RuntimeError)
    assert issubclass(DpmMandateSourceIncompleteError, RuntimeError)


def test_mandate_errors_exports_only_error_types() -> None:
    from src.api.services import mandate_errors

    assert mandate_errors.__all__ == [
        "DpmMandateDiffUnavailableError",
        "DpmMandateHealthNotFoundError",
        "DpmMandateNotFoundError",
        "DpmMandateSourceIncompleteError",
        "DpmMandateSourceUnavailableError",
        "DpmMonitoringRunNotFoundError",
    ]
