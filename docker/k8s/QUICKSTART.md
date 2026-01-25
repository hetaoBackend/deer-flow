# Kubernetes Sandbox Quick Start

A simplified setup guide for getting started with the Kubernetes sandbox provider.

## TL;DR (Using Setup Script)

```bash
# 1. Enable Kubernetes (Docker Desktop) or start Minikube
# Docker Desktop → Settings → Kubernetes → Enable Kubernetes
# OrbStack Desktop → Kubernetes → Enable Kubernetes

# 2. Run the setup script
cd docker/k8s
./setup.sh
```

## Manual Setup

If you prefer manual setup or need more control:

```bash
# 1. Enable Kubernetes (Docker Desktop) or start Minikube
# Docker Desktop → Settings → Kubernetes → Enable Kubernetes

# 2. Update skills path and deploy
cd docker/k8s
PROJECT_ROOT=$(cd ../.. && pwd)
sed -i.bak "s|/path/to/your/project/skills|${PROJECT_ROOT}/skills|g" skills-pv-pvc.yaml

kubectl apply -f namespace.yaml
kubectl apply -f skills-pv-pvc.yaml
kubectl apply -f headless-service.yaml

# 3. Configure backend
cat >> ../../backend/config.yaml << EOF
sandbox:
  use: src.community.aio_sandbox:KubernetesSandboxProvider
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  k8s_namespace: deer-flow
  ttl_seconds: 3600
EOF

# 4. Install dependencies and start
cd ../../backend
pip install -e .
make dev

# 5. Test (in another terminal)
cd docker/k8s
./test-concurrent.sh
```

## Setup Script Options

```bash
# Show help
./setup.sh --help

# Run setup (interactive)
./setup.sh

# Skip backend configuration prompt
./setup.sh --skip-config

# Cleanup all Kubernetes resources
./setup.sh --cleanup
```

## Configuration Example

Minimal `backend/config.yaml`:

```yaml
sandbox:
  use: src.community.aio_sandbox:KubernetesSandboxProvider
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  k8s_namespace: deer-flow
  ttl_seconds: 3600
```

With resource limits:

```yaml
sandbox:
  use: src.community.aio_sandbox:KubernetesSandboxProvider
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  k8s_namespace: deer-flow
  ttl_seconds: 3600
  cpu_request: "100m"
  cpu_limit: "1000m"
  memory_request: "256Mi"
  memory_limit: "1Gi"
```

## Verification Commands

```bash
# Check namespace
kubectl get namespace deer-flow

# Check service
kubectl get service -n deer-flow

# Check PVC
kubectl get pvc -n deer-flow

# Watch Pods (run this while testing)
kubectl get pods -n deer-flow -w

# View Pod logs
kubectl logs -n deer-flow deer-flow-sandbox-xxxxx

# Delete all sandbox Pods
kubectl delete pods -n deer-flow -l app=deer-flow-sandbox
```

## Switching Back to Docker

```yaml
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  port: 8080
  auto_start: true
```

## Common Issues

**PVC Pending**: Update path in `skills-pv-pvc.yaml` to your actual project path

**ImagePullBackOff**: Check image name and network connectivity

**Pod not ready**: Check logs with `kubectl logs -n deer-flow <pod-name>`

See [README.md](README.md) for detailed documentation.
