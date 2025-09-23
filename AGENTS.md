# Repository Guidelines

## Project Structure & Module Organization
Root package holds `__init__.py` and CLI entry `main.py`. Place orchestration code in `agents/`, configuration in `config/`, schemas and DSPy signatures in `models/`, reusable Tavily/web helpers in `tools/`, and scoring utilities in `metrics/`. Store fixtures and mocked payloads under `data/`. Persist generated artifacts (reports, traces) in `outputs/`. Add new tests in `tests/` to mirror package paths; legacy `test_*.py` files at the root remain for backward compatibility.

## Build, Test, and Development Commands
Create a virtual env with `python -m venv .venv && . .venv/bin/activate` (PowerShell: `.venv\\Scripts\\Activate.ps1`). Install deps via `pip install -e .` or `pip install -r requirements.txt`. Run the CLI locally using `python main.py` after exporting API keys. Lint and format with `ruff check .` and `black .`. Execute tests using `pytest`; add `-k <pattern>` to target a subset.

## Coding Style & Naming Conventions
Target Python 3.10+, follow PEP 8 with 4-space indents, and include type hints. Modules use `lower_snake_case.py`; classes use `PascalCase`; functions, variables, and config keys use `snake_case`. Keep functions small, side-effect free, and prefer absolute imports (`from models.vendor import Vendor`). Use concise docstrings: one-line summary plus brief detail when needed.

## Testing Guidelines
Mock networked or LLM calls (`httpx.MockTransport`, `responses`, local fakes). Write tests under `tests/test_<module>.py` mirroring package layout. Validate parsing logic in `tools/`, scoring in `metrics/`, schema invariants in `models/`, and agent orchestration in `agents/`. Run `pytest --maxfail=1 --disable-warnings` before requesting review.

## Commit & Pull Request Guidelines
Use Conventional Commits (e.g., `feat: add vendor score breakdown`). PRs should summarize intent, list functional changes, attach critical CLI output, link issues, and call out config/env updates. Confirm `python main.py` completes with your `.env` and all tests pass.

## Security & Configuration Tips
Store secrets in `.env`; never commit them. Required keys: `OPENAI_API_KEY`, `TAVILY_API_KEY`; optional: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`. Add explicit timeouts and error handling when extending `tools/web_tools.py` or `main.py` to avoid long-running calls.

## Available Agents
- **Vendor Discovery**: Uses ReAct + Tavily to surface vendors with contacts and geographies.
- **SWOT Analysis**: Vendor-level strengths, weaknesses, opportunities, threats with optional caching.
- **PESTLE Analysis**: Market macro factors with political, economic, social, technological, legal, environmental pillars.
- **Porter’s 5 Forces**: Competitive pressure scan covering suppliers, buyers, rivalry, substitutes, entrants.
- **RFP Generation (isolated)**: Synthesizes PESTLE/Porter/SWOT outputs, mines public RFP references, and emits 100 categorized questions.
