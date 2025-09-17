# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a vendor discovery system built with DSPy that uses GEPA (Generalized Expectation-Programmable Agents) optimization to find and evaluate vendors in various categories. The system leverages Tavily for web search and OpenAI models for reasoning.

## Common Development Commands

### Running the Application
```bash
python main.py
```
The main script performs vendor discovery with GEPA optimization. It requires environment variables (see Configuration section).

### Code Quality
```bash
# Syntax check
python -m compileall config models tools metrics data main.py

# If ruff is installed (not currently in dependencies)
ruff check .

# If black is installed (not currently in dependencies)
black .
```

### Dependencies
```bash
# Install dependencies with uv (preferred if available)
uv pip install -e .

# Or with pip
pip install -r requirements.txt  # if generated from pyproject.toml
```

## Architecture

### Core Flow
1. **Environment Setup** (`config/environment.py`): Validates API keys and configures DSPy models
2. **Tool Creation** (`tools/web_tools.py`): Creates Tavily-based search and extraction tools
3. **GEPA Optimization** (`main.py`): Uses reflective optimization to improve vendor discovery
4. **ReAct Agent** (`main.py`): Executes vendor search with optimized prompts and tool usage
5. **Scoring & Evaluation** (`metrics/scoring.py`): LLM-based judge evaluates vendor list quality

### Key Components

- **DSPy Configuration**: Uses two models - primary (gpt-5-mini by default) for main execution and reflection model (gpt-5) for GEPA optimization
- **Tavily Integration**: Web search, page extraction, crawling, and site mapping tools wrapped for DSPy compatibility
- **GEPA Optimization**: Few-shot reflective optimization that improves prompt engineering and tool usage patterns
- **Vendor Model** (`models/vendor.py`): Pydantic models enforce structured output with validation for emails, phone numbers, and geographic coverage

## Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY=<your-key>
TAVILY_API_KEY=<your-key>
```

### Optional Configuration
```bash
# Model configuration
DSPY_MODEL=openai/gpt-5-mini  # Primary model
DSPY_TEMPERATURE=1.0
DSPY_MAX_TOKENS=100000

# Reflection model for GEPA
DSPY_REFLECTION_MODEL=openai/gpt-5
DSPY_REFLECTION_TEMPERATURE=1.0
DSPY_REFLECTION_MAX_TOKENS=32000

# GEPA optimization settings
GEPA_MAX_METRIC_CALLS=60  # Number of optimization iterations
GEPA_NUM_THREADS=3  # Parallel threads for GEPA
```

## Development Notes

- The system uses MLflow for experiment tracking when run via `main.py`
- Page fetching includes caching to reduce redundant HTTP requests
- The ReAct agent has a max iteration limit of 50 to prevent infinite loops
- Vendor scoring considers email/phone validation, geographic coverage, and overall quality via LLM judge
- GEPA trainset in `main.py` uses minimal examples - expand for better optimization in production