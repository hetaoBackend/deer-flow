# [RFC] Support Langfuse Tracing in DeerFlow

## Summary

DeerFlow currently has built-in LangSmith tracing support, but does not support Langfuse as a trace backend. This RFC proposes adding provider-based tracing so DeerFlow can export agent, tool, and model traces to Langfuse with minimal disruption to the existing LangSmith path.

The recommended implementation is:

- Introduce a tracing provider abstraction: `langsmith | langfuse`
- Keep existing `LANGSMITH_*` behavior fully backward compatible
- Add Langfuse support via `langfuse.langchain.CallbackHandler`
- Move callback injection from model construction to per-run `RunnableConfig["callbacks"]`

This is the lowest-risk path because DeerFlow already follows a LangChain/LangGraph callback-based execution model.

## Problem

Today DeerFlow tracing is effectively hardcoded to LangSmith:

- Tracing config only understands `LANGSMITH_*` and legacy `LANGCHAIN_*`
- `create_chat_model()` attaches `LangChainTracer` directly to the model instance
- Run metadata is prepared for LangSmith-style tagging, but there is no provider abstraction

This creates three problems:

1. Teams using Langfuse cannot adopt DeerFlow tracing without patching the codebase
2. Model-level tracer injection is the wrong abstraction boundary for multi-provider tracing
3. The current design makes it hard to add trace-specific metadata like Langfuse `session_id`, tags, and user context

## Goals

- Support Langfuse as a first-class tracing backend
- Preserve existing LangSmith behavior for current users
- Capture full DeerFlow execution traces, not just isolated model calls
- Reuse DeerFlow's existing `thread_id`, `agent_name`, and `model_name` as trace context
- Keep the initial implementation small and easy to validate

## Non-Goals

- Rebuilding DeerFlow observability around OpenTelemetry from day one
- Adding a custom UI for trace inspection inside DeerFlow
- Emitting every internal backend event as a custom tracing span
- Reworking unrelated logging or token usage systems

## Current State

Current tracing-related behavior lives in these places:

- `deerflow.config.tracing_config`
  - Reads `LANGSMITH_*` and legacy `LANGCHAIN_*`
- `deerflow.models.factory.create_chat_model`
  - Appends `LangChainTracer` to `model_instance.callbacks`
- `deerflow.agents.lead_agent.make_lead_agent`
  - Injects `agent_name`, `model_name`, and mode flags into `config["metadata"]`
- `DeerFlowClient`
  - Builds the `RunnableConfig` used for embedded runs

This means DeerFlow already has most of the metadata needed for Langfuse, but the callback attachment point is too low in the stack.

## Proposal

### 1. Add provider-based tracing config

Extend tracing config to support a DeerFlow-level provider switch:

```bash
DEERFLOW_TRACING_ENABLED=true
DEERFLOW_TRACING_PROVIDER=langfuse
```

LangSmith remains supported:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=deer-flow
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Langfuse adds:

