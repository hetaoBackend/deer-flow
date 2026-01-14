# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeerFlow is a LangGraph-based AI agent backend that provides a "super agent" with sandbox execution capabilities. The agent can execute code, browse the web, and manage files in isolated sandbox environments.

## Commands

```bash
# Install dependencies
make install

# Run development server (LangGraph Studio)
make dev

# Lint
make lint

# Format code
make format
```

## Architecture

### Configuration System

The app uses a YAML-based configuration system loaded from `config.yaml`. Configuration priority:
1. Explicit `config_path` argument
2. `DEER_FLOW_CONFIG_PATH` environment variable
3. `config.yaml` in current directory
4. `config.yaml` in parent directory

Config values starting with `$` are resolved as environment variables (e.g., `$OPENAI_API_KEY`).

### Core Components

**Agent Graph** (`src/agents/`)
- `lead_agent` is the main entry point registered in `langgraph.json`
- Uses `ThreadState` which extends `AgentState` with sandbox state
- Agent is created via `create_agent()` with model, tools, middleware, and system prompt

**Sandbox System** (`src/sandbox/`)
- Abstract `Sandbox` base class defines interface: `execute_command`, `read_file`, `write_file`, `list_dir`
- `SandboxProvider` manages sandbox lifecycle: `acquire`, `get`, `release`
- `SandboxMiddleware` automatically acquires sandbox on agent start and injects into state
- `LocalSandboxProvider` is a singleton implementation for local execution
- Sandbox tools (`bash`, `ls`, `read_file`, `write_file`, `str_replace`) extract sandbox from tool runtime

**Model Factory** (`src/models/`)
- `create_chat_model()` instantiates LLM from config using reflection
- Supports `thinking_enabled` flag with per-model `when_thinking_enabled` overrides

**Tool System** (`src/tools/`)
- Tools defined in config with `use` path (e.g., `src.sandbox.tools:bash_tool`)
- `get_available_tools()` resolves tool paths via reflection
- Community tools in `src/community/`: Jina AI (web fetch), Tavily (web search)

**Reflection System** (`src/reflection/`)
- `resolve_variable()` imports module and returns variable (e.g., `module:variable`)
- `resolve_class()` imports and validates class against base class

### Config Schema

Models, tools, and sandbox providers are configured in `config.yaml`:
- `models[]`: LLM configurations with `use` class path
- `tools[]`: Tool configurations with `use` variable path and `group`
- `sandbox.use`: Sandbox provider class path

## Code Style

- Uses `ruff` for linting and formatting
- Line length: 240 characters
- Python 3.12+ with type hints
- Double quotes, space indentation
