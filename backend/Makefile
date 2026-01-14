install:
	uv sync

dev:
	uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.12 langgraph dev --no-browser --allow-blocking

lint:
	uvx ruff check .

format:
	uvx ruff check . --fix && uvx ruff format .