```bash
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Expected behavior:

- If provider is `langsmith`, use the current LangSmith path
- If provider is `langfuse`, build Langfuse callback handlers
- If nothing is configured, tracing remains disabled

### 2. Move tracer injection to run-time config

Instead of attaching tracer callbacks during model construction, inject callbacks into each run:

```python
config["callbacks"] = [callback_handler]
```

Why:

- Langfuse's LangChain integration is designed around per-run callback handlers
- Per-run injection is a better fit for LangGraph execution than model-level mutation
- This makes provider switching and metadata injection much cleaner
- This avoids hidden callback state hanging off long-lived model instances

### 3. Reuse DeerFlow runtime metadata for Langfuse context

For Langfuse runs, map DeerFlow metadata as follows:

- `thread_id` -> Langfuse `session_id`
- `agent_name` -> metadata + tags
- `model_name` -> metadata + tags
- `thinking_enabled` -> metadata
- `reasoning_effort` -> metadata
- `is_plan_mode` -> metadata
- `subagent_enabled` -> metadata

This gives Langfuse traces stable grouping without requiring additional DeerFlow identifiers.

### 4. Keep phase 1 callback-based, not OTel-first

Langfuse's Python stack is compatible with OpenTelemetry, but DeerFlow should not start with a full OTel-first rewrite.

Phase 1 should stay focused on:

- LangChain/LangGraph callback-based tracing
- Minimal code churn
- Full backward compatibility for LangSmith

If needed later, phase 2 can add custom Langfuse observations around:

- gateway requests
- channel message handling
- memory update jobs
- subagent lifecycle

## Proposed Implementation

### New abstraction

Introduce a small tracing helper module, for example:

- `deerflow.tracing.callbacks`

Suggested responsibilities:

- build tracing callbacks for the active provider
- enrich `RunnableConfig` with provider-specific metadata
- keep provider-specific imports out of model factory logic

Example API:

```python
def prepare_run_config_for_tracing(
    config: RunnableConfig,
    *,
    thread_id: str | None,
    agent_name: str | None,
    model_name: str | None,
) -> RunnableConfig:
    ...
```

### Integration points

- `deerflow.agents.lead_agent.make_lead_agent`
  - inject provider-specific callbacks and metadata for LangGraph server runs
- `deerflow.client.DeerFlowClient._get_runnable_config`
  - inject provider-specific callbacks and metadata for embedded client runs
- `deerflow.models.factory.create_chat_model`
  - stop attaching provider-specific tracing handlers directly to model instances

### Dependency

Add optional runtime dependency:

```toml
langfuse>=3
```

## Alternatives Considered

### A. Keep LangSmith-only support

Rejected because it blocks teams already standardized on Langfuse.

### B. Add Langfuse by mutating `model_instance.callbacks`

Rejected because:

- it is too low-level
- it is less aligned with Langfuse's recommended LangChain usage
- it makes run-scoped metadata harder to manage

### C. Do a full OpenTelemetry redesign immediately

Rejected for phase 1 because it adds too much scope and risk relative to the problem we are solving.

## Risks

### Duplicate tracing

If LangSmith model-level callbacks remain while Langfuse is added at run level, the system may emit duplicate or fragmented traces.

Mitigation:

- move to one injection path
- ensure only one provider is active for a given run

### Incomplete metadata propagation

If `thread_id` is not consistently available, Langfuse `session_id` grouping will be weaker.

Mitigation:

- reuse existing DeerFlow `thread_id` propagation paths
- gracefully omit `session_id` when not present

### Concurrency surprises with shared handlers

Some callback handlers hold run-local state.

Mitigation:

- construct handlers per run
- avoid global singleton callback objects

## Acceptance Criteria

- DeerFlow can be configured with `DEERFLOW_TRACING_PROVIDER=langfuse`
- A simple chat run appears in Langfuse as one coherent trace
- Tool calls are visible in the trace hierarchy
- `thread_id` is represented as Langfuse session context
- Existing LangSmith users see no breaking config changes
- When tracing is disabled, DeerFlow behavior is unchanged

## Rollout Plan

1. Add provider-aware tracing config and tests
2. Add Langfuse callback builder
3. Move tracing injection from model-level to run-level
4. Validate both LangGraph server runs and `DeerFlowClient` runs
5. Update README/backend docs with Langfuse setup examples

## Open Questions

1. Do we want DeerFlow-specific env names like `DEERFLOW_TRACING_ENABLED`, or should provider enablement be inferred entirely from vendor env vars?
2. Should Langfuse support ship as an always-installed dependency, or as an optional extra?
3. Do we want to propagate end-user identity into tracing in a later phase for IM channel integrations?

## Suggested Issue Title

`[RFC] Support Langfuse tracing in DeerFlow`

## Suggested Labels

- `rfc`
- `observability`
- `enhancement`

## References

- Langfuse SDK Overview: https://langfuse.com/docs/observability/sdk/overview
- Langfuse LangChain integration: https://langfuse.com/integrations/frameworks/langchain
