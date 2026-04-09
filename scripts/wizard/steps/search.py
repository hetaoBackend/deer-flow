"""Step: Web search configuration."""

from __future__ import annotations

from dataclasses import dataclass

from wizard.providers import SEARCH_PROVIDERS, SearchProvider
from wizard.ui import ask_choice, ask_secret, print_header, print_success


@dataclass
class SearchStepResult:
    provider: SearchProvider | None  # None = skip
    api_key: str | None


def run_search_step(step_label: str = "Step 3/3") -> SearchStepResult:
    print_header(f"{step_label} · Web Search (optional)")

    options = [f"{p.display_name}  —  {p.description}" for p in SEARCH_PROVIDERS]
    options.append("Skip for now  (agent still works without web search)")

    idx = ask_choice("Enable web search?", options, default=0)

    if idx >= len(SEARCH_PROVIDERS):
        # Skip
        return SearchStepResult(provider=None, api_key=None)

    provider = SEARCH_PROVIDERS[idx]

    api_key: str | None = None
    if provider.env_var:
        print()
        api_key = ask_secret(f"{provider.env_var}")
        print_success(f"Key will be saved to .env as {provider.env_var}")

    return SearchStepResult(provider=provider, api_key=api_key)
