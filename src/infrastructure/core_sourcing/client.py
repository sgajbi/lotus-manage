from dataclasses import dataclass
from typing import Optional

import httpx

from src.core.dpm_source_context import (
    DpmCoreExecutionContext,
    DpmStatefulInput,
    build_core_resolver_payload,
)


class DpmCoreResolverError(RuntimeError):
    pass


class DpmCoreResolverUnavailableError(DpmCoreResolverError):
    pass


LEGACY_DPM_EXECUTION_CONTEXT_PATH = "/integration/portfolios/{portfolio_id}/dpm-execution-context"


@dataclass(frozen=True)
class DpmCoreResolverConfig:
    base_url: str
    path_template: str = ""
    timeout_seconds: float = 2.0
    max_attempts: int = 2

    def resolve_url(self, portfolio_id: str) -> str:
        if not self.path_template.strip():
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
        if self.path_template.strip() == LEGACY_DPM_EXECUTION_CONTEXT_PATH:
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
        base = self.base_url.rstrip("/")
        path = self.path_template.format(portfolio_id=portfolio_id).lstrip("/")
        return f"{base}/{path}"


class DpmCoreResolverClient:
    def __init__(
        self,
        *,
        config: DpmCoreResolverConfig,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = config
        self._client = client
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def resolve_execution_context(
        self,
        *,
        stateful_input: DpmStatefulInput,
        correlation_id: Optional[str],
    ) -> DpmCoreExecutionContext:
        attempts = max(self._config.max_attempts, 1)
        url = self._config.resolve_url(stateful_input.portfolio_id)
        payload = build_core_resolver_payload(stateful_input)
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = self._client or httpx.Client(timeout=self._config.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    if response.status_code in {502, 503, 504} and attempt + 1 < attempts:
                        continue
                    if response.status_code >= 500:
                        raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
                    if response.status_code >= 400:
                        raise DpmCoreResolverError("DPM_CORE_CONTEXT_INCOMPLETE")
                    return DpmCoreExecutionContext.model_validate(response.json())
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise DpmCoreResolverUnavailableError(
                            "DPM_CORE_RESOLVER_UNAVAILABLE"
                        ) from exc
            raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE") from last_error
        finally:
            if self._owns_client:
                client.close()
