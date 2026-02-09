#!/usr/bin/env bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

# Docker Compose command with project name
COMPOSE_CMD="docker compose -p deer-flow-dev -f docker-compose-dev.yaml"

# Cleanup function for Ctrl+C
cleanup() {
    echo ""
    echo -e "${YELLOW}Operation interrupted by user${NC}"
    exit 130
}

# Set up trap for Ctrl+C
trap cleanup INT TERM

# Initialize Docker containers and install dependencies
init() {
    echo "=========================================="
    echo "  Initializing Docker Development"
    echo "=========================================="
    echo ""

    # Check if pnpm is installed on host
    if ! command -v pnpm >/dev/null 2>&1; then
        echo -e "${YELLOW}✗ pnpm is required but not found on host${NC}"
        echo ""
        echo "Please install pnpm first:"
        echo "  npm install -g pnpm"
        echo "  or visit: https://pnpm.io/installation"
        echo ""
        exit 1
    fi

    # Get pnpm store directory
    echo -e "${BLUE}Detecting pnpm store directory...${NC}"
    PNPM_STORE=$(pnpm store path 2>/dev/null || echo "")

    if [ -z "$PNPM_STORE" ]; then
        echo -e "${YELLOW}✗ Could not detect pnpm store path${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Found pnpm store: $PNPM_STORE${NC}"
    echo -e "${BLUE}  Will share pnpm cache with host${NC}"

    # Export for docker compose
    export PNPM_STORE_PATH="$PNPM_STORE"

    echo ""

    # Build containers
    echo -e "${BLUE}Building containers...${NC}"
    cd "$DOCKER_DIR" && PNPM_STORE_PATH="$PNPM_STORE" $COMPOSE_CMD build

    echo ""

    # Install frontend dependencies
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    if ! (cd "$DOCKER_DIR" && PNPM_STORE_PATH="$PNPM_STORE" $COMPOSE_CMD run --rm -it --entrypoint "" web pnpm install --frozen-lockfile); then
        echo -e "${YELLOW}Frontend dependencies installation failed or was interrupted${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

    echo ""

    # Install backend dependencies
    echo -e "${BLUE}Installing backend dependencies...${NC}"
    if ! (cd "$DOCKER_DIR" && $COMPOSE_CMD run --rm -it --entrypoint "" api uv sync); then
        echo -e "${YELLOW}Backend dependencies installation failed or was interrupted${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"

    echo ""

    echo "=========================================="
    echo -e "${GREEN}  ✓ Docker initialization complete!${NC}"
    echo "=========================================="
    echo ""
    echo "You can now run: make docker-dev"
    echo ""
}

# Start Docker development environment
start() {
    echo "=========================================="
    echo "  Starting DeerFlow Docker Development"
    echo "=========================================="
    echo ""
    echo "Building and starting containers..."
    cd "$DOCKER_DIR" && $COMPOSE_CMD up --build -d --remove-orphans
    echo ""
    echo "=========================================="
    echo "  DeerFlow Docker is starting!"
    echo "=========================================="
    echo ""
    echo "  🌐 Application: http://localhost:2026"
    echo "  📡 API Gateway: http://localhost:2026/api/*"
    echo "  🤖 LangGraph:   http://localhost:2026/api/langgraph/*"
    echo ""
    echo "  📋 View logs: make docker-dev-logs"
    echo "  🛑 Stop:      make docker-dev-stop"
    echo ""
}

# View Docker development logs
logs() {
    local service=""
    
    case "$1" in
        --web)
            service="web"
            echo -e "${BLUE}Viewing frontend logs...${NC}"
            ;;
        --api)
            service="api"
            echo -e "${BLUE}Viewing backend logs...${NC}"
            ;;
        --nginx)
            service="nginx"
            echo -e "${BLUE}Viewing nginx logs...${NC}"
            ;;
        "")
            echo -e "${BLUE}Viewing all logs...${NC}"
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            echo "Usage: $0 logs [--web|--api]"
            exit 1
            ;;
    esac
    
    cd "$DOCKER_DIR" && $COMPOSE_CMD logs -f $service
}

# Stop Docker development environment
stop() {
    echo "Stopping Docker development services..."
    cd "$DOCKER_DIR" && $COMPOSE_CMD down
    echo -e "${GREEN}✓ Docker services stopped${NC}"
}

# Restart Docker development environment
restart() {
    echo "========================================"
    echo "  Restarting DeerFlow Docker Services"
    echo "========================================"
    echo ""
    echo -e "${BLUE}Restarting containers...${NC}"
    cd "$DOCKER_DIR" && $COMPOSE_CMD restart
    echo ""
    echo -e "${GREEN}✓ Docker services restarted${NC}"
    echo ""
    echo "  🌐 Application: http://localhost:2026"
    echo "  📋 View logs: make docker-dev-logs"
    echo ""
}

# Show help
help() {
    echo "DeerFlow Docker Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  init          - Initialize and install dependencies in Docker containers"
    echo "  start         - Start all services in Docker (localhost:2026)"
    echo "  restart       - Restart all running Docker services"
    echo "  logs [option] - View Docker development logs"
    echo "                  --web   View frontend logs only"
    echo "                  --api   View backend logs only"
    echo "  stop          - Stop Docker development services"
    echo "  help          - Show this help message"
    echo ""
}

# Main command dispatcher
case "$1" in
    init)
        init
        ;;
    start)
        start
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$2"
        ;;
    stop)
        stop
        ;;
    help|--help|-h|"")
        help
        ;;
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        echo ""
        help
        exit 1
        ;;
esac
