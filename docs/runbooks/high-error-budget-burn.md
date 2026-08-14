# High Error-Budget Burn

## Trigger

Any `SLOBurnRate_sre_observatory_*` alert indicates that availability or latency bad-event ratios
exceeded the configured budget multiplier in both its long and short windows.

## Immediate Checks

1. Acknowledge the page and identify the SLO, windows, first firing time, and recent deployment.
2. Confirm user-work traffic exists; a zero-traffic service should produce a zero bad ratio.
3. Check rollout and pod state:

```bash
kubectl -n observability get deploy,pod,hpa
kubectl -n observability rollout history deployment/sre-observatory
kubectl -n observability describe deployment sre-observatory
```

4. Verify the controlled drill flag is absent:

```bash
kubectl -n observability get deployment sre-observatory \
  -o jsonpath='{.spec.template.spec.containers[0].env}'
```

## Prometheus Triage

Request and error rate:

```promql
sum by (route, status_code) (rate(http_server_requests_total[5m]))
```

p95 by route:

```promql
histogram_quantile(
  0.95,
  sum by (le, route) (rate(http_server_request_duration_seconds_bucket[5m]))
)
```

Fast availability burn:

```promql
slo:sre_observatory_availability:bad_ratio_rate1h / 0.001
```

Compare failures by pod and inspect matching traces in Tempo or the configured trace backend. For
Kubernetes' default debug exporter, inspect `deployment/otel-collector` logs.

## Mitigation

- **Recent release correlated:** run `./scripts/rollback.sh`, verify rollout, then repeat `/readyz`
  and `/work` from inside the namespace.
- **Injected drill left active:** remove the override with
  `kubectl -n observability set env deployment/sre-observatory FAIL_EVERY_N-`.
- **Capacity pressure:** inspect HPA desired/current replicas, pending pods, and node capacity before
  changing limits. Do not mask an application error by scaling blindly.
- **Collector failure only:** service requests should continue; restore telemetry separately unless
  missing visibility prevents safe operation.

Escalate to the service owner when rollback does not reduce the short-window ratio or when multiple
services indicate a shared platform dependency.

## Recovery Criteria

- `/readyz` succeeds across current pods.
- 5xx rate and p95 return below their SLO thresholds.
- Short-window burn rate remains below threshold for at least one evaluation interval.
- Deployment image, replica state, and `FAIL_EVERY_N` are documented.

Capture the alert timeline, relevant dashboard/traces, mitigation, and follow-up owner. Do not claim
budget recovery until the rolling windows have actually decayed.

