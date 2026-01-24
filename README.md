# 🦌 DeerFlow - v2

> Originated from Open Source, give back to Open Source.

A LangGraph-based AI agent backend with sandbox execution capabilities.

## Quick Start

### Option 1: Docker (Recommended)

The fastest way to get started with a consistent environment:

1. **Configure the application**:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml and set your API keys
   ```

2. **Initialize and start**:
   ```bash
   make docker-init  # First time only
   make docker-dev   # Start all services
   ```

3. **Access**: http://localhost:2026

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed Docker development guide.

### Option 2: Local Development

If you prefer running services locally:

1. **Check prerequisites**:
   ```bash
   make check  # Verifies Node.js 22+, pnpm, uv, nginx
   ```

2. **Configure and install**:
   ```bash
   cp config.example.yaml config.yaml
   make install
   ```

3. **Start services**:
   ```bash
   make dev
   ```

4. **Access**: http://localhost:2026

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed local development guide.

## Features

- 🤖 **LangGraph-based Agents** - Multi-agent orchestration with sophisticated workflows
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
- [MCP Setup Guide](MCP_SETUP.md) - Configure Model Context Protocol servers for additional tools

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
