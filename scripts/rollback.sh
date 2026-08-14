#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="${NAMESPACE:-observability}"
DEPLOYMENT="${DEPLOYMENT:-sre-observatory}"
TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"
REVISION="${REVISION:-${1:-}}"

command -v kubectl >/dev/null || {
  echo "kubectl is required" >&2
  exit 127
}

if [[ -n "${REVISION}" ]]; then
  kubectl -n "${NAMESPACE}" rollout undo "deployment/${DEPLOYMENT}" \
    --to-revision="${REVISION}"
else
  kubectl -n "${NAMESPACE}" rollout undo "deployment/${DEPLOYMENT}"
fi

kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout="${TIMEOUT}"
kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}" \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[0].image,READY:.status.readyReplicas'

