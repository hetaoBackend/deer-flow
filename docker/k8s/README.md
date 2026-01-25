# Kubernetes Sandbox Deployment Guide

This guide explains how to deploy the deer-flow sandbox system on Kubernetes for multi-instance concurrent support.

## Architecture Overview

The Kubernetes-based sandbox replaces the single Docker container approach with dynamic Pod management:

- **Pods**: Created on-demand per sandbox acquisition (one Pod per thread)
- **Networking**: Headless Service for DNS-based Pod access (no port conflicts)
- **Storage**: 
  - hostPath volumes for thread-specific data (`.deer-flow/threads/{thread-id}/user-data/`)
  - Shared ReadOnlyMany PV for skills directory
- **Cleanup**: TTL-based background cleanup (default 1 hour after release)

## Prerequisites

### 1. Kubernetes Cluster

Choose one of the following options:

**Option A: Docker Desktop or OrbStack (Recommended for macOS/Windows)**
```bash
# Enable Kubernetes in Docker Desktop or OrbStack settings
# Docker Desktop: Settings → Kubernetes → Enable Kubernetes
# OrbStack: Settings → Kubernetes → Enable Kubernetes
```

**Option B: Minikube**
```bash
# Install Minikube
brew install minikube  # macOS
# or visit: https://minikube.sigs.k8s.io/docs/start/

# Start cluster
minikube start --driver=docker

# Verify
kubectl cluster-info
```

**Option C: Kind (Kubernetes in Docker)**
```bash
brew install kind  # macOS
kind create cluster --name deer-flow

# Verify
kubectl cluster-info --context kind-deer-flow
```

### 2. kubectl CLI

```bash
# Install kubectl (if not already installed)
brew install kubectl  # macOS

# Verify installation
kubectl version --client
```

### 3. Verify Cluster Access

```bash
kubectl get nodes
# Should show at least one node in Ready status
```

## Deployment Steps

### Option A: Automated Setup (Recommended)

The easiest way to get started:

```bash
cd docker/k8s
./setup.sh
```

The script automatically handles:
- Path configuration in `skills-pv-pvc.yaml` (replaces `__DEER_FLOW_SKILLS_PATH__` placeholder)
- Kubernetes resource deployment
- Backend configuration prompts
- Image pulling

For other options, see [QUICKSTART.md](QUICKSTART.md).

### Option B: Manual Setup

If you prefer manual control:

#### Step 1: Configure Skills Path

The `setup.sh` script automatically replaces the `__DEER_FLOW_SKILLS_PATH__` placeholder in `skills-pv-pvc.yaml`. 

For manual setup, run just the path update:

```bash
cd docker/k8s

# Auto-detect and update path
PROJECT_ROOT=$(cd ../.. && pwd)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|__DEER_FLOW_SKILLS_PATH__|${PROJECT_ROOT}/skills|g" skills-pv-pvc.yaml
else
    sed -i "s|__DEER_FLOW_SKILLS_PATH__|${PROJECT_ROOT}/skills|g" skills-pv-pvc.yaml
fi
```

#### Step 2: Apply Kubernetes Resources

```bash
# Apply in order
kubectl apply -f namespace.yaml
kubectl apply -f skills-pv-pvc.yaml
kubectl apply -f headless-service.yaml

# Verify resources
kubectl get namespace deer-flow
kubectl get pv deer-flow-skills-pv
kubectl get pvc -n deer-flow
kubectl get service -n deer-flow
```

Expected output:
```
namespace/deer-flow created
persistentvolume/deer-flow-skills-pv created
persistentvolumeclaim/deer-flow-skills-pvc created
service/deer-flow-sandbox created
```

#### Step 3: Update Backend Configuration

Edit `backend/config.yaml` to use the Kubernetes provider:

```yaml
sandbox:
  # Switch to Kubernetes provider
  use: src.community.aio_sandbox:KubernetesSandboxProvider
  
  # Container image (required)
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  
  # Kubernetes configuration
  k8s_namespace: deer-flow      # Namespace for sandbox Pods
  # k8s_context: docker-desktop  # Optional: specify kubeconfig context
  ttl_seconds: 3600              # Pod cleanup TTL (1 hour)
  
  # Optional: Resource limits
  # cpu_request: "100m"
  # cpu_limit: "1000m"
  # memory_request: "256Mi"
  # memory_limit: "1Gi"
  
  # Environment variables (optional)
  # environment:
  #   NODE_ENV: production
  #   API_KEY: $MY_API_KEY
```

