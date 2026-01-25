#!/bin/bash

# Kubernetes Sandbox Initialization Script for Deer-Flow
# This script sets up the Kubernetes environment for the sandbox provider

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default sandbox image
DEFAULT_SANDBOX_IMAGE="enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Deer-Flow Kubernetes Sandbox Setup       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo

# Function to print status messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is installed
check_kubectl() {
    info "Checking kubectl installation..."
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed. Please install kubectl first."
        echo "  - macOS: brew install kubectl"
        echo "  - Linux: https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/"
        exit 1
    fi
    success "kubectl is installed"
}

# Check if Kubernetes cluster is accessible
check_cluster() {
    info "Checking Kubernetes cluster connection..."
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster."
        echo "Please ensure:"
        echo "  - Docker Desktop: Settings → Kubernetes → Enable Kubernetes"
        echo "  - Or OrbStack: Enable Kubernetes in settings"
        echo "  - Or Minikube: minikube start"
        exit 1
    fi
    success "Connected to Kubernetes cluster"
}

# Update skills path in PV/PVC configuration
update_skills_path() {
    info "Updating skills path in skills-pv-pvc.yaml..."
    
    SKILLS_PATH="${PROJECT_ROOT}/skills"
    PVC_FILE="${SCRIPT_DIR}/skills-pv-pvc.yaml"
    
    if [[ ! -f "$PVC_FILE" ]]; then
        error "skills-pv-pvc.yaml not found at ${PVC_FILE}"
        exit 1
    fi
    
    # Create backup
    cp "$PVC_FILE" "${PVC_FILE}.bak"
    
    # Update the path
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|__DEER_FLOW_SKILLS_PATH__|${SKILLS_PATH}|g" "$PVC_FILE"
    else
        # Linux
        sed -i "s|__DEER_FLOW_SKILLS_PATH__|${SKILLS_PATH}|g" "$PVC_FILE"
    fi
    
    success "Updated skills path to: ${SKILLS_PATH}"
}

# Apply Kubernetes resources
apply_resources() {
    info "Applying Kubernetes resources..."
    
    echo "  → Creating namespace..."
    kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"
    
    echo "  → Creating PersistentVolume and PersistentVolumeClaim..."
    kubectl apply -f "${SCRIPT_DIR}/skills-pv-pvc.yaml"
    
    echo "  → Creating headless service..."
    kubectl apply -f "${SCRIPT_DIR}/headless-service.yaml"
    
    success "All Kubernetes resources applied"
}

# Verify deployment
verify_deployment() {
    info "Verifying deployment..."
    
    echo "  → Checking namespace..."
    kubectl get namespace deer-flow
    
    echo "  → Checking service..."
    kubectl get service -n deer-flow
    
    echo "  → Checking PVC..."
    kubectl get pvc -n deer-flow
    
    success "Deployment verified"
}

# Pull sandbox image
pull_image() {
    info "Checking sandbox image..."
    
    IMAGE="${SANDBOX_IMAGE:-$DEFAULT_SANDBOX_IMAGE}"
    
    # Check if image already exists locally
    if docker image inspect "$IMAGE" &> /dev/null; then
        success "Image already exists locally: $IMAGE"
        return 0
    fi
    
    info "Pulling sandbox image (this may take a few minutes on first run)..."
    echo "  → Image: $IMAGE"
    echo
    
    if docker pull "$IMAGE"; then
        success "Image pulled successfully"
    else
        warn "Failed to pull image. Pod startup may be slow on first run."
        echo "  You can manually pull the image later with:"
        echo "    docker pull $IMAGE"
    fi
}

