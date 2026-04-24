# RFC: Inherit Parent Skill Allowlist in Subagents

## Summary

Subagents should never gain access to skills that the parent agent was not allowed to load.

Today a parent custom agent can restrict skills, but a default subagent with `skills=None` loads all enabled skills from disk. That bypasses the parent agent's allowlist and can inject unrelated or unsafe skill instructions into the subagent context.

## Problem

Skill access is part of an agent's instruction boundary. If a configured agent allows only `safe-skill`, delegating work to a `general-purpose` subagent should not expand that boundary to every enabled skill.

Current risky sequence:

1. Parent agent config sets `skills: ["safe-skill"]`.
2. An enabled custom skill exists on disk, for example `dangerous-skill`.
3. Parent agent calls the `task` tool.
4. The built-in subagent config has `skills=None`.
5. `SubagentExecutor` treats `None` as "load all enabled skills".
6. The subagent receives `dangerous-skill` as a system/developer message.

This violates least privilege and makes subagent behavior depend on unrelated enabled skills.

## Affected Code

- `backend/packages/harness/deerflow/tools/builtins/task_tool.py`
- `backend/packages/harness/deerflow/subagents/executor.py`
- `backend/packages/harness/deerflow/subagents/registry.py`
- Agent config loading that determines the parent skill allowlist

## Goals

- Parent agent skill allowlists constrain subagents by default.
- Custom subagent skill config can further narrow, but not widen, parent access.
- Preserve explicit `skills=[]` semantics for no skills.
- Add tests for built-in and custom subagents.

## Non-Goals

- Redesign skill installation or enablement.
- Remove the ability for a top-level agent with unrestricted skills to delegate to unrestricted subagents.
- Change skill file format.

## Proposal

Pass the parent agent's effective skill allowlist into `task_tool` metadata or executor initialization.

Effective subagent skills should be:

- parent unrestricted + subagent unrestricted: all enabled skills
- parent unrestricted + subagent allowlist: subagent allowlist
- parent allowlist + subagent unrestricted: parent allowlist
- parent allowlist + subagent allowlist: intersection
- any side `[]`: no skills, or intersection semantics that yields empty

If a custom subagent requests a skill outside the parent allowlist, log a warning and omit it.

The same inheritance rule should apply whether the subagent is built-in or custom.

## Testing

Add tests for:

- Parent `skills=["safe"]`, default subagent loads only `safe`.
- Parent `skills=["safe"]`, custom subagent `skills=["safe", "other"]` loads only `safe`.
- Parent unrestricted, custom subagent `skills=["safe"]` loads only `safe`.
- Parent `skills=[]` causes subagent to load no skills.

## Open Questions

- Where should the parent effective skill list be stored so direct SDK usage and gateway usage behave the same?
- Should the UI/API expose that a subagent skill request was narrowed by parent policy?