#### Step 4: Install Dependencies

```bash
cd backend

# Install/update Python dependencies (includes kubernetes>=30.0.0)
pip install -e .
# or
uv sync
```

#### Step 5: Start the Backend

```bash
cd backend

# Start the server
make dev
# or
langgraph dev
```

## Verification

### 1. Check Namespace and Service

```bash
kubectl get all -n deer-flow
```

Expected: Headless service should be listed, no Pods yet.

### 2. Test Sandbox Creation

Trigger a sandbox acquisition (e.g., by using a tool that requires sandbox):

```bash
# Watch Pods being created
kubectl get pods -n deer-flow -w
```

You should see Pods like `deer-flow-sandbox-{id}` appearing and transitioning to Running.

### 3. Check Pod Details

```bash
# List Pods
kubectl get pods -n deer-flow

# Describe a Pod
kubectl describe pod deer-flow-sandbox-xxxxx -n deer-flow

# Check logs
kubectl logs deer-flow-sandbox-xxxxx -n deer-flow

# Verify mounts
kubectl exec deer-flow-sandbox-xxxxx -n deer-flow -- ls -la /mnt/user-data/
kubectl exec deer-flow-sandbox-xxxxx -n deer-flow -- ls -la /mnt/skills/
```

### 4. Test DNS Resolution

```bash
# From within a Pod, test DNS
kubectl run test-dns --image=busybox --rm -it --restart=Never -n deer-flow -- \
  nslookup deer-flow-sandbox-xxxxx.deer-flow-sandbox.deer-flow.svc.cluster.local
```

### 5. Test Concurrent Access

Run the test script:

```bash
# From project root
bash docker/k8s/test-concurrent.sh
```

This will create multiple sandboxes concurrently and verify they are isolated.

## Configuration Reference

### Kubernetes Provider Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `use` | string | - | Provider class path (required) |
| `image` | string | See default | Container image for sandbox |
| `k8s_namespace` | string | `deer-flow` | Kubernetes namespace |
| `k8s_context` | string | None | Kubeconfig context (optional) |
| `ttl_seconds` | int | `3600` | Pod cleanup TTL after release |
| `cpu_request` | string | None | CPU request (e.g., `100m`) |
| `cpu_limit` | string | None | CPU limit (e.g., `1000m`) |
| `memory_request` | string | None | Memory request (e.g., `256Mi`) |
| `memory_limit` | string | None | Memory limit (e.g., `1Gi`) |
| `environment` | dict | `{}` | Environment variables |

### Resource Limits Guidelines

Based on workload, adjust resource limits:

**Light workload** (development):
```yaml
cpu_request: "100m"
cpu_limit: "500m"
memory_request: "128Mi"
memory_limit: "512Mi"
```

**Medium workload** (testing):
```yaml
cpu_request: "250m"
cpu_limit: "1000m"
memory_request: "256Mi"
memory_limit: "1Gi"
```

**Heavy workload** (production):
```yaml
cpu_request: "500m"
cpu_limit: "2000m"
memory_request: "512Mi"
memory_limit: "2Gi"
```

## Troubleshooting

### Issue: PV Not Binding

**Symptom**: PVC status is `Pending`

```bash
kubectl get pvc -n deer-flow
# deer-flow-skills-pvc   Pending   deer-flow-skills   0s
```

**Solution**: Verify path was correctly configured by setup.sh

```bash
# Check if placeholder was replaced
grep -n "__DEER_FLOW_SKILLS_PATH__" skills-pv-pvc.yaml
# Should return nothing if properly configured

# Check actual path in YAML
grep "path:" skills-pv-pvc.yaml

# Verify skills directory exists
ls -la /Users/feng/Projects/deer-flow/skills

# Check PV status
kubectl describe pv deer-flow-skills-pv

# Re-run setup if path is wrong:
./setup.sh --skip-config
```

### Issue: Pod ImagePullBackOff

**Symptom**: Pod stuck in `ImagePullBackOff` or `ErrImagePull`

```bash
kubectl get pods -n deer-flow
# NAME                        READY   STATUS             RESTARTS   AGE
# deer-flow-sandbox-xxxxx    0/1     ImagePullBackOff   0          30s
```

**Solution**: Check image availability and pull policy

