# Operations

## Validation

Run before review:

```bash
PYTHONPATH=service python -m unittest discover -s tests -v
python scripts/render_slo_rules.py --check
python scripts/validate_configs.py
```

CI additionally runs Ruff, mypy, pytest, ShellCheck, yamllint, kubeconform, promtool, Hadolint,
Docker build, `terraform fmt`, `terraform init -backend=false`, and `terraform validate`.

## Local Observability

```bash
docker compose up --build -d
python tools/loadgen.py --url http://localhost:8080/work --rps 10 --duration 30
docker compose down
```

Compose retains Tempo data in a named volume for 24 hours. Grafana permits anonymous Viewer access
only for this local stack. Do not copy that authentication setting to a shared environment.

## Infrastructure Planning

The Terraform development environment creates billable AWS resources. It has not been applied by
this repository.

1. Create an S3 state bucket and lock-table strategy according to the owning organization's policy.
2. Select an EKS version currently supported in the target region.
3. Supply a connected operator role; the private API endpoint is unreachable from the public
   internet.
4. Initialize with backend values and inspect the plan:

```bash
terraform -chdir=infra/terraform/environments/dev init \
  -backend-config="bucket=STATE_BUCKET" \
  -backend-config="key=sre-observatory/dev.tfstate" \
  -backend-config="region=us-west-2"
terraform -chdir=infra/terraform/environments/dev plan \
  -var="operator_role_arn=arn:aws:iam::ACCOUNT_ID:role/PLATFORM_OPERATOR"
```

The dev default uses one NAT gateway. Set `single_nat_gateway=false` for one per availability zone
when resilience justifies the additional cost.

## Release

Prerequisites: authenticated kubectl access, a pullable immutable image tag or digest, metrics-server
for HPA, and Prometheus configured to discover annotated pods.

```bash
IMAGE=registry.example/sre-observatory:git-sha ./scripts/deploy.sh
```

The script applies the Kustomize base, changes only the service image/version, waits for rollout,
and issues readiness and work requests from a temporary pod inside the namespace. A failed update
automatically rolls back when a previous Deployment exists.

Inspect:

```bash
kubectl -n observability get deploy,pod,svc,hpa,pdb
kubectl -n observability rollout history deployment/sre-observatory
kubectl -n observability logs deployment/otel-collector
```

## Rollback

```bash
./scripts/rollback.sh
REVISION=3 ./scripts/rollback.sh
```

Rollback changes only Deployment history. If the release includes incompatible external state or
schema changes, use a separately reviewed forward-fix or migration rollback.

## Trace Backend

The Kubernetes collector deliberately uses a debug exporter, proving receipt without pretending to
provide durable storage. Replace or supplement it with an authenticated OTLP exporter and update
NetworkPolicy egress before using the environment operationally. The Compose profile already routes
traces to Tempo for local inspection.

