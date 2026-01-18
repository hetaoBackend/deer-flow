install:
	uv sync

dev:
	uv run langgraph dev --no-browser --allow-blocking --no-reload

gateway:
	uv run uvicorn src.gateway.app:app --host 0.0.0.0 --port 8000

serve:
	@trap 'kill 0' EXIT; \
	uv run langgraph dev --no-browser --allow-blocking --no-reload & \
	sleep 3 && uv run uvicorn src.gateway.app:app --host 0.0.0.0 --port 8000 & \
	wait

lint:
	uvx ruff check .

format:
	uvx ruff check . --fix && uvx ruff format .
