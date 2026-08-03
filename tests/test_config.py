from __future__ import annotations

import unittest

from observatory.config import ServiceConfig


class ServiceConfigTests(unittest.TestCase):
    def test_defaults_are_safe_for_normal_operation(self) -> None:
        config = ServiceConfig.from_env({})
        self.assertEqual(config.fail_every_n, 0)
        self.assertEqual(config.default_delay_ms, 20)
        self.assertEqual(config.service_name, "sre-observatory")

    def test_fault_injection_is_bounded(self) -> None:
        config = ServiceConfig.from_env({"FAIL_EVERY_N": "2", "DEFAULT_DELAY_MS": "5000"})
        self.assertEqual(config.fail_every_n, 2)
        self.assertEqual(config.default_delay_ms, 5_000)
        with self.assertRaises(ValueError):
            ServiceConfig.from_env({"FAIL_EVERY_N": "-1"})

    def test_otlp_endpoint_must_be_http(self) -> None:
        with self.assertRaises(ValueError):
            ServiceConfig.from_env({"OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "collector:4318"})


if __name__ == "__main__":
    unittest.main()
