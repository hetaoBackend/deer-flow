# RFC: Normalize LangGraph Runtime Context for Lead Agent Configuration

## Summary

The gateway should support LangGraph 0.6-style `config.context` for run-time agent options such as `model_name`, `thinking_enabled`, `is_plan_mode`, and `subagent_enabled`.

Currently `build_run_config()` preserves `context`, but `make_lead_agent()` only reads `configurable`. Requests that use `config.context` therefore silently fall back to default model and runtime options.

## Problem

LangGraph 0.6 introduced `context` as the preferred place for run-level context. The gateway has code to avoid sending both `context` and `configurable`, but the lead agent factory still reads only:

```python
cfg = config.get("configurable", {})
```

Risky sequence:

1. Client sends a run request with `config.context.model_name = "deepseek-v3"`.
2. Gateway preserves `context` and skips `configurable`.
3. `make_lead_agent()` reads an empty configurable dict.
4. The requested model and flags are ignored.
5. The run uses defaults without warning.

This affects model selection, thinking mode, plan mode, subagent enablement, custom agent names, and other run-time knobs that are currently read from `configurable`.

## Affected Code

- `backend/app/gateway/services.py`
- `backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- Tests around gateway run config and lead agent model resolution

## Goals

- Support both legacy `configurable` and newer `context` callers.
- Avoid silent fallback when caller supplied valid run options.
- Keep behavior consistent between gateway, SDK, and channel manager paths.
- Add end-to-end tests that verify requested model/options reach `create_chat_model`.

## Non-Goals

- Remove support for `configurable`.
- Pass arbitrary unvalidated request data into agent internals.
- Change public option names.

## Proposal

Introduce a small normalization helper that builds the effective run options:

1. Start with `config.get("configurable", {})`.
2. Merge allowed keys from `config.get("context", {})`.
3. Decide precedence. Recommended: explicit `context` wins for LangGraph 0.6 requests, while logging if both contain conflicting values.
4. Use the normalized dict everywhere `make_lead_agent()` currently reads `configurable`.

Allowed keys should include the existing runtime options:

- `thread_id`
- `model_name`
- `model`
- `thinking_enabled`
- `reasoning_effort`
- `is_plan_mode`
- `subagent_enabled`
- `max_concurrent_subagents`
- `is_bootstrap`
- `agent_name`

The gateway can also inject `assistant_id` into `context.agent_name` when it is already operating in context mode.

## Testing

Add tests for:

- `config.context.model_name` reaches `create_chat_model(name=...)`.
- `config.context.subagent_enabled` enables task tooling/middleware.
- `config.context.agent_name` selects the custom agent.
- When both `context` and `configurable` are present with conflicting values, the chosen precedence is deterministic and logged.

## Open Questions

- Should normalization happen in the gateway only, or in `make_lead_agent()` so direct SDK callers get the same behavior?
- Should unknown context keys be ignored, logged, or rejected?
