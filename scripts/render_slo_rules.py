#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sre_tools.slo import load_definition, render_prometheus_rules  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Prometheus rules from the SLO definition")
    parser.add_argument("--check", action="store_true", help="fail if the checked-in rules differ")
    args = parser.parse_args()
    source = ROOT / "slo" / "service.json"
    destination = ROOT / "observability" / "prometheus" / "slo-rules.yaml"
    rendered = render_prometheus_rules(load_definition(source))

    if args.check:
        if not destination.exists() or destination.read_text(encoding="utf-8") != rendered:
            print(f"{destination} is stale; run {Path(__file__).name}", file=sys.stderr)
            return 1
        print(f"{destination} is current")
        return 0

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
