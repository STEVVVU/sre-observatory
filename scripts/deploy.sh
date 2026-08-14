#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-observability}"
DEPLOYMENT="${DEPLOYMENT:-sre-observatory}"
IMAGE="${IMAGE:-${1:-}}"
TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"

if [[ -z "${IMAGE}" ]]; then
  echo "usage: IMAGE=registry/repository:immutable-tag $0" >&2
  exit 2
fi
if [[ "${IMAGE}" == *":latest" || "${IMAGE}" != *":"* && "${IMAGE}" != *"@sha256:"* ]]; then
  echo "IMAGE must use an explicit non-latest tag or digest: ${IMAGE}" >&2
  exit 2
fi
command -v kubectl >/dev/null || {
  echo "kubectl is required" >&2
  exit 127
}

previous_image="$(
  kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}" \
    -o jsonpath='{.spec.template.spec.containers[?(@.name=="service")].image}' 2>/dev/null || true
)"
rollback_required=false

on_exit() {
  status=$?
  if [[ ${status} -ne 0 && "${rollback_required}" == "true" ]]; then
    echo "Deployment verification failed; rolling back to the previous ReplicaSet." >&2
    kubectl -n "${NAMESPACE}" rollout undo "deployment/${DEPLOYMENT}" || true
    kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout="${TIMEOUT}" || true
  fi
  exit "${status}"
}
trap on_exit EXIT

kubectl apply -f "${ROOT}/deploy/kubernetes/namespace.yaml"
kubectl kustomize "${ROOT}/deploy/kubernetes" |
  awk -v image="${IMAGE}" -v version="${IMAGE##*:}" '
    $1 == "image:" && $2 == "sre-observatory:dev" { $2 = image }
    $1 == "name:" && $2 == "SERVICE_VERSION" { service_version = 1 }
    service_version && $1 == "value:" { $2 = version; service_version = 0 }
    { print }
  ' |
  kubectl apply -f -
kubectl -n "${NAMESPACE}" annotate "deployment/${DEPLOYMENT}" \
  "kubernetes.io/change-cause=image ${IMAGE}" --overwrite

if [[ -n "${previous_image}" && "${previous_image}" != "${IMAGE}" ]]; then
  rollback_required=true
fi

kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout="${TIMEOUT}"

smoke_name="sre-observatory-smoke-$(date +%s)"
kubectl -n "${NAMESPACE}" run "${smoke_name}" \
  --image=curlimages/curl:8.12.1 \
  --restart=Never \
  --rm \
  --attach \
  --quiet \
  --command -- sh -ec \
  "curl --fail --silent --show-error http://${DEPLOYMENT}/readyz >/dev/null &&
   curl --fail --silent --show-error http://${DEPLOYMENT}/work >/dev/null"

rollback_required=false
trap - EXIT
echo "Deployed ${IMAGE}; rollout and in-cluster smoke checks passed."
