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

# Apply Kubernetes resources
apply_resources() {
    info "Applying Kubernetes resources..."
    
    # Determine skills path
    SKILLS_PATH="${SKILLS_PATH:-${PROJECT_ROOT}/skills}"
    info "Using skills path: ${SKILLS_PATH}"
    
    # Validate skills path exists
    if [[ ! -d "${SKILLS_PATH}" ]]; then
        warn "Skills path does not exist: ${SKILLS_PATH}"
        warn "Creating directory..."
        mkdir -p "${SKILLS_PATH}"
    fi
    
    echo "  → Creating namespace..."
    kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"
    
    echo "  → Creating sandbox service..."
    kubectl apply -f "${SCRIPT_DIR}/sandbox-service.yaml"
    
    echo "  → Creating sandbox deployment with skills path: ${SKILLS_PATH}"
    # Replace __SKILLS_PATH__ placeholder with actual path
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed "s|__SKILLS_PATH__|${SKILLS_PATH}|g" "${SCRIPT_DIR}/sandbox-deployment.yaml" | kubectl apply -f -
    else
        # Linux
        sed "s|__SKILLS_PATH__|${SKILLS_PATH}|g" "${SCRIPT_DIR}/sandbox-deployment.yaml" | kubectl apply -f -
    fi
    
    success "All Kubernetes resources applied"
}

# Verify deployment
verify_deployment() {
    info "Verifying deployment..."
    
    echo "  → Checking namespace..."
    kubectl get namespace deer-flow
    
    echo "  → Checking service..."
    kubectl get service -n deer-flow
    
    echo "  → Checking statefulset..."
    kubectl get statefulset -n deer-flow
    
    echo "  → Checking pods..."
    kubectl get pods -n deer-flow
    
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

# Print next steps
print_next_steps() {
    echo
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Setup Complete!                          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${YELLOW}To enable Kubernetes sandbox, add the following to backend/config.yaml:${NC}"
    echo
    echo -e "${GREEN}sandbox:${NC}"
    echo -e "${GREEN}  use: src.community.aio_sandbox:AioSandboxProvider${NC}"
    echo -e "${GREEN}  base_url: http://deer-flow-sandbox-{pod_index}.deer-flow-sandbox.deer-flow.svc.cluster.local:8080${NC}"
    echo -e "${GREEN}  replicas: 1  # Match the replicas count in sandbox-deployment.yaml${NC}"
    echo
    echo
    echo -e "${GREEN}Next steps:${NC}"
    echo "  make dev                # Start backend and frontend in development mode"
    echo "  make docker-start       # Start backend and frontend in Docker containers"
    echo
}

# Cleanup function
cleanup() {
    if [[ "$1" == "--cleanup" ]] || [[ "$1" == "-c" ]]; then
        info "Cleaning up Kubernetes resources..."
        kubectl delete -f "${SCRIPT_DIR}/sandbox-deployment.yaml" --ignore-not-found=true
        kubectl delete -f "${SCRIPT_DIR}/sandbox-service.yaml" --ignore-not-found=true
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
    echo "  -h, --help              Show this help message"
    echo "  -c, --cleanup           Remove all Kubernetes resources"
    echo "  -p, --skip-pull         Skip pulling sandbox image"
    echo "  --image <image>         Use custom sandbox image"
    echo "  --skills-path <path>    Custom skills directory path"
    echo
    echo "Environment variables:"
    echo "  SANDBOX_IMAGE      Custom sandbox image (default: $DEFAULT_SANDBOX_IMAGE)"
    echo "  SKILLS_PATH        Custom skills path (default: PROJECT_ROOT/skills)"
    echo
    echo "Examples:"
    echo "  $0                                    # Use default settings"
    echo "  $0 --skills-path /custom/path         # Use custom skills path"
    echo "  SKILLS_PATH=/custom/path $0           # Use env variable"
    echo
    exit 0
}

# Parse arguments
SKIP_PULL=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -c|--cleanup)
            cleanup "$1"
            ;;
        -p|--skip-pull)
            SKIP_PULL=true
            shift
            ;;
        --image)
            SANDBOX_IMAGE="$2"
            shift 2
            ;;
        --skills-path)
            SKILLS_PATH="$2"
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
    
    apply_resources
    verify_deployment
    print_next_steps
}

main
