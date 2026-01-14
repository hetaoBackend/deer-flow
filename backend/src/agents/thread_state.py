from typing import NotRequired, TypedDict

from langchain.agents import AgentState


class SandboxState(TypedDict):
    sandbox_id: NotRequired[str | None]


class ThreadState(AgentState):
    sandbox: NotRequired[SandboxState | None]
    title: NotRequired[str | None]
