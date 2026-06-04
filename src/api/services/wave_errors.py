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


class DpmWaveDependencyError(ValueError):
    status_code: int

    def __init__(self, *, code: str, message: str | None = None, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(code)

    def __str__(self) -> str:
        return self.code


class DpmWaveDependencyUnavailableError(DpmWaveDependencyError):
    def __init__(self, *, code: str, message: str | None = None) -> None:
        super().__init__(code=code, message=message, status_code=503)


class DpmWaveDependencyFailedError(DpmWaveDependencyError):
    def __init__(self, *, code: str, message: str | None = None) -> None:
        super().__init__(code=code, message=message, status_code=424)


__all__ = [
    "DpmWaveDependencyError",
    "DpmWaveDependencyFailedError",
    "DpmWaveDependencyUnavailableError",
    "DpmWaveLookupError",
    "DpmWaveValidationError",
]
