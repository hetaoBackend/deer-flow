"""LLM and search provider definitions for the Setup Wizard."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMProvider:
    name: str
    display_name: str
    description: str
    use: str
    models: list[str]
    default_model: str
    env_var: str
    package: str
    # Optional: some providers use a different field name for the API key in YAML
    api_key_field: str = "api_key"
    # Extra config fields beyond the common ones (merged into YAML)
    extra_config: dict = field(default_factory=dict)


@dataclass
class SearchProvider:
    name: str
    display_name: str
    description: str
    use: str
    env_var: str | None  # None = no API key required
    tool_name: str = "web_search"


LLM_PROVIDERS: list[LLMProvider] = [
    LLMProvider(
        name="openai",
        display_name="OpenAI",
        description="GPT-4o, GPT-4.1, o3",
        use="langchain_openai:ChatOpenAI",
        models=["gpt-4o", "gpt-4.1", "o3"],
        default_model="gpt-4o",
        env_var="OPENAI_API_KEY",
        package="langchain-openai",
    ),
    LLMProvider(
        name="anthropic",
        display_name="Anthropic",
        description="Claude Opus 4, Sonnet 4",
        use="langchain_anthropic:ChatAnthropic",
        models=["claude-opus-4-5", "claude-sonnet-4-5"],
        default_model="claude-sonnet-4-5",
        env_var="ANTHROPIC_API_KEY",
        package="langchain-anthropic",
        extra_config={"max_tokens": 8192},
    ),
    LLMProvider(
        name="deepseek",
        display_name="DeepSeek",
        description="V3, R1",
        use="langchain_deepseek:ChatDeepSeek",
        models=["deepseek-chat", "deepseek-reasoner"],
        default_model="deepseek-chat",
        env_var="DEEPSEEK_API_KEY",
        package="langchain-deepseek",
    ),
    LLMProvider(
        name="google",
        display_name="Google Gemini",
        description="2.0 Flash, 2.5 Pro",
        use="langchain_google_genai:ChatGoogleGenerativeAI",
        models=["gemini-2.0-flash", "gemini-2.5-pro"],
        default_model="gemini-2.0-flash",
        env_var="GEMINI_API_KEY",
        package="langchain-google-genai",
        api_key_field="gemini_api_key",
    ),
    LLMProvider(
        name="other",
        display_name="Other",
        description="OpenAI-compatible gateway (custom base_url)",
        use="langchain_openai:ChatOpenAI",
        models=["gpt-4o"],
        default_model="gpt-4o",
        env_var="OPENAI_API_KEY",
        package="langchain-openai",
    ),
]

SEARCH_PROVIDERS: list[SearchProvider] = [
    SearchProvider(
        name="ddg",
        display_name="DuckDuckGo (free, no key needed)",
        description="No API key required",
        use="deerflow.community.ddg_search.tools:web_search_tool",
        env_var=None,
    ),
    SearchProvider(
        name="tavily",
        display_name="Tavily",
        description="Recommended, free tier available",
        use="deerflow.community.tavily.tools:web_search_tool",
        env_var="TAVILY_API_KEY",
    ),
]