# Configure backend
configure_backend() {
    info "Checking backend configuration..."
    
    BACKEND_CONFIG="${PROJECT_ROOT}/backend/config.yaml"
    
    if [[ ! -f "$BACKEND_CONFIG" ]]; then
        warn "Backend config.yaml not found. Creating from example..."
        if [[ -f "${PROJECT_ROOT}/config.example.yaml" ]]; then
            cp "${PROJECT_ROOT}/config.example.yaml" "$BACKEND_CONFIG"
        fi
    fi
    
    # Check if sandbox config already exists
    if grep -q "KubernetesSandboxProvider" "$BACKEND_CONFIG" 2>/dev/null; then
        success "Kubernetes sandbox already configured in backend/config.yaml"
        return
    fi
    
    echo
    echo -e "${YELLOW}To enable Kubernetes sandbox, add the following to backend/config.yaml:${NC}"
    echo
    echo -e "${GREEN}sandbox:${NC}"
    echo -e "${GREEN}  use: src.community.aio_sandbox:KubernetesSandboxProvider${NC}"
    echo -e "${GREEN}  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest${NC}"
    echo -e "${GREEN}  k8s_namespace: deer-flow${NC}"
    echo -e "${GREEN}  ttl_seconds: 3600${NC}"
    echo
    
    read -p "Would you like to automatically append this configuration? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat >> "$BACKEND_CONFIG" << EOF

# Kubernetes Sandbox Configuration (added by init.sh)
sandbox:
  use: src.community.aio_sandbox:KubernetesSandboxProvider
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  k8s_namespace: deer-flow
  ttl_seconds: 3600
EOF
        success "Backend configuration updated"
    else
        warn "Skipped backend configuration. Please configure manually."
    fi
}

# Print next steps
print_next_steps() {
    echo
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Setup Complete!                          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Start the backend:"
    echo "     cd ${PROJECT_ROOT}/backend"
    echo "     pip install -e ."
    echo "     make dev"
    echo
    echo "  2. Test the setup (in another terminal):"
    echo "     cd ${SCRIPT_DIR}"
    echo "     ./test-concurrent.sh"
    echo
    echo -e "${GREEN}Useful commands:${NC}"
    echo "  • Watch pods:    kubectl get pods -n deer-flow -w"
    echo "  • View logs:     kubectl logs -n deer-flow <pod-name>"
    echo "  • Delete pods:   kubectl delete pods -n deer-flow -l app=deer-flow-sandbox"
    echo
}

# Cleanup function
cleanup() {
    if [[ "$1" == "--cleanup" ]] || [[ "$1" == "-c" ]]; then
        info "Cleaning up Kubernetes resources..."
        kubectl delete pods -n deer-flow -l app=deer-flow-sandbox --ignore-not-found=true
        kubectl delete -f "${SCRIPT_DIR}/headless-service.yaml" --ignore-not-found=true
        kubectl delete -f "${SCRIPT_DIR}/skills-pv-pvc.yaml" --ignore-not-found=true
        kubectl delete -f "${SCRIPT_DIR}/namespace.yaml" --ignore-not-found=true
        success "Cleanup complete"
        exit 0
    fi
}

# Show help
show_help() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -h, --help         Show this help message"
    echo "  -c, --cleanup      Remove all Kubernetes resources"
    echo "  -s, --skip-config  Skip backend configuration step"
    echo "  -p, --skip-pull    Skip pulling sandbox image"
    echo "  --image <image>    Use custom sandbox image"
    echo
    echo "Environment variables:"
    echo "  SANDBOX_IMAGE      Custom sandbox image (default: $DEFAULT_SANDBOX_IMAGE)"
    echo
    exit 0
}

# Parse arguments
SKIP_CONFIG=false
SKIP_PULL=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -c|--cleanup)
            cleanup "$1"
            ;;
        -s|--skip-config)
            SKIP_CONFIG=true
            shift
            ;;
        -p|--skip-pull)
            SKIP_PULL=true
            shift
            ;;
        --image)
            SANDBOX_IMAGE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Main execution
main() {
    check_kubectl
    check_cluster
    
    # Pull image first to avoid Pod startup timeout
    if [[ "$SKIP_PULL" == false ]]; then
        pull_image
    fi
    
    update_skills_path
    apply_resources
    verify_deployment
    
    if [[ "$SKIP_CONFIG" == false ]]; then
        configure_backend
    fi
    
    print_next_steps
}

main
