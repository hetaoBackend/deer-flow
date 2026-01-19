# 🦌 DeerFlow - v2

> Originated from Open Source, give back to Open Source.

A LangGraph-based AI agent backend with sandbox execution capabilities.

## Quick Start

1. **Configure the application**:
   ```bash
   # Copy example configuration
   cp config.example.yaml config.yaml

   # Set your API keys
   export OPENAI_API_KEY="your-key-here"
   # or edit config.yaml directly

   # Optional: Enable MCP servers for additional tools
   cp mcp_config.example.json mcp_config.json
   # Edit mcp_config.json to enable desired servers
   ```

2. **Install dependencies**:
   ```bash
   cd backend
   make install
   ```

3. **Run development server**:
   ```bash
   make dev
   ```

### Production Deployment

For production environments, use nginx as a reverse proxy to route traffic between the gateway and LangGraph services:

1. **Start backend services**:
   ```bash
   # Terminal 1: Start Gateway API (port 8001)
   cd backend
   python -m src.gateway.app

   # Terminal 2: Start LangGraph Server (port 2024)
   cd backend
   langgraph up
   ```

2. **Start nginx**:
   ```bash
   nginx -c $(pwd)/nginx.conf
   ```

3. **Access the application**:
   - Main API: http://localhost:8000

The nginx configuration provides:
- Unified entry point on port 8000
- Routes `/api/models`, `/api/threads/*/artifacts`, and `/health` to Gateway (8001)
- Routes all other requests to LangGraph (2024)
- Centralized CORS handling
- SSE/streaming support for real-time agent responses
- Optimized timeouts for long-running operations

## Project Structure

```
deer-flow/
├── config.example.yaml    # Configuration template (copy to config.yaml)
├── nginx.conf            # Nginx reverse proxy configuration
├── backend/              # Backend application
│   ├── src/             # Source code
│   │   ├── gateway/     # Gateway API (port 8001)
│   │   └── agents/      # LangGraph agents (port 2024)
│   └── docs/            # Documentation
├── frontend/            # Frontend application
└── skills/              # Agent skills
    ├── public/          # Public skills
    └── custom/          # Custom skills
```

### Architecture

```
Client
  ↓
Nginx (port 8000) ← Unified entry point
  ├→ Gateway API (port 8001) ← /api/models, /api/threads/*/artifacts, /health
  └→ LangGraph Server (port 2024) ← All other requests (agent interactions)
```

## Documentation

- [Configuration Guide](backend/docs/CONFIGURATION.md) - Setup and configuration instructions
- [Architecture Overview](backend/CLAUDE.md) - Technical architecture details
- [MCP Setup Guide](MCP_SETUP.md) - Configure Model Context Protocol servers for additional tools

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
