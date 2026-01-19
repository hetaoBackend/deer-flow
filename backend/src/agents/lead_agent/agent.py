from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.runnables import RunnableConfig

from src.agents.lead_agent.prompt import apply_prompt_template
from src.agents.middlewares.clarification_middleware import ClarificationMiddleware
from src.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
from src.agents.middlewares.title_middleware import TitleMiddleware
from src.agents.thread_state import ThreadState
from src.config.summarization_config import get_summarization_config
from src.models import create_chat_model
from src.sandbox.middleware import SandboxMiddleware


def _create_summarization_middleware() -> SummarizationMiddleware | None:
    """Create and configure the summarization middleware from config."""
    config = get_summarization_config()

    if not config.enabled:
        return None

    # Prepare trigger parameter
    trigger = None
    if config.trigger is not None:
        if isinstance(config.trigger, list):
            trigger = [t.to_tuple() for t in config.trigger]
        else:
            trigger = config.trigger.to_tuple()

    # Prepare keep parameter
    keep = config.keep.to_tuple()

    # Prepare model parameter
    if config.model_name:
        model = config.model_name
    else:
        # Use a lightweight model for summarization to save costs
        # Falls back to default model if not explicitly specified
        model = create_chat_model(thinking_enabled=False)

    # Prepare kwargs
    kwargs = {
        "model": model,
        "trigger": trigger,
        "keep": keep,
    }

    if config.trim_tokens_to_summarize is not None:
        kwargs["trim_tokens_to_summarize"] = config.trim_tokens_to_summarize

    if config.summary_prompt is not None:
        kwargs["summary_prompt"] = config.summary_prompt

    return SummarizationMiddleware(**kwargs)


# ThreadDataMiddleware must be before SandboxMiddleware to ensure thread_id is available
# SummarizationMiddleware should be early to reduce context before other processing
# ClarificationMiddleware should be last to intercept clarification requests after model calls
def _build_middlewares():
    middlewares = [ThreadDataMiddleware(), SandboxMiddleware()]

    # Add summarization middleware if enabled
    summarization_middleware = _create_summarization_middleware()
    if summarization_middleware is not None:
        middlewares.append(summarization_middleware)

    middlewares.extend([TitleMiddleware(), ClarificationMiddleware()])
    return middlewares


def make_lead_agent(config: RunnableConfig):
    # Lazy import to avoid circular dependency
    from src.tools import get_available_tools

    thinking_enabled = config.get("configurable", {}).get("thinking_enabled", True)
    model_name = config.get("configurable", {}).get("model_name") or config.get("configurable", {}).get("model")
    print(f"thinking_enabled: {thinking_enabled}, model_name: {model_name}")
    return create_agent(
        model=create_chat_model(name=model_name, thinking_enabled=thinking_enabled),
        tools=get_available_tools(),
        middleware=_build_middlewares(),
        system_prompt=apply_prompt_template(),
        state_schema=ThreadState,
    )
