#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-observability}"
DEPLOYMENT="${DEPLOYMENT:-sre-observatory}"
JOB="${JOB:-sre-observatory-drill-load}"
TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"
ARTIFACT="${ROOT}/artifacts/chaos-drill-$(date -u +%Y%m%dT%H%M%SZ).json"

if [[ "${CONFIRM_CHAOS:-}" != "sre-observatory" ]]; then
  echo "Set CONFIRM_CHAOS=sre-observatory to run the controlled failure drill." >&2
  exit 2
fi
command -v kubectl >/dev/null || {
  echo "kubectl is required" >&2
  exit 127
}

restore() {
  status=$?
  trap - EXIT INT TERM
  echo "Restoring normal behavior..."
  kubectl -n "${NAMESPACE}" set env "deployment/${DEPLOYMENT}" FAIL_EVERY_N- || true
  kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout="${TIMEOUT}" || true
  kubectl -n "${NAMESPACE}" delete job "${JOB}" --ignore-not-found --wait=false || true
  exit "${status}"
}
trap restore EXIT INT TERM

kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}" >/dev/null
kubectl -n "${NAMESPACE}" set env "deployment/${DEPLOYMENT}" FAIL_EVERY_N=2
kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout="${TIMEOUT}"

current_image="$(
  kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}" \
    -o jsonpath='{.spec.template.spec.containers[?(@.name=="service")].image}'
)"
kubectl -n "${NAMESPACE}" delete job "${JOB}" --ignore-not-found --wait=true
sed "s|image: sre-observatory:dev|image: ${current_image}|" \
  "${ROOT}/deploy/kubernetes/drills/load-generator-job.yaml" |
  kubectl -n "${NAMESPACE}" apply -f -
kubectl -n "${NAMESPACE}" wait --for=condition=complete "job/${JOB}" --timeout=300s

mkdir -p "${ROOT}/artifacts"
kubectl -n "${NAMESPACE}" logs "job/${JOB}" | tee "${ARTIFACT}"

python - "${ARTIFACT}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    result = json.load(handle)
statuses = result["status_counts"]
success = int(statuses.get("200", 0))
failures = int(statuses.get("503", 0))
observed = success + failures
ratio = failures / observed if observed else 0
if observed != result["sent"] or not 0.45 <= ratio <= 0.55:
    raise SystemExit(
        f"unexpected drill result: sent={result['sent']} observed={observed} "
        f"503_ratio={ratio:.3f}"
    )
print(f"Validated deterministic fault signal: {failures}/{observed} requests returned 503.")
PY

echo "Drill evidence written to ${ARTIFACT}."
