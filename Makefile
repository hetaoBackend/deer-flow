# DeerFlow - Unified Development Environment

.PHONY: help check install dev stop clean docker-init docker-dev docker-dev-stop docker-dev-logs

help:
	@echo "DeerFlow Development Commands:"
	@echo "  make check          - Check if all required tools are installed"
	@echo "  make install        - Install all dependencies (frontend + backend)"
	@echo "  make dev            - Start all services (frontend + backend + nginx on localhost:2026)"
	@echo "  make stop           - Stop all running services"
	@echo "  make clean          - Clean up processes and temporary files"
	@echo ""
	@echo "Docker Development Commands:"
	@echo "  make docker-init     - Initialize and install dependencies in Docker containers"
	@echo "  make docker-start    - Start all services in Docker (localhost:2026)"
	@echo "  make docker-stop     - Stop Docker development services"
	@echo "  make docker-logs 	  - View Docker development logs"
	@echo "  make docker-logs-web - View Docker frontend logs"
	@echo "  make docker-logs-api - View Docker backend logs"

# Check required tools
check:
	@echo "=========================================="
	@echo "  Checking Required Dependencies"
	@echo "=========================================="
	@echo ""
	@FAILED=0; \
	echo "Checking Node.js..."; \
	if command -v node >/dev/null 2>&1; then \
		NODE_VERSION=$$(node -v | sed 's/v//'); \
		NODE_MAJOR=$$(echo $$NODE_VERSION | cut -d. -f1); \
		if [ $$NODE_MAJOR -ge 22 ]; then \
			echo "  ✓ Node.js $$NODE_VERSION (>= 22 required)"; \
		else \
			echo "  ✗ Node.js $$NODE_VERSION found, but version 22+ is required"; \
			echo "    Install from: https://nodejs.org/"; \
			FAILED=1; \
		fi; \
	else \
		echo "  ✗ Node.js not found (version 22+ required)"; \
		echo "    Install from: https://nodejs.org/"; \
		FAILED=1; \
	fi; \
	echo ""; \
	echo "Checking pnpm..."; \
	if command -v pnpm >/dev/null 2>&1; then \
		PNPM_VERSION=$$(pnpm -v); \
		echo "  ✓ pnpm $$PNPM_VERSION"; \
	else \
		echo "  ✗ pnpm not found"; \
		echo "    Install: npm install -g pnpm"; \
		echo "    Or visit: https://pnpm.io/installation"; \
		FAILED=1; \
	fi; \
	echo ""; \
	echo "Checking uv..."; \
	if command -v uv >/dev/null 2>&1; then \
		UV_VERSION=$$(uv --version | awk '{print $$2}'); \
		echo "  ✓ uv $$UV_VERSION"; \
	else \
		echo "  ✗ uv not found"; \
		echo "    Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo "    Or visit: https://docs.astral.sh/uv/getting-started/installation/"; \
		FAILED=1; \
	fi; \
	echo ""; \
	echo "Checking nginx..."; \
	if command -v nginx >/dev/null 2>&1; then \
		NGINX_VERSION=$$(nginx -v 2>&1 | awk -F'/' '{print $$2}'); \
		echo "  ✓ nginx $$NGINX_VERSION"; \
	else \
		echo "  ✗ nginx not found"; \
		echo "    macOS:   brew install nginx"; \
		echo "    Ubuntu:  sudo apt install nginx"; \
		echo "    Or visit: https://nginx.org/en/download.html"; \
		FAILED=1; \
	fi; \
	echo ""; \
	if [ $$FAILED -eq 0 ]; then \
		echo "=========================================="; \
		echo "  ✓ All dependencies are installed!"; \
		echo "=========================================="; \
		echo ""; \
		echo "You can now run:"; \
		echo "  make install  - Install project dependencies"; \
		echo "  make dev      - Start development server"; \
	else \
		echo "=========================================="; \
		echo "  ✗ Some dependencies are missing"; \
		echo "=========================================="; \
		echo ""; \
		echo "Please install the missing tools and run 'make check' again."; \
		exit 1; \
	fi

# Install all dependencies
install:
	@echo "Installing backend dependencies..."
	@cd backend && uv sync
	@echo "Installing frontend dependencies..."
	@cd frontend && pnpm install
	@echo "✓ All dependencies installed"

