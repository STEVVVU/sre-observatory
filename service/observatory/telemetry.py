from __future__ import annotations

from fastapi import FastAPI
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from observatory.config import ServiceConfig


def configure_tracing(app: FastAPI, config: ServiceConfig) -> TracerProvider:
    resource = Resource.create(
        {
            SERVICE_NAME: config.service_name,
            SERVICE_VERSION: config.service_version,
            "deployment.environment.name": config.environment,
        }
    )
    provider = TracerProvider(resource=resource)
    if config.otlp_traces_endpoint:
        exporter = OTLPSpanExporter(endpoint=config.otlp_traces_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="healthz,readyz,metrics",
    )
    return provider
