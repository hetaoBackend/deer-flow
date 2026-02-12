# 🦌 DeerFlow - v2

> Originated from Open Source, give back to Open Source.

A LangGraph-based AI agent backend with sandbox execution capabilities.

## Quick Start

### Configuration

1. **Copy the example config**:
   ```bash
   cp config.example.yaml config.yaml
   cp .env.example .env
   ```

2. **Edit `config.yaml`** and set your API keys in `.env` and preferred sandbox mode.

#### Sandbox Configuration

DeerFlow supports multiple sandbox execution modes. Configure your preferred mode in `config.yaml`:

**Local Execution** (runs sandbox code directly on the host machine):
```yaml
sandbox:
   use: src.sandbox.local:LocalSandboxProvider # Local execution
```

**Docker Execution** (runs sandbox code in isolated Docker containers):
```yaml
sandbox:
   use: src.community.aio_sandbox:AioSandboxProvider # Docker-based sandbox
```

**Docker Execution with Kubernetes** (runs sandbox code in Kubernetes pods via provisioner service):

This mode runs each sandbox in an isolated Kubernetes Pod on your **host machine's cluster**. Requires Docker Desktop K8s, OrbStack, or similar local K8s setup.

```yaml
sandbox:
   use: src.community.aio_sandbox:AioSandboxProvider
   provisioner_url: http://provisioner:8002
```

See [Provisioner Setup Guide](docker/provisioner/README.md) for detailed configuration, prerequisites, and troubleshooting.

### Running the Application

#### Option 1: Docker (Recommended)

The fastest way to get started with a consistent environment:

1. **Initialize and start**:
   ```bash
   make docker-init    # Pull sandbox image (Only once or when image updates)
   make docker-start   # Start all services and watch for code changes
   ```

2. **Access**: http://localhost:2026

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed Docker development guide.

#### Option 2: Local Development

If you prefer running services locally:

1. **Check prerequisites**:
   ```bash
   make check  # Verifies Node.js 22+, pnpm, uv, nginx
   ```

2. **(Optional) Pre-pull sandbox image**:
   ```bash
   # Recommended if using Docker/Container-based sandbox
   make setup-sandbox
   ```

3. **Start services**:
   ```bash
   make dev
   ```

4. **Access**: http://localhost:2026

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed local development guide.


## Features

- 🤖 **LangGraph-based Agents** - Multi-agent orchestration with sophisticated workflows
- 🧠 **Persistent Memory** - LLM-powered context retention across conversations with automatic fact extraction
- 🔧 **Model Context Protocol (MCP)** - Extensible tool integration
- 🎯 **Skills System** - Reusable agent capabilities
- 🛡️ **Sandbox Execution** - Safe code execution environment
- 🌐 **Unified API Gateway** - Single entry point with nginx reverse proxy
- 🔄 **Hot Reload** - Fast development iteration
- 📊 **Real-time Streaming** - Server-Sent Events (SSE) support

## Documentation

- [Contributing Guide](CONTRIBUTING.md) - Development environment setup and workflow
- [Configuration Guide](backend/docs/CONFIGURATION.md) - Setup and configuration instructions
- [Architecture Overview](backend/CLAUDE.md) - Technical architecture details
- [Backend Architecture](backend/README.md) - Backend architecture and API reference

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, workflow, and guidelines.

## License

This project is open source and available under the [MIT License](./LICENSE).

## Acknowledgments

DeerFlow is built upon the incredible work of the open-source community. We are deeply grateful to all the projects and contributors whose efforts have made DeerFlow possible. Truly, we stand on the shoulders of giants.

We would like to extend our sincere appreciation to the following projects for their invaluable contributions:

- **[LangChain](https://github.com/langchain-ai/langchain)**: Their exceptional framework powers our LLM interactions and chains, enabling seamless integration and functionality.
- **[LangGraph](https://github.com/langchain-ai/langgraph)**: Their innovative approach to multi-agent orchestration has been instrumental in enabling DeerFlow's sophisticated workflows.

These projects exemplify the transformative power of open-source collaboration, and we are proud to build upon their foundations.

### Key Contributors

A heartfelt thank you goes out to the core authors of `DeerFlow`, whose vision, passion, and dedication have brought this project to life:

- **[Daniel Walnut](https://github.com/hetaoBackend/)**
- **[Henry Li](https://github.com/magiccube/)**

Your unwavering commitment and expertise have been the driving force behind DeerFlow's success. We are honored to have you at the helm of this journey.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=bytedance/deer-flow&type=Date)](https://star-history.com/#bytedance/deer-flow&Date)
