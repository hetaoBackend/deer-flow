# RFC: Gate Deferred MCP Tool Execution Until Promotion

## Summary

When `tool_search` is enabled, MCP tools should not be executable until the model has explicitly selected or promoted them through the deferred tool flow.

Currently deferred MCP tools are hidden from model binding, but they still exist in the runtime tool set. If an unbound tool call is injected, restored from history, or produced by a permissive provider, the ToolNode can execute it directly.

## Problem

The deferred tool design has two intended effects:

1. Keep large MCP tool schemas out of the model context.
2. Force the model to discover/select a tool through `tool_search` before using it.

The current implementation primarily does the first part. The complete MCP tool list is still passed into the executable tool collection, while middleware filters the list shown to the model.

That leaves a bypass:

1. `tool_search.enabled` is true.
2. MCP tool `foo` is registered as deferred but not promoted.
3. A model/provider emits a tool call for `foo`, or a saved AIMessage containing `foo` is resumed.
4. The runtime router finds `foo` in the executable tools and runs it.

For filesystem, browser, network, or SaaS MCP tools this is a capability boundary issue.

## Affected Code

- `backend/packages/harness/deerflow/tools/tools.py`
- `backend/packages/harness/deerflow/tools/builtins/tool_search.py`
- `backend/packages/harness/deerflow/agents/middlewares/deferred_tool_filter_middleware.py`
- Runtime tool-call middleware around ToolNode execution

## Goals

- Make deferred tools non-executable until promoted.
- Keep the model-visible schema filtering behavior.
- Preserve current `tool_search` user experience.
- Make bypass attempts produce a clear tool error, not a silent execution.

## Non-Goals

- Redesign MCP tool discovery.
- Remove support for direct MCP binding when `tool_search` is disabled.
- Change individual MCP server permissions.

## Proposal

Add an execution gate in a tool-call middleware:

1. Track deferred tool names in the `DeferredToolRegistry`.
2. Track promoted tool names separately.
3. Before executing any tool call, check whether the name is deferred and not promoted.
4. If so, return a ToolMessage error instructing the model to call `tool_search`.
5. Once `tool_search` promotes a tool, allow that tool for the current run/context.

This gate should run for both sync and async tool calls.

The registry should also be scoped so subagent tool construction or nested calls cannot accidentally reset or overwrite the parent run's promoted tools.

## Testing

Add tests for:

- Deferred MCP tool call before promotion returns an error and does not invoke the underlying tool.
- Promoted MCP tool call executes normally.
- Resumed message history containing an unpromoted MCP tool call is rejected.
- Subagent tool construction does not clear the parent run's promoted registry.

## Open Questions

- Should promotion be per single tool call, per run, or per conversation turn?
- Should the error include the closest matching deferred tool names, or only instruct `tool_search`?
