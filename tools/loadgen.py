#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Result:
    status: int
    latency_ms: float


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def request_once(url: str, timeout: float, sequence: int) -> Result:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "sre-observatory-loadgen/0.1", "X-Request-Sequence": str(sequence)},
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except (TimeoutError, urllib.error.URLError):
        status = 0
    return Result(status=status, latency_ms=(time.perf_counter() - start) * 1_000)


def run(url: str, requests_per_second: int, duration_seconds: int, timeout: float) -> dict:
    total = requests_per_second * duration_seconds
    interval = 1 / requests_per_second
    started = time.monotonic()
    futures = []
    workers = min(max(requests_per_second * 2, 4), 64)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for sequence in range(total):
            deadline = started + sequence * interval
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
            futures.append(executor.submit(request_once, url, timeout, sequence + 1))
        results = [future.result() for future in futures]

    latencies = [result.latency_ms for result in results]
    statuses = Counter(str(result.status) for result in results)
    return {
        "url": url,
        "sent": total,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "status_counts": dict(sorted(statuses.items())),
        "latency_ms": {
            "p50": round(percentile(latencies, 0.50), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "p99": round(percentile(latencies, 0.99), 3),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Constant-rate SRE Observatory load generator")
    parser.add_argument("--url", default="http://localhost:8080/work")
    parser.add_argument("--rps", type=int, default=10)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()
    if args.rps < 1 or args.duration < 1 or args.timeout <= 0:
        parser.error("--rps and --duration must be positive; --timeout must be greater than zero")
    print(json.dumps(run(args.url, args.rps, args.duration, args.timeout), indent=2))


if __name__ == "__main__":
    main()
