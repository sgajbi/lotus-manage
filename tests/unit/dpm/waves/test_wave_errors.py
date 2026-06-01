from src.api.services import wave_service
from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError


def test_wave_validation_error_preserves_code_and_message() -> None:
    error = DpmWaveValidationError("DPM_WAVE_INVALID", "Wave command is invalid.")

    assert str(error) == "Wave command is invalid."
    assert error.code == "DPM_WAVE_INVALID"
    assert error.message == "Wave command is invalid."


def test_wave_lookup_error_preserves_code_and_message() -> None:
    error = DpmWaveLookupError("DPM_WAVE_NOT_FOUND", "Wave was not found.")

    assert str(error) == "Wave was not found."
    assert error.code == "DPM_WAVE_NOT_FOUND"
    assert error.message == "Wave was not found."


def test_wave_service_preserves_imported_error_surface() -> None:
    assert wave_service.DpmWaveValidationError is DpmWaveValidationError
    assert wave_service.DpmWaveLookupError is DpmWaveLookupError


def test_wave_errors_exports_only_wave_error_types() -> None:
    from src.api.services import wave_errors

    assert wave_errors.__all__ == ["DpmWaveLookupError", "DpmWaveValidationError"]