# Start all services
dev:
	@echo "Stopping existing services if any..."
	@-pkill -f "langgraph dev" 2>/dev/null || true
	@-pkill -f "uvicorn src.gateway.app:app" 2>/dev/null || true
	@-pkill -f "next dev" 2>/dev/null || true
	@-nginx -c $(PWD)/docker/nginx.local.conf -p $(PWD) -s quit 2>/dev/null || true
	@sleep 1
	@-pkill -9 nginx 2>/dev/null || true
	@sleep 1
	@echo ""
	@echo "=========================================="
	@echo "  Starting DeerFlow Development Server"
	@echo "=========================================="
	@echo ""
	@echo "Services starting up..."
	@echo "  → Backend: LangGraph + Gateway"
	@echo "  → Frontend: Next.js"
	@echo "  → Nginx: Reverse Proxy"
	@echo ""
	@cleanup() { \
		echo ""; \
		echo "Shutting down services..."; \
		pkill -f "langgraph dev" 2>/dev/null || true; \
		pkill -f "uvicorn src.gateway.app:app" 2>/dev/null || true; \
		pkill -f "next dev" 2>/dev/null || true; \
		nginx -c $(PWD)/docker/nginx.local.conf -p $(PWD) -s quit 2>/dev/null || true; \
		sleep 1; \
		pkill -9 nginx 2>/dev/null || true; \
		echo "✓ All services stopped"; \
		exit 0; \
	}; \
	trap cleanup INT TERM; \
	echo "Starting LangGraph server..."; \
	cd backend && uv run langgraph dev --no-browser --allow-blocking --no-reload > ../logs/langgraph.log 2>&1 & \
	sleep 3; \
	echo "✓ LangGraph server started on localhost:2024"; \
	echo "Starting Gateway API..."; \
	cd backend && uv run uvicorn src.gateway.app:app --host 0.0.0.0 --port 8001 > ../logs/gateway.log 2>&1 & \
	sleep 2; \
	echo "✓ Gateway API started on localhost:8001"; \
	echo "Starting Frontend..."; \
	cd frontend && pnpm run dev > ../logs/frontend.log 2>&1 & \
	sleep 3; \
	echo "✓ Frontend started on localhost:3000"; \
	echo "Starting Nginx reverse proxy..."; \
	mkdir -p logs && nginx -g 'daemon off;' -c $(PWD)/docker/nginx.local.conf -p $(PWD) > logs/nginx.log 2>&1 & \
	sleep 2; \
	echo "✓ Nginx started on localhost:2026"; \
	echo ""; \
	echo "=========================================="; \
	echo "  DeerFlow is ready!"; \
	echo "=========================================="; \
	echo ""; \
	echo "  🌐 Application: http://localhost:2026"; \
	echo "  📡 API Gateway: http://localhost:2026/api/*"; \
	echo "  🤖 LangGraph:   http://localhost:2026/api/langgraph/*"; \
	echo ""; \
	echo "  📋 Logs:"; \
	echo "     - LangGraph: logs/langgraph.log"; \
	echo "     - Gateway:   logs/gateway.log"; \
	echo "     - Frontend:  logs/frontend.log"; \
	echo "     - Nginx:     logs/nginx.log"; \
	echo ""; \
	echo "Press Ctrl+C to stop all services"; \
	echo ""; \
	wait

# Stop all services
stop:
	@echo "Stopping all services..."
	@-pkill -f "langgraph dev" 2>/dev/null || true
	@-pkill -f "uvicorn src.gateway.app:app" 2>/dev/null || true
	@-pkill -f "next dev" 2>/dev/null || true
	@-nginx -c $(PWD)/docker/nginx.local.conf -p $(PWD) -s quit 2>/dev/null || true
	@sleep 1
	@-pkill -9 nginx 2>/dev/null || true
	@echo "✓ All services stopped"

# Clean up
clean: stop
	@echo "Cleaning up..."
	@-rm -rf logs/*.log 2>/dev/null || true
	@echo "✓ Cleanup complete"

# ==========================================
# Docker Development Commands
# ==========================================

# Initialize Docker containers and install dependencies
docker-init:
	@./scripts/docker.sh init

# Start Docker development environment
docker-start:
	@./scripts/docker.sh start

# Stop Docker development environment
docker-stop:
	@./scripts/docker.sh stop

# View Docker development logs
docker-logs:
	@./scripts/docker.sh logs

# View Docker development logs
docker-logs-web:
	@./scripts/docker.sh logs --web
docker-logs-api:
	@./scripts/docker.sh logs --api