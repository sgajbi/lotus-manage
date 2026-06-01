class DpmWaveValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DpmWaveLookupError(LookupError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


__all__ = ["DpmWaveLookupError", "DpmWaveValidationError"]
