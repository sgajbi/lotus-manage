from fastapi import Response

_OBSERVER_RESPONSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-Permitted-Cross-Domain-Policies": "none",
    "X-XSS-Protection": "0",
}


def apply_observability_headers(response: Response) -> None:
    """Apply hardened, deterministic response headers to application responses."""
    for header_name, header_value in _OBSERVER_RESPONSE_HEADERS.items():
        response.headers.setdefault(header_name, header_value)
