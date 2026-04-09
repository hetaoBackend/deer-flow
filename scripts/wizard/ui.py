"""Terminal UI helpers for the Setup Wizard."""

from __future__ import annotations

import getpass
import sys

# ── ANSI colours ──────────────────────────────────────────────────────────────

def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    if _supports_color():
        return f"\033[{code}m{text}\033[0m"
    return text


def green(text: str) -> str:
    return _c(text, "32")


def red(text: str) -> str:
    return _c(text, "31")


def yellow(text: str) -> str:
    return _c(text, "33")


def cyan(text: str) -> str:
    return _c(text, "36")


def bold(text: str) -> str:
    return _c(text, "1")


# ── UI primitives ─────────────────────────────────────────────────────────────

def print_header(title: str) -> None:
    width = max(len(title) + 4, 44)
    bar = "═" * width
    print()
    print(f"╔{bar}╗")
    print(f"║  {title.ljust(width - 2)}║")
    print(f"╚{bar}╝")
    print()


def print_section(title: str) -> None:
    print()
    print(bold(f"── {title} ──"))
    print()


def print_success(message: str) -> None:
    print(f"  {green('✓')} {message}")


def print_warning(message: str) -> None:
    print(f"  {yellow('!')} {message}")


def print_error(message: str) -> None:
    print(f"  {red('✗')} {message}")


def print_info(message: str) -> None:
    print(f"  {cyan('→')} {message}")


def ask_choice(prompt: str, options: list[str], default: int | None = None) -> int:
    """Present a numbered menu and return the 0-based index of the selected option."""
    for i, opt in enumerate(options, 1):
        marker = f" {green('*')}" if default is not None and i - 1 == default else "  "
        print(f"{marker} {i}. {opt}")
    print()

    while True:
        suffix = f" [{default + 1}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw == "" and default is not None:
            return default
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        print(f"  Please enter a number between 1 and {len(options)}.")


def ask_text(prompt: str, default: str = "", required: bool = False) -> str:
    """Ask for a text value, returning default if the user presses Enter."""
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print("  This field is required.")


def ask_secret(prompt: str) -> str:
    """Ask for a secret value (hidden input)."""
    while True:
        value = getpass.getpass(f"{prompt}: ").strip()
        if value:
            return value
        print("  API key cannot be empty.")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{prompt} {suffix}: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please enter y or n.")
