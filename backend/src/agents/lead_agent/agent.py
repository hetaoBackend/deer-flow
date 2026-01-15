from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig

from src.agents.lead_agent.prompt import apply_prompt_template
from src.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
from src.agents.middlewares.title_middleware import TitleMiddleware
from src.agents.thread_state import ThreadState
from src.models import create_chat_model
from src.sandbox.middleware import SandboxMiddleware
from src.tools import get_available_tools

# ThreadDataMiddleware must be before SandboxMiddleware to ensure thread_id is available
middlewares = [ThreadDataMiddleware(), SandboxMiddleware(), TitleMiddleware()]


def make_lead_agent(config: RunnableConfig):
    thinking_enabled = config.get("configurable", {}).get("thinking_enabled", True)
    model_name = config.get("configurable", {}).get("model_name")
    print(f"thinking_enabled: {thinking_enabled}, model_name: {model_name}")
    return create_agent(
        model=create_chat_model(name=model_name, thinking_enabled=thinking_enabled),
        tools=get_available_tools(),
        middleware=middlewares,
        system_prompt=apply_prompt_template(),
        state_schema=ThreadState,
    )
