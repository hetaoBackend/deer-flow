"""Step 1: LLM provider selection."""

from __future__ import annotations

from dataclasses import dataclass

from wizard.providers import LLM_PROVIDERS, LLMProvider
from wizard.ui import (
    ask_choice,
    ask_secret,
    ask_text,
    print_header,
    print_info,
    print_success,
)


@dataclass
class LLMStepResult:
    provider: LLMProvider
    model_name: str
    api_key: str
    base_url: str | None = None


def run_llm_step(step_label: str = "Step 1/3") -> LLMStepResult:
    print_header(f"{step_label} · Choose your LLM provider")

    options = [f"{p.display_name}  ({p.description})" for p in LLM_PROVIDERS]
    idx = ask_choice("Enter choice", options)
    provider = LLM_PROVIDERS[idx]

    print()

    # Model selection (show list, default to first)
    if len(provider.models) > 1:
        print_info(f"Available models for {provider.display_name}:")
        model_idx = ask_choice("Select model", provider.models, default=0)
        model_name = provider.models[model_idx]
    else:
        model_name = provider.models[0]

    print()
    print_header(f"{step_label.split('/')[0].replace('Step ', 'Step ')} · Enter your API Key")

    # "Other" provider: ask for base_url too
    base_url: str | None = None
    if provider.name == "other":
        base_url = ask_text("Base URL (e.g. https://api.openai.com/v1)", required=True)
        model_name = ask_text("Model name", default=provider.default_model)

    if provider.env_var:
        api_key = ask_secret(f"{provider.env_var}")
    else:
        api_key = ""

    if api_key:
        print_success(f"Key will be saved to .env as {provider.env_var}")

    return LLMStepResult(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
    )
