from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AlertWindow:
    long: str
    short: str
    burn_rate: float
    severity: str


def error_budget(objective: float) -> float:
    if not 0 < objective < 1:
        raise ValueError("objective must be between zero and one")
    return 1 - objective


def burn_rate(bad_events: int, total_events: int, objective: float) -> float:
    if total_events <= 0:
        return 0.0
    if not 0 <= bad_events <= total_events:
        raise ValueError("bad_events must be between zero and total_events")
    return (bad_events / total_events) / error_budget(objective)


def budget_consumed(burn: float, elapsed_seconds: float, period_seconds: float) -> float:
    if burn < 0 or elapsed_seconds < 0 or period_seconds <= 0:
        raise ValueError("burn and elapsed must be non-negative; period must be positive")
    return burn * elapsed_seconds / period_seconds


def load_definition(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bad_ratio_expression(
    definition: dict[str, Any], indicator: dict[str, Any], window: str
) -> str:
    metric = definition["metrics"]["request_counter"]
    route_filter = definition["metrics"]["route_filter"]
    base = f'{metric}{{route!~"{route_filter}"'
    total = f"sum(rate({base}}}[{window}]))"
    if indicator["type"] == "availability":
        bad = f'sum(rate({base},status_code=~"5.."}}[{window}]))'
        return f"{bad}\n/\nclamp_min({total}, 1e-9)"
    if indicator["type"] == "latency":
        histogram = definition["metrics"]["request_duration_histogram"]
        threshold = indicator["threshold_seconds"]
        good = (
            f'sum(rate({histogram}_bucket{{route!~"{route_filter}",le="{threshold}"}}[{window}]))'
        )
        count = f'sum(rate({histogram}_count{{route!~"{route_filter}"}}[{window}]))'
        return f"1 - (\n  {good}\n  /\n  clamp_min({count}, 1e-9)\n)"
    raise ValueError(f"unsupported indicator type: {indicator['type']}")


def build_rule_groups(definition: dict[str, Any]) -> list[dict[str, Any]]:
    service = definition["service"].replace("-", "_")
    windows = [AlertWindow(**item) for item in definition["alert_windows"]]
    recording_rules: list[dict[str, Any]] = []
    alert_rules: list[dict[str, Any]] = []

    for indicator in definition["indicators"]:
        objective = float(indicator["objective"])
        budget = error_budget(objective)
        seen_windows: set[str] = set()
        for pair in windows:
            for window in (pair.long, pair.short):
                if window in seen_windows:
                    continue
                seen_windows.add(window)
                record = f"slo:{service}_{indicator['name']}:bad_ratio_rate{window}"
                recording_rules.append(
                    {
                        "record": record,
                        "expr": _bad_ratio_expression(definition, indicator, window),
                        "labels": {
                            "service": definition["service"],
                            "slo": indicator["name"],
                        },
                    }
                )

            threshold = pair.burn_rate * budget
            long_record = f"slo:{service}_{indicator['name']}:bad_ratio_rate{pair.long}"
            short_record = f"slo:{service}_{indicator['name']}:bad_ratio_rate{pair.short}"
            alert_rules.append(
                {
                    "alert": (
                        f"SLOBurnRate_{service}_{indicator['name']}_{pair.long}_{pair.short}"
                    ),
                    "expr": (
                        f"({long_record} > {threshold:.12g})\n"
                        f"and\n({short_record} > {threshold:.12g})"
                    ),
                    "for": "2m",
                    "labels": {
                        "severity": pair.severity,
                        "service": definition["service"],
                        "slo": indicator["name"],
                    },
                    "annotations": {
                        "summary": (
                            f"{definition['service']} {indicator['name']} error budget "
                            f"is burning at >{pair.burn_rate:g}x"
                        ),
                        "runbook_url": definition["runbook_url"],
                    },
                }
            )

    return [
        {"name": f"{service}.slo.recording", "rules": recording_rules},
        {"name": f"{service}.slo.alerts", "rules": alert_rules},
    ]


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def render_prometheus_rules(definition: dict[str, Any]) -> str:
    lines = ["groups:"]
    for group in build_rule_groups(definition):
        lines.append(f"  - name: {_quote(group['name'])}")
        lines.append("    rules:")
        for rule in group["rules"]:
            key = "record" if "record" in rule else "alert"
            lines.append(f"      - {key}: {_quote(rule[key])}")
            lines.append("        expr: |")
            lines.extend(f"          {line}" for line in rule["expr"].splitlines())
            if "for" in rule:
                lines.append(f"        for: {_quote(rule['for'])}")
            lines.append("        labels:")
            for label, value in rule["labels"].items():
                lines.append(f"          {label}: {_quote(str(value))}")
            if "annotations" in rule:
                lines.append("        annotations:")
                for annotation, value in rule["annotations"].items():
                    lines.append(f"          {annotation}: {_quote(str(value))}")
    return "\n".join(lines) + "\n"
