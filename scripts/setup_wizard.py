#!/usr/bin/env python3
"""DeerFlow Interactive Setup Wizard.

Usage:
    uv run python scripts/setup_wizard.py           # Quick Setup
    uv run python scripts/setup_wizard.py --full    # Full Setup (not yet implemented)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the scripts/ directory importable so wizard.* works
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def main() -> int:
    full_mode = "--full" in sys.argv

    if not _is_interactive():
        print(
            "Non-interactive environment detected.\n"
            "Please edit config.yaml and .env directly, or run 'make setup' in a terminal."
        )
        return 1

    from wizard.ui import (
        ask_yes_no,
        bold,
        cyan,
        green,
        print_header,
        print_info,
        print_success,
        yellow,
    )
    from wizard.writer import write_config_yaml, write_env_file

    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "config.yaml"
    env_path = project_root / ".env"

    # ── Welcome ───────────────────────────────────────────────────────────────
    print()
    print(bold("Welcome to DeerFlow Setup!"))
    print("This wizard will help you configure DeerFlow in a few minutes.")
    print()

    # ── Returning-user detection ───────────────────────────────────────────────
    if config_path.exists():
        print(yellow("Existing configuration detected."))
        print()
        should_reconfigure = ask_yes_no("Do you want to reconfigure?", default=False)
        if not should_reconfigure:
            print()
            print_info("Keeping existing config. Run 'make doctor' to verify your setup.")
            return 0
        print()

    # ── Step 1: LLM ──────────────────────────────────────────────────────────
    from wizard.steps.llm import run_llm_step

    llm = run_llm_step("Step 1/3")

    # ── Step 2: Web Search ────────────────────────────────────────────────────
    from wizard.steps.search import run_search_step

    search = run_search_step("Step 2/3" if full_mode else "Step 2/3")

    # ── Write files ───────────────────────────────────────────────────────────
    print_header("Step 3/3 · Writing configuration")

    # config.yaml
    write_config_yaml(
        config_path,
        provider_use=llm.provider.use,
        model_name=llm.model_name,
        display_name=f"{llm.provider.display_name} / {llm.model_name}",
        api_key_field=llm.provider.api_key_field,
        env_var=llm.provider.env_var,
        extra_model_config=llm.provider.extra_config or None,
        base_url=llm.base_url,
        search_use=search.provider.use if search.provider else None,
        search_tool_name=search.provider.tool_name if search.provider else "web_search",
    )
    print_success(f"Config written to: {config_path.relative_to(project_root)}")

    # .env — copy .env.example if not present, then merge keys
    if not env_path.exists():
        env_example = project_root / ".env.example"
        if env_example.exists():
            import shutil
            shutil.copyfile(env_example, env_path)

    env_pairs: dict[str, str] = {}
    if llm.api_key:
        env_pairs[llm.provider.env_var] = llm.api_key
    if search.api_key and search.provider and search.provider.env_var:
        env_pairs[search.provider.env_var] = search.api_key

    if env_pairs:
        write_env_file(env_path, env_pairs)
        print_success(f"API keys written to: {env_path.relative_to(project_root)}")

    # Also ensure frontend/.env exists
    frontend_env = project_root / "frontend" / ".env"
    frontend_env_example = project_root / "frontend" / ".env.example"
    if not frontend_env.exists() and frontend_env_example.exists():
        import shutil
        shutil.copyfile(frontend_env_example, frontend_env)
        print_success("frontend/.env created from example")

    # ── Done ──────────────────────────────────────────────────────────────────
    print_header("Setup complete!")
    print(f"  {green('✓')} LLM:        {llm.provider.display_name} / {llm.model_name}")
    if search.provider:
        print(f"  {green('✓')} Web search: {search.provider.display_name}")
    else:
        print(f"  {'—':>3} Web search: not configured (DuckDuckGo used as fallback)")
    print()
    print("Next steps:")
    print(f"  {cyan('make install')}    # Install dependencies (first time only)")
    print(f"  {cyan('make dev')}        # Start DeerFlow")
    print()
    print(f"Run {cyan('make doctor')} to verify your setup at any time.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
