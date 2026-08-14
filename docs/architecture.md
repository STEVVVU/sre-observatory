# Architecture

## Goals

SRE Observatory keeps application behavior, telemetry contracts, reliability objectives, and
operational controls in one reviewable repository. It is deliberately small enough to inspect
without treating a managed service or framework as a black box.

## Request and Telemetry Flow

1. A client calls the internal Kubernetes Service or the Compose `app` service.
2. FastAPI middleware records request count, duration, in-flight work, normalized route, and status.
3. FastAPI OpenTelemetry instrumentation creates server spans. The application adds route and
   elapsed-time attributes and returns a trace ID from `/work`.
4. Prometheus scrapes `/metrics`. Generated recording rules calculate bad-event ratios over seven
   unique windows.
5. The OpenTelemetry Collector batches and enriches spans. Compose exports to Tempo; Kubernetes
   uses the debug exporter until an operator selects a durable backend.
6. Grafana provisions Prometheus and Tempo data sources and a service dashboard.

## Service Boundaries

`observatory.config` is dependency-free and validates all behavior-affecting environment values.
`FAIL_EVERY_N=0` is the safe default. A positive value introduces deterministic 503 responses only
on `/work`; health and readiness remain truthful so an exercise tests SLO response rather than
process restarts.

Prometheus labels are bounded to HTTP method, normalized framework route, and status code. Request
IDs, raw paths, and trace IDs are not metric labels. Trace IDs belong in traces and responses, where
they do not create time-series cardinality.

## Reliability Model

The availability SLI is:

```text
5xx requests / all requests
```

The latency SLI is:

```text
1 - (requests in the <=300 ms histogram bucket / all requests)
```

Probe and `/metrics` traffic are excluded. For objective `O`, error budget is `1 - O`; burn rate is
`bad-event ratio / error budget`. Alerts require both a long and a short window to exceed the same
threshold, limiting transient pages while preserving fast detection.

## Kubernetes Safety

- Two baseline replicas, zero-unavailable rolling updates, PDB, and topology spreading reduce
  voluntary-disruption and rollout risk.
- HPA uses CPU and memory utilization with conservative scale-down stabilization.
- Restricted pod security, non-root UIDs, dropped capabilities, read-only filesystems, no service
  account token, and namespace-scoped NetworkPolicy reduce workload privileges.
- Startup, readiness, and liveness checks have distinct responsibilities.

The NetworkPolicy allows service ingress only from the `observability` namespace and egress only to
cluster DNS and the colocated OTLP collector. Any ingress controller or external collector requires
an explicit policy change.

## Infrastructure Boundary

Terraform composes local network and cluster modules. The EKS API is private by default, control
plane logs are enabled, nodes require IMDSv2 and encrypted storage, and cluster access must be
provided as an explicit IAM access entry. State storage and operator identity are deployment inputs,
not embedded assumptions.

