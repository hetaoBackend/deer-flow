install:
	uv sync

dev:
	uv run langgraph dev --no-browser --allow-blocking --no-reload

gateway:
	uv run uvicorn src.gateway.app:app --host 0.0.0.0 --port 8001

nginx:
	nginx -c $(PWD)/../nginx.conf -p $(PWD)/..

serve:
	@echo "Stopping existing services if any..."
	@-pkill -f "langgraph dev" 2>/dev/null || true
	@-pkill -f "uvicorn src.gateway.app:app" 2>/dev/null || true
	@-nginx -c $(PWD)/../nginx.conf -p $(PWD)/.. -s quit 2>/dev/null || true
	@sleep 1
	@echo "Starting services..."
	@trap 'kill 0' EXIT; \
	uv run langgraph dev --no-browser --allow-blocking --no-reload & \
	sleep 3 && uv run uvicorn src.gateway.app:app --host 0.0.0.0 --port 8001 & \
	sleep 1 && nginx -c $(PWD)/../nginx.conf -p $(PWD)/.. & \
	wait

lint:
	uvx ruff check .

format:
	uvx ruff check . --fix && uvx ruff format .