```bash
# Describe Pod to see error
kubectl describe pod deer-flow-sandbox-xxxxx -n deer-flow

# If image is private, configure imagePullSecrets
# Or use a public/local image for testing
```

### Issue: Pod CrashLoopBackOff

**Symptom**: Pod keeps restarting

```bash
kubectl get pods -n deer-flow
# NAME                        READY   STATUS             RESTARTS   AGE
# deer-flow-sandbox-xxxxx    0/1     CrashLoopBackOff   5          2m
```

**Solution**: Check Pod logs

```bash
# View logs
kubectl logs deer-flow-sandbox-xxxxx -n deer-flow

# Check previous container logs
kubectl logs deer-flow-sandbox-xxxxx -n deer-flow --previous

# Common causes:
# - Missing volume mounts (thread directories not created)
# - Image CMD/ENTRYPOINT issues
# - Container startup failures
```

### Issue: Cannot Connect to Pod

**Symptom**: Sandbox acquisition times out waiting for Pod ready

**Solution**: Verify network and readiness probe

```bash
# Check Pod events
kubectl describe pod deer-flow-sandbox-xxxxx -n deer-flow

# Test readiness endpoint manually
kubectl port-forward deer-flow-sandbox-xxxxx -n deer-flow 8080:8080
curl http://localhost:8080/v1/sandbox

# If DNS not working, check service
kubectl get endpoints -n deer-flow
# Should show Pod IPs listed under deer-flow-sandbox service
```

### Issue: Pods Not Cleaning Up

**Symptom**: Old Pods remain after TTL expires

**Solution**: Check provider logs and cleanup worker

```bash
# Check backend logs for cleanup worker messages
# Look for: "Started TTL cleanup worker" and "Cleaned up X expired Pod(s)"

# Manually delete Pods if needed
kubectl delete pod deer-flow-sandbox-xxxxx -n deer-flow

# Or delete all sandbox Pods
kubectl delete pods -n deer-flow -l app=deer-flow-sandbox
```

### Issue: hostPath Mount Permissions

**Symptom**: Pod cannot write to mounted directories

**Solution**: Check directory permissions

```bash
# Verify directory permissions
ls -la .deer-flow/threads/

# Ensure directories are writable
chmod -R 755 .deer-flow/threads/

# Check Pod security context in logs
kubectl describe pod deer-flow-sandbox-xxxxx -n deer-flow
```

## Cleanup

### Remove All Sandbox Pods

```bash
kubectl delete pods -n deer-flow -l app=deer-flow-sandbox
```

### Remove All Resources

```bash
cd docker/k8s
kubectl delete -f headless-service.yaml
kubectl delete -f skills-pv-pvc.yaml
kubectl delete -f namespace.yaml
```

### Stop Cluster (if using Minikube)

```bash
minikube stop
# or
minikube delete
```

## Migration from Docker Provider

To switch back to Docker provider:

```yaml
# config.yaml
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  port: 8080
  auto_start: true
```

Both providers implement the same `SandboxProvider` interface, so no code changes are needed.

## Monitoring

### Watch Pod Creation

```bash
watch kubectl get pods -n deer-flow
```

### Monitor Resource Usage

```bash
kubectl top pods -n deer-flow
```

### View All Events

```bash
kubectl get events -n deer-flow --sort-by='.lastTimestamp'
```

## Advanced Configuration

### Multi-Node Clusters

The current implementation uses `hostPath` which only works on single-node clusters. For multi-node clusters, consider:

1. **Add nodeSelector**: Pin Pods to the node where project root is accessible
2. **Use network storage**: Replace hostPath with NFS/Ceph/Cloud storage
3. **Use local PV**: Configure local persistent volumes on each node

### Custom Security Context

Edit `k8s_sandbox_provider.py` to modify security settings:

```python
security_context=client.V1SecurityContext(
    run_as_non_root=True,
    run_as_user=1000,
    allow_privilege_escalation=False,
    capabilities=client.V1Capabilities(drop=["ALL"])
)
```

## Support

For issues specific to the Kubernetes implementation, check:
- Kubernetes cluster logs: `kubectl logs -n kube-system`
- Provider logs: Check backend console output
- GitHub Issues: Report bugs with `kubectl describe` output

## Next Steps

- Monitor Pod resource usage and adjust limits
- Set up Prometheus/Grafana for metrics
- Configure pod autoscaling (HPA) if needed
- Implement network policies for isolation
- Set up log aggregation (ELK/Loki)
