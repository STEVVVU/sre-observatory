# Service-Level Objectives

## Definitions

The source of truth is [`../slo/service.json`](../slo/service.json). Availability targets 99.9% and
latency targets 99% of requests below 300 ms over a rolling 30-day period. Health, readiness, and
metrics requests are excluded because they do not represent user work.

## Alert Policy

| Long window | Short window | Burn rate | Severity | Approximate 30-day budget consumed |
| --- | --- | ---: | --- | ---: |
| 1 hour | 5 minutes | 14.4x | page | 2% per hour |
| 6 hours | 30 minutes | 6x | page | 5% per 6 hours |
| 1 day | 2 hours | 3x | ticket | 10% per day |
| 3 days | 6 hours | 1x | ticket | 10% per 3 days |

Both windows must breach. The longer window establishes material budget consumption; the shorter
window confirms the condition remains active.

## Changing an Objective

1. Update `slo/service.json`.
2. Run `python scripts/render_slo_rules.py`.
3. Review the definition and generated PromQL together.
4. Run unit tests and `promtool check rules`.
5. Obtain service-owner approval because objective changes alter paging and release policy.

Generated rules must not be edited directly. CI fails when they differ from compiler output.

