from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


def _integer(
    values: Mapping[str, str], name: str, default: int, *, minimum: int, maximum: int
) -> int:
    raw = values.get(name, str(default))
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}, got {parsed}")
    return parsed


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    service_name: str
    service_version: str
    environment: str
    otlp_traces_endpoint: str
    default_delay_ms: int
    fail_every_n: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ServiceConfig:
        values = os.environ if env is None else env
        service_name = values.get("OTEL_SERVICE_NAME", "sre-observatory").strip()
        environment = values.get("DEPLOYMENT_ENVIRONMENT", "local").strip()
        endpoint = values.get(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "http://otel-collector.observability.svc.cluster.local:4318/v1/traces",
        ).strip()
        if not service_name:
            raise ValueError("OTEL_SERVICE_NAME cannot be empty")
        if not environment:
            raise ValueError("DEPLOYMENT_ENVIRONMENT cannot be empty")
        if endpoint and not endpoint.startswith(("http://", "https://")):
            raise ValueError("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT must be an HTTP(S) URL")

        return cls(
            service_name=service_name,
            service_version=values.get("SERVICE_VERSION", "dev").strip() or "dev",
            environment=environment,
            otlp_traces_endpoint=endpoint,
            default_delay_ms=_integer(values, "DEFAULT_DELAY_MS", 20, minimum=0, maximum=5_000),
            fail_every_n=_integer(values, "FAIL_EVERY_N", 0, minimum=0, maximum=10_000),
        )
