# Deterministic Failure Drill

## Objective

Exercise detection, evidence capture, and recovery for a high 5xx rate without killing processes,
modifying external state, or depending on random timing.

This document describes an executable drill; it does not claim the drill has run in a real cluster.

## Preconditions

- The current service image was deployed with `scripts/deploy.sh`.
- Prometheus scrapes service pods and loads the generated SLO rules.
- Operators can update the Deployment and create a Job in `observability`.
- No active user-impacting incident is in progress.

## Procedure

```bash
CONFIRM_CHAOS=sre-observatory ./scripts/chaos-drill.sh
```

The script:

1. verifies the Deployment exists;
2. rolls out `FAIL_EVERY_N=2`;
3. starts a three-minute, 20-RPS Job using the exact deployed service image;
4. records the load generator's JSON output under ignored `artifacts/`;
5. requires all 3,600 requests to be observed and a 45-55% 503 ratio;
6. removes the environment override and waits for recovery, even after interruption.

## Expected Signals

- `http_server_requests_total{status_code="503",route="/work"}` rises at roughly half of work
  traffic.
- Availability bad ratio approaches 0.5, far above the 0.001 budget.
- The 1h/5m availability burn-rate alert can enter pending/firing once Prometheus has enough samples
  and the two-minute `for` duration is met.
- Liveness/readiness stay healthy because the process is operating as designed.
- Traces for failed requests carry HTTP 503 status.

## Safeguards

- An exact confirmation string is required.
- Faults affect only `/work`; no storage or third-party systems exist.
- The Job has a fixed request count, timeout, no retries, and bounded resources.
- An EXIT/INT/TERM trap removes the fault override.
- The load Job is excluded from normal Kustomize deployment.

## Evidence

Retain the generated JSON, alert timeline, dashboard capture, trace IDs, and observed recovery time
in the incident system. `artifacts/` is intentionally ignored because operational evidence may
contain environment-specific data.

