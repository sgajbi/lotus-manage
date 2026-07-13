from src.api.main import app
from tests.integration.test_openapi_certification_matrix import (
    PM_QUALITY_OPENAPI_OPERATIONS_UNDER_CERTIFICATION,
)


def test_pm_quality_openapi_certification_inventory_covers_registered_operations() -> None:
    schema = app.openapi()

    registered_operations = {
        (path, method)
        for path, operations in schema["paths"].items()
        if "/pm-operating-quality/" in path
        for method in operations
    }

    assert registered_operations == set(PM_QUALITY_OPENAPI_OPERATIONS_UNDER_CERTIFICATION)
