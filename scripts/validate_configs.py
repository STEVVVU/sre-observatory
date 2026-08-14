#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sre_tools.slo import load_definition, render_prometheus_rules  # noqa: E402

ERRORS: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def validate_text_files() -> None:
    extensions = {".yaml", ".yml", ".json", ".py", ".sh", ".tf", ".toml"}
    excluded_directories = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".terraform",
        ".venv",
        "__pycache__",
    }
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or path.suffix not in extensions
            or excluded_directories.intersection(path.parts)
        ):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        require("\t" not in text, f"{relative}: tabs are not allowed")
        require(
            all(line == line.rstrip() for line in text.splitlines()),
            f"{relative}: trailing whitespace found",
        )
        require(
            not re.search(r"\b(?:CHANGEME|replace-me|OWNER)\b", text),
            f"{relative}: unresolved placeholder found",
        )


def validate_kubernetes() -> None:
    directory = ROOT / "deploy" / "kubernetes"
    kinds: set[str] = set()
    for path in sorted(directory.glob("*.yaml")):
        for document in path.read_text(encoding="utf-8").split("\n---\n"):
            if not document.strip():
                continue
            api_version = re.search(r"^apiVersion:\s*(\S+)", document, re.MULTILINE)
            kind = re.search(r"^kind:\s*(\S+)", document, re.MULTILINE)
            require(api_version is not None, f"{path.name}: document has no apiVersion")
            require(kind is not None, f"{path.name}: document has no kind")
            if kind:
                kinds.add(kind.group(1))

    require(
        {"Deployment", "Service", "HorizontalPodAutoscaler", "PodDisruptionBudget", "NetworkPolicy"}
        <= kinds,
        "Kubernetes base is missing a required workload safety resource",
    )
    deployment = (directory / "deployment.yaml").read_text(encoding="utf-8")
    for field in (
        "startupProbe:",
        "readinessProbe:",
        "livenessProbe:",
        "resources:",
        "readOnlyRootFilesystem: true",
        "allowPrivilegeEscalation: false",
    ):
        require(field in deployment, f"deployment.yaml: missing {field}")
    kustomization = (directory / "kustomization.yaml").read_text(encoding="utf-8")
    require(
        "drills/load-generator-job.yaml" not in kustomization,
        "load generator must not run during a normal deployment",
    )


def validate_observability() -> None:
    dashboard_path = ROOT / "observability" / "grafana" / "dashboards" / "service-overview.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    require(dashboard.get("uid") == "sre-observatory", "Grafana dashboard UID changed")
    require(len(dashboard.get("panels", [])) >= 5, "Grafana dashboard needs at least five panels")
    expressions = json.dumps(dashboard.get("panels", []))
    for metric in (
        "http_server_requests_total",
        "http_server_request_duration_seconds_bucket",
        "slo:sre_observatory_availability",
    ):
        require(metric in expressions, f"Grafana dashboard does not query {metric}")

    definition = load_definition(ROOT / "slo" / "service.json")
    expected = render_prometheus_rules(definition)
    rules_path = ROOT / "observability" / "prometheus" / "slo-rules.yaml"
    require(rules_path.read_text(encoding="utf-8") == expected, "generated SLO rules are stale")


def validate_repository_contract() -> None:
    required = [
        "README.md",
        "LICENSE",
        "compose.yaml",
        ".github/workflows/ci.yml",
        "docs/architecture.md",
        "docs/operations.md",
        "docs/runbooks/high-error-budget-burn.md",
        "infra/terraform/modules/network/main.tf",
        "infra/terraform/modules/cluster/main.tf",
    ]
    for item in required:
        require((ROOT / item).is_file(), f"required repository file is missing: {item}")

    dockerfile = (ROOT / "service" / "Dockerfile").read_text(encoding="utf-8")
    require("USER 10001:10001" in dockerfile, "service image must run as a non-root UID")
    require(":latest" not in dockerfile, "Dockerfile must not use a latest tag")


def main() -> int:
    validate_text_files()
    validate_kubernetes()
    validate_observability()
    validate_repository_contract()
    if ERRORS:
        print("configuration validation failed:", file=sys.stderr)
        for error in ERRORS:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("configuration validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
