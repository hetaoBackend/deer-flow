# DeerFlow install.md

This file is for coding agents. Execute it from the repository root.

## Goal

Prepare a working DeerFlow development environment on the user's machine with the least risky path available.

Default preference:

1. Docker development environment
2. Local development environment

Do not assume API keys or model credentials exist. Set up everything that can be prepared safely, then stop with a concise summary of what the user still needs to provide.

## Operating Rules

- Be idempotent. Re-running this document should not damage an existing setup.
- Prefer existing repo commands over ad hoc shell commands.
- Do not use `sudo` or install system packages without explicit user approval.
- Do not overwrite existing user config values unless the user asks.
- If a step fails, stop, explain the blocker, and provide the smallest next action.
- If multiple setup paths are possible, prefer Docker when Docker is already available.

## Success Criteria

Consider the setup successful when all of the following are true:

- The repo is at the DeerFlow project root.
- `config.yaml` exists.
- Project dependencies for the chosen path are installed or initialized.
- The user receives the exact next command to launch DeerFlow.
- The user also receives the exact config fields or environment variables still missing, if any.

## TODO

- Confirm the current directory is the DeerFlow repository root by checking that `Makefile`, `backend/`, `frontend/`, and `config.example.yaml` exist.
- Detect whether `config.yaml` already exists.
- If `config.yaml` does not exist, run `make config`.
- Detect whether Docker is available with `docker --version`.
- If Docker is available:
  - Run `make docker-init`.
  - Do not start long-running services unless the user explicitly asks or this setup request clearly includes launch verification.
  - Tell the user the recommended next command is `make docker-start`.
- If Docker is not available:
  - Run `make check`.
  - If `make check` reports missing system dependencies such as `node`, `pnpm`, `uv`, or `nginx`, stop and report the missing tools instead of attempting privileged installs.
  - If prerequisites are satisfied, run `make install`.
  - Tell the user the recommended next command is `make dev`.
- Inspect `config.yaml` and `.env` only for placeholders or missing required values. Do not print secrets.
- If no model is configured, tell the user they must add at least one entry under `models` in `config.yaml`.
- If obvious placeholder API keys remain, tell the user which variables still need real values.
- If the repository already appears configured, avoid repeating expensive work unless it is necessary to verify the environment.

## Verification

Use the lightest verification that matches the chosen setup path.

For Docker setup:

- Confirm `make docker-init` completed successfully.
- Confirm `config.yaml` exists.
- Do not leave background services running unless the user asked for that.

For local setup:

- Confirm `make install` completed successfully.
- Confirm `config.yaml` exists.
- Do not leave background services running unless the user asked for that.

## Final Response Format

Return a short status report with:

1. Setup path used: Docker or local
2. Files created or detected: for example `config.yaml`
3. Remaining user action: model config, API keys, auth files, or nothing
4. Exact next command to start DeerFlow

## EXECUTE NOW

Complete the TODO list above. When finished, stop after the setup boundary and report status instead of continuing into unrelated project work.
