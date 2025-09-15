# Repository Guidelines

## Project Structure & Module Organization
- Root package: `__init__.py`, entrypoint: `main.py`.
- Modules: `config/` (env + instrumentation), `models/` (Pydantic + DSPy signatures), `tools/` (Tavily/web utils), `metrics/` (scoring + LLM judge), `data/` (examples/fixtures).
- Assets/data belong in `data/`; avoid checking large files into git.

## Build, Test, and Development Commands
- Create env: `python -m venv .venv && . .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`).
- Install deps (example): `pip install dspy-ai openai tavily-python httpx beautifulsoup4 pydantic python-dotenv openinference-instrumentation-dspy mcp`.
- Run locally: `python main.py` (requires API keys; see below).
- Lint/format (if installed): `ruff check .` and `black .`.

## Coding Style & Naming Conventions
- Python 3.10+; PEP 8 with 4-space indents and type hints.
- Modules/files: `lower_snake_case.py`; classes: `PascalCase`; functions/vars: `snake_case`.
- Docstrings: one-line summary + short details where helpful.
- Imports: prefer absolute within repo (e.g., `from models.vendor import Vendor`). Keep functions small and side-effect free.

## Testing Guidelines
- Framework: `pytest` recommended (add to dev deps if introducing tests).
- Layout: place tests under `tests/`, named `test_*.py`; mirror module paths.
- Isolation: mock network and LLM calls (e.g., `httpx`/`responses` or fakes). Use `data/examples.py` for fixtures.
- Targets: validate parsing in `tools/`, scoring in `metrics/`, and schema in `models/`.

## Commit & Pull Request Guidelines
- Commit style: Conventional Commits (e.g., `feat: add vendor score breakdown`). Keep messages imperative and focused.
- PRs: include purpose, summary of changes, before/after behavior (CLI output if applicable), and linked issues. Note any config/env impacts.
- CI readiness: ensure `python main.py` runs locally and tests pass before requesting review.

## Security & Configuration Tips
- Required env vars: `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, optional `LANGFUSE_HOST`, and `TAVILY_API_KEY`. Use a local `.env`; never commit secrets.
- Networked components: `tools/web_tools.py` and `main.py` call external services (Tavily MCP, OpenAI). Add timeouts and error handling when extending.
