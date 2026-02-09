# Kubernetes Sandbox Setup

This guide explains how to deploy and configure the DeerFlow sandbox execution environment on Kubernetes.

## Overview

The Kubernetes sandbox deployment allows you to run DeerFlow's code execution sandbox in a Kubernetes cluster, providing:

- **Isolated Execution**: Sandbox runs in dedicated Kubernetes pods
- **Scalability**: Easy horizontal scaling with replica configuration
- **Cluster Integration**: Seamless integration with existing Kubernetes infrastructure
- **Persistent Skills**: Skills directory mounted from host or PersistentVolume

## Prerequisites

Before you begin, ensure you have:

1. **Kubernetes Cluster**: One of the following:
   - Docker Desktop with Kubernetes enabled
   - OrbStack with Kubernetes enabled
   - Minikube
   - Any production Kubernetes cluster

2. **kubectl**: Kubernetes command-line tool
   ```bash
   # macOS
   brew install kubectl
   
   # Linux
   # See: https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
   ```

3. **Docker**: For pulling the sandbox image (optional, but recommended)
   ```bash
   # Verify installation
   docker version
   ```

## Quick Start

### 1. Enable Kubernetes

**Docker Desktop:**
```
Settings → Kubernetes → Enable Kubernetes → Apply & Restart
```

**OrbStack:**
```
Settings → Enable Kubernetes
```

**Minikube:**
```bash
minikube start
```

### 2. Run Setup Script

The easiest way to get started:

```bash
cd docker/k8s
./setup.sh
```

This will:
- ✅ Check kubectl installation and cluster connectivity
- ✅ Pull the sandbox Docker image (optional, can be skipped)
- ✅ Create the `deer-flow` namespace
- ✅ Deploy the sandbox service and deployment
- ✅ Verify the deployment is running

### 3. Configure Backend

Add the following to `backend/config.yaml`:

```yaml
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  base_url: http://deer-flow-sandbox.deer-flow.svc.cluster.local:8080
```

### 4. Verify Deployment

Check that the sandbox pod is running:

```bash
kubectl get pods -n deer-flow
```

You should see:
```
NAME                                 READY   STATUS    RESTARTS   AGE
deer-flow-sandbox-xxxxxxxxxx-xxxxx   1/1     Running   0          1m
```

## Advanced Configuration

### Custom Skills Path

By default, the setup script uses `PROJECT_ROOT/skills`. You can specify a custom path:

**Using command-line argument:**
```bash
./setup.sh --skills-path /custom/path/to/skills
```

**Using environment variable:**
```bash
SKILLS_PATH=/custom/path/to/skills ./setup.sh
```

### Custom Sandbox Image

To use a different sandbox image:

**Using command-line argument:**
```bash
./setup.sh --image your-registry/sandbox:tag
```

**Using environment variable:**
```bash
SANDBOX_IMAGE=your-registry/sandbox:tag ./setup.sh
```

### Skip Image Pull

If you already have the image locally or want to pull it manually later:

```bash
./setup.sh --skip-pull
```

### Combined Options

```bash
./setup.sh --skip-pull --skills-path /custom/skills --image custom/sandbox:latest
```

## Manual Deployment

If you prefer manual deployment or need more control:

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create Service

```bash
kubectl apply -f sandbox-service.yaml
```

### 3. Deploy Sandbox

First, update the skills path in `sandbox-deployment.yaml`:

```bash
# Replace __SKILLS_PATH__ with your actual path
sed 's|__SKILLS_PATH__|/Users/feng/Projects/deer-flow/skills|g' \
  sandbox-deployment.yaml | kubectl apply -f -
```

Or manually edit `sandbox-deployment.yaml` and replace `__SKILLS_PATH__` with your skills directory path.

### 4. Verify Deployment

```bash
# Check all resources
kubectl get all -n deer-flow

# Check pod status
kubectl get pods -n deer-flow

# Check pod logs
kubectl logs -n deer-flow -l app=deer-flow-sandbox

# Describe pod for detailed info
kubectl describe pod -n deer-flow -l app=deer-flow-sandbox
```

## Configuration Options

### Resource Limits

Edit `sandbox-deployment.yaml` to adjust resource limits:

```yaml
resources:
  requests:
    cpu: 100m      # Minimum CPU
    memory: 256Mi  # Minimum memory
  limits:
    cpu: 1000m     # Maximum CPU (1 core)
    memory: 1Gi    # Maximum memory
```

### Scaling

Adjust the number of replicas:

```yaml
spec:
  replicas: 3  # Run 3 sandbox pods
```

Or scale dynamically:

```bash
kubectl scale deployment deer-flow-sandbox -n deer-flow --replicas=3
```

### Health Checks

The deployment includes readiness and liveness probes:

- **Readiness Probe**: Checks if the pod is ready to serve traffic
- **Liveness Probe**: Restarts the pod if it becomes unhealthy

Configure in `sandbox-deployment.yaml`:

