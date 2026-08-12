from __future__ import annotations

import unittest
from pathlib import Path

from sre_tools.slo import (
    budget_consumed,
    build_rule_groups,
    burn_rate,
    error_budget,
    load_definition,
    render_prometheus_rules,
)

ROOT = Path(__file__).resolve().parents[1]


class SLOMathTests(unittest.TestCase):
    def test_error_budget_and_burn_rate(self) -> None:
        self.assertAlmostEqual(error_budget(0.999), 0.001)
        self.assertAlmostEqual(burn_rate(10, 10_000, 0.999), 1.0)
        self.assertEqual(burn_rate(0, 0, 0.999), 0.0)

    def test_fast_burn_consumes_two_percent_of_monthly_budget_in_one_hour(self) -> None:
        consumed = budget_consumed(14.4, 60 * 60, 30 * 24 * 60 * 60)
        self.assertAlmostEqual(consumed, 0.02)

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            error_budget(1.0)
        with self.assertRaises(ValueError):
            burn_rate(2, 1, 0.99)
        with self.assertRaises(ValueError):
            budget_consumed(-1, 60, 3600)


class RuleGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition = load_definition(ROOT / "slo" / "service.json")

    def test_generates_deduplicated_recording_rules_and_eight_alerts(self) -> None:
        recording, alerts = build_rule_groups(self.definition)
        self.assertEqual(len(recording["rules"]), 14)
        self.assertEqual(len(alerts["rules"]), 8)
        names = [rule["record"] for rule in recording["rules"]]
        self.assertEqual(len(names), len(set(names)))

    def test_alert_thresholds_use_each_indicators_budget(self) -> None:
        _, alerts = build_rule_groups(self.definition)
        availability = alerts["rules"][0]["expr"]
        latency = alerts["rules"][4]["expr"]
        self.assertIn("> 0.0144", availability)
        self.assertIn("> 0.144", latency)

    def test_render_is_deterministic_and_contains_runbook(self) -> None:
        first = render_prometheus_rules(self.definition)
        second = render_prometheus_rules(self.definition)
        self.assertEqual(first, second)
        self.assertIn("high-error-budget-burn.md", first)
        self.assertTrue(first.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
