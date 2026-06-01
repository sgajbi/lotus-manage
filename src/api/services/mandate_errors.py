class DpmMandateNotFoundError(LookupError):
    pass


class DpmMandateDiffUnavailableError(LookupError):
    pass


class DpmMandateSourceUnavailableError(RuntimeError):
    pass


class DpmMandateSourceIncompleteError(RuntimeError):
    pass


class DpmMandateHealthNotFoundError(LookupError):
    pass


class DpmMonitoringRunNotFoundError(LookupError):
    pass


__all__ = [
    "DpmMandateDiffUnavailableError",
    "DpmMandateHealthNotFoundError",
    "DpmMandateNotFoundError",
    "DpmMandateSourceIncompleteError",
    "DpmMandateSourceUnavailableError",
    "DpmMonitoringRunNotFoundError",
]
