from __future__ import annotations

import asyncio
import itertools
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Response
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

from observatory import __version__
from observatory.config import ServiceConfig
from observatory.telemetry import configure_tracing

CONFIG = ServiceConfig.from_env()
REQUEST_SEQUENCE = itertools.count(1)

HTTP_REQUESTS = Counter(
    "http_server_requests_total",
    "Completed HTTP requests.",
    ("method", "route", "status_code"),
)
HTTP_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "HTTP request latency.",
    ("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.3, 0.5, 1.0, 2.5, 5.0),
)
HTTP_IN_FLIGHT = Gauge(
    "http_server_requests_in_flight",
    "HTTP requests currently being processed.",
)
WORK_OPERATIONS = Counter(
    "observatory_work_operations_total",
    "Synthetic work operations.",
    ("outcome",),
)
READINESS = Gauge("observatory_ready", "Whether this process can receive traffic.")
BUILD_INFO = Info("observatory_build", "Build and deployment metadata.")
BUILD_INFO.info(
    {
        "version": CONFIG.service_version,
        "environment": CONFIG.environment,
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ready = True
    READINESS.set(1)
    try:
        yield
    finally:
        app.state.ready = False
        READINESS.set(0)


app = FastAPI(
    title="SRE Observatory",
    version=__version__,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
TRACER_PROVIDER = configure_tracing(app, CONFIG)


@app.middleware("http")
async def observe_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    status_code = 500
    HTTP_IN_FLIGHT.inc()
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route_object = request.scope.get("route")
        route = getattr(route_object, "path", "unmatched")
        method = request.method
        elapsed = time.perf_counter() - start
        HTTP_IN_FLIGHT.dec()
        HTTP_REQUESTS.labels(method=method, route=route, status_code=str(status_code)).inc()
        HTTP_DURATION.labels(method=method, route=route).observe(elapsed)
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("http.route", route)
            span.set_attribute("observatory.elapsed_ms", elapsed * 1_000)


@app.get("/", include_in_schema=False)
async def index() -> dict[str, str]:
    return {"service": CONFIG.service_name, "status": "ok", "version": CONFIG.service_version}


@app.get("/healthz", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/readyz", include_in_schema=False)
async def readiness(request: Request) -> dict[str, str]:
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail="service is not ready")
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/work")
async def work(
    delay_ms: int = Query(default=CONFIG.default_delay_ms, ge=0, le=5_000),
) -> dict[str, int | str]:
    request_number = next(REQUEST_SEQUENCE)
    await asyncio.sleep(delay_ms / 1_000)

    if CONFIG.fail_every_n and request_number % CONFIG.fail_every_n == 0:
        WORK_OPERATIONS.labels(outcome="injected_failure").inc()
        raise HTTPException(status_code=503, detail="deterministic fault injected")

    WORK_OPERATIONS.labels(outcome="success").inc()
    span_context = trace.get_current_span().get_span_context()
    trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else "unavailable"
    return {
        "status": "complete",
        "request_number": request_number,
        "delay_ms": delay_ms,
        "trace_id": trace_id,
    }
