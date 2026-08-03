from __future__ import annotations

import importlib.util
import itertools
import os
import unittest

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("service integration dependencies are not installed")

os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = ""

from fastapi.testclient import TestClient
from observatory import main  # noqa: E402
from observatory.config import ServiceConfig  # noqa: E402


def test_health_readiness_and_work() -> None:
    with TestClient(main.app) as client:
        assert client.get("/healthz").json() == {"status": "alive"}
        assert client.get("/readyz").status_code == 200
        response = client.get("/work", params={"delay_ms": 0})
        assert response.status_code == 200
        assert response.json()["status"] == "complete"


def test_metrics_expose_normalized_route_labels() -> None:
    with TestClient(main.app) as client:
        client.get("/work", params={"delay_ms": 0})
        metrics = client.get("/metrics").text
    assert "http_server_requests_total" in metrics
    assert 'route="/work"' in metrics
    assert "http_server_request_duration_seconds_bucket" in metrics


def test_deterministic_failure_injection(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "CONFIG",
        ServiceConfig.from_env(
            {
                "FAIL_EVERY_N": "2",
                "DEFAULT_DELAY_MS": "0",
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "",
            }
        ),
    )
    monkeypatch.setattr(main, "REQUEST_SEQUENCE", itertools.count(1))
    with TestClient(main.app) as client:
        assert client.get("/work", params={"delay_ms": 0}).status_code == 200
        assert client.get("/work", params={"delay_ms": 0}).status_code == 503
