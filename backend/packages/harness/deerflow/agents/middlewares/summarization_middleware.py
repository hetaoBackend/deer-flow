"""Summarization middleware extensions for DeerFlow."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from langchain.agents import AgentState
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import AnyMessage
from langgraph.config import get_config
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummarizationEvent:
    """Context emitted before conversation history is summarized away."""

    messages_to_summarize: list[AnyMessage]
    preserved_messages: list[AnyMessage]
    thread_id: str | None
    runtime: Runtime


@runtime_checkable
class BeforeSummarizationHook(Protocol):
    """Hook invoked before summarization removes messages from state."""

    def __call__(self, event: SummarizationEvent) -> None: ...


def _resolve_thread_id(runtime: Runtime) -> str | None:
    """Resolve the current thread ID from runtime context or LangGraph config."""
    thread_id = runtime.context.get("thread_id") if runtime.context else None
    if thread_id is None:
        config_data = get_config()
        thread_id = config_data.get("configurable", {}).get("thread_id")
    return thread_id


class DeerFlowSummarizationMiddleware(SummarizationMiddleware):
    """Summarization middleware with pre-compression hook dispatch."""

    def __init__(
        self,
        *args,
        before_summarization: list[BeforeSummarizationHook] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._before_summarization_hooks = before_summarization or []

    def before_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        self._fire_hooks(state, runtime)
        return super().before_model(state, runtime)

    async def abefore_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        self._fire_hooks(state, runtime)
        return await super().abefore_model(state, runtime)

    def _fire_hooks(self, state: AgentState, runtime: Runtime) -> None:
        if not self._before_summarization_hooks:
            return

        messages = state["messages"]
        self._ensure_message_ids(messages)

        total_tokens = self.token_counter(messages)
        if not self._should_summarize(messages, total_tokens):
            return

        cutoff_index = self._determine_cutoff_index(messages)
        if cutoff_index <= 0:
            return

        messages_to_summarize, preserved_messages = self._partition_messages(messages, cutoff_index)
        event = SummarizationEvent(
            messages_to_summarize=messages_to_summarize,
            preserved_messages=preserved_messages,
            thread_id=_resolve_thread_id(runtime),
            runtime=runtime,
        )

        for hook in self._before_summarization_hooks:
            try:
                hook(event)
            except Exception:
                logger.exception("before_summarization hook %s failed", type(hook).__name__)
