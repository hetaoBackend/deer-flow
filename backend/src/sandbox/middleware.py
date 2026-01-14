from typing import NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from src.agents.thread_state import SandboxState
from src.sandbox import get_sandbox_provider


class SandboxMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    sandbox: NotRequired[SandboxState | None]


class SandboxMiddleware(AgentMiddleware[SandboxMiddlewareState]):
    """Create a sandbox environment and assign it to an agent."""

    state_schema = SandboxMiddlewareState

    def _acquire_sandbox(self) -> str:
        provider = get_sandbox_provider()
        sandbox_id = provider.acquire()
        print(f"Acquiring sandbox {sandbox_id}")
        return sandbox_id

    @override
    def before_agent(self, state: SandboxMiddlewareState, runtime: Runtime) -> dict | None:
        if "sandbox" not in state or state["sandbox"] is None:
            sandbox_id = self._acquire_sandbox()
            return {"sandbox": {"sandbox_id": sandbox_id}}
        return super().before_agent(state, runtime)