```yaml
readinessProbe:
  httpGet:
    path: /v1/sandbox
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

## Troubleshooting

### Pod Not Starting

Check pod status and events:

```bash
kubectl describe pod -n deer-flow -l app=deer-flow-sandbox
```

Common issues:
- **ImagePullBackOff**: Docker image cannot be pulled
  - Solution: Pre-pull image with `docker pull <image>`
- **Skills path not found**: HostPath doesn't exist
  - Solution: Verify the skills path exists on the host
- **Resource constraints**: Not enough CPU/memory
  - Solution: Adjust resource requests/limits

### Service Not Accessible

Verify the service is running:

```bash
kubectl get service -n deer-flow
kubectl describe service deer-flow-sandbox -n deer-flow
```

Test connectivity from another pod:

```bash
kubectl run test-pod -n deer-flow --rm -it --image=curlimages/curl -- \
  curl http://deer-flow-sandbox.deer-flow.svc.cluster.local:8080/v1/sandbox
```

### Check Logs

View sandbox logs:

```bash
# Follow logs in real-time
kubectl logs -n deer-flow -l app=deer-flow-sandbox -f

# View logs from previous container (if crashed)
kubectl logs -n deer-flow -l app=deer-flow-sandbox --previous
```

### Health Check Failures

If pods show as not ready:

```bash
# Check readiness probe
kubectl get events -n deer-flow --sort-by='.lastTimestamp'

# Exec into pod to debug
kubectl exec -it -n deer-flow <pod-name> -- /bin/sh
```

## Cleanup

### Remove All Resources

Using the setup script:

```bash
./setup.sh --cleanup
```

Or manually:

```bash
kubectl delete -f sandbox-deployment.yaml
kubectl delete -f sandbox-service.yaml
kubectl delete namespace deer-flow
```

### Remove Specific Resources

```bash
# Delete only the deployment (keeps namespace and service)
kubectl delete deployment deer-flow-sandbox -n deer-flow

# Delete pods (they will be recreated by deployment)
kubectl delete pods -n deer-flow -l app=deer-flow-sandbox
```

## Architecture

```
┌─────────────────────────────────────────────┐
│         DeerFlow Backend                    │
│  (config.yaml: base_url configured)         │
└────────────────┬────────────────────────────┘
                 │ HTTP requests
                 ↓
┌─────────────────────────────────────────────┐
│    Kubernetes Service (ClusterIP)           │
│  deer-flow-sandbox.deer-flow.svc:8080       │
└────────────────┬────────────────────────────┘
                 │ Load balancing
                 ↓
┌─────────────────────────────────────────────┐
│         Sandbox Pods (replicas)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Pod 1   │  │  Pod 2   │  │  Pod 3   │  │
│  │ Port 8080│  │ Port 8080│  │ Port 8080│  │
│  └──────────┘  └──────────┘  └──────────┘  │
└────────────────┬────────────────────────────┘
                 │ Volume mount
                 ↓
┌─────────────────────────────────────────────┐
│         Host Skills Directory               │
│    /path/to/deer-flow/skills                │
└─────────────────────────────────────────────┘
```

## Setup Script Reference

### Command-Line Options

```bash
./setup.sh [options]

Options:
  -h, --help              Show help message
  -c, --cleanup           Remove all Kubernetes resources
  -p, --skip-pull         Skip pulling sandbox image
  --image <image>         Use custom sandbox image
  --skills-path <path>    Custom skills directory path

Environment Variables:
  SANDBOX_IMAGE      Custom sandbox image
  SKILLS_PATH        Custom skills path

Examples:
  ./setup.sh                                    # Use default settings
  ./setup.sh --skills-path /custom/path         # Use custom skills path
  ./setup.sh --skip-pull --image custom:tag     # Custom image, skip pull
  SKILLS_PATH=/custom/path ./setup.sh           # Use env variable
```

## Production Considerations

### Security

1. **Network Policies**: Restrict pod-to-pod communication
2. **RBAC**: Configure appropriate service account permissions
3. **Pod Security**: Enable pod security standards
4. **Image Security**: Scan images for vulnerabilities

### High Availability

1. **Multiple Replicas**: Run at least 3 replicas
2. **Pod Disruption Budget**: Prevent all pods from being evicted
3. **Node Affinity**: Distribute pods across nodes
4. **Resource Quotas**: Set namespace resource limits

### Monitoring

1. **Prometheus**: Scrape metrics from pods
2. **Logging**: Centralized log aggregation
3. **Alerting**: Set up alerts for pod failures
4. **Tracing**: Distributed tracing for requests

### Storage

For production, consider using PersistentVolume instead of hostPath:

1. **Create PersistentVolume**: Define storage backend
2. **Create PersistentVolumeClaim**: Request storage
3. **Update Deployment**: Use PVC instead of hostPath

See `skills-pv-pvc.yaml.bak` for reference implementation.

## Next Steps

After successful deployment:

1. **Start Backend**: `make dev` or `make docker-start`
2. **Test Sandbox**: Create a conversation and execute code
3. **Monitor**: Watch pod logs and resource usage
4. **Scale**: Adjust replicas based on workload

## Support

For issues and questions:

- Check troubleshooting section above
- Review pod logs: `kubectl logs -n deer-flow -l app=deer-flow-sandbox`
- See main project documentation: [../../README.md](../../README.md)
- Report issues on GitHub
