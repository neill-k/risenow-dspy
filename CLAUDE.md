# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

### Required Environment Variables
Create a `.env` file with:
```
OPENAI_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
LANGFUSE_PUBLIC_KEY=optional_for_tracing
LANGFUSE_SECRET_KEY=optional_for_tracing
```

### Installation
```bash
# Use uv for dependency management (preferred)
uv pip install -e .

# Or standard pip
pip install -e .
```

### Running the System
```bash
# Main vendor discovery with PESTLE analysis
python main.py

# Individual agent tests
python test_vendor_agent.py
python test_pestle_agent.py
python test_porters_agent.py

# Bootstrap optimization demos
python -m optimize.bootstrap_vendor
python -m optimize.bootstrap_pestle
```

## Architecture Overview

### DSPy Agent Pattern
All agents follow a consistent DSPy-based architecture:

1. **Model Layer** (`models/`): Pydantic models define data structures and DSPy signatures define input/output contracts
2. **Agent Layer** (`agents/`): DSPy modules (ReAct or ChainOfThought) orchestrate reasoning with optional Tavily web tools
3. **Metrics Layer** (`metrics/`): LLM-based judges evaluate output quality for GEPA optimization
4. **Optimization** (`optimize/`): BootstrapFewShot and GEPA optimize agents with synthetic or real training data

### Core Agent Flow
```python
# 1. Create agent with tools
agent = create_[domain]_agent(use_tools=True, max_iters=N)

# 2. Create evaluation metric
metric, counter = create_[domain]_metric()

# 3. Generate/load training data
trainset = create_[domain]_trainset()

# 4. Optimize with GEPA
optimized = optimize_[domain]_agent(agent, metric, trainset, ...)

# 5. Cache optimized program
save_[domain]_agent(optimized, path)

# 6. Execute analysis
result = optimized(inputs...)
```

### Tool Integration
The system uses Tavily API for web research via `tools/web_tools.py`:
- `tavily_search()`: General web search
- `tavily_extract()`: Extract content from URLs
- `tavily_crawl()`: Deep website crawling
- DSPy tools are created via `create_dspy_tools()` factory

### Observability
Langfuse integration provides full tracing when credentials are configured:
- Automatic span creation for all DSPy operations
- Metric tracking for vendor coverage and PESTLE insights
- Session grouping for related operations
- GEPA optimization metrics captured

## Key Design Patterns

### Program Caching
Optimized DSPy programs are cached to disk (e.g., `data/artifacts/vendor_program.json`) to avoid re-optimization. Delete cache files to force re-optimization or set `VENDOR_OPTIMIZE_ON_MISS=false` to skip optimization entirely.

### Metric Functions
All metrics return `dspy.Prediction` with:
- `score`: Float between 0.0 and 1.0
- `feedback`: String explanation of score
- Optional detailed breakdowns for debugging

### Training Data
Training examples can be:
- Hardcoded in `create_[domain]_trainset()` functions
- Generated via BootstrapFewShot in `optimize/` modules
- Loaded from JSONL files in `data/artifacts/`

### Environment Configuration
All configuration flows through `config/environment.py`:
- Model settings: `DSPY_MODEL`, `DSPY_TEMPERATURE`, `DSPY_MAX_TOKENS`
- Reflection model: `DSPY_REFLECTION_MODEL` (used by GEPA)
- GEPA settings: `GEPA_MAX_METRIC_CALLS`, `GEPA_NUM_THREADS`
- Program paths: `VENDOR_PROGRAM_PATH`, etc.

## Adding New Analysis Agents

To add a new analysis type (e.g., SWOT):

1. **Define models** in `models/swot.py`:
   - Pydantic models for data structures
   - DSPy signatures for agent I/O
   - Judge signature for evaluation

2. **Create agent** in `agents/swot_agent.py`:
   - `create_swot_agent()`: Initialize ReAct/ChainOfThought
   - `create_swot_metric()`: Build evaluation metric
   - `create_swot_trainset()`: Generate training examples
   - `optimize_swot_agent()`: Apply GEPA optimization

3. **Add metrics** in `metrics/swot_scoring.py`:
   - Component scoring functions
   - `comprehensive_swot_score()`
   - `make_swot_llm_judge_metric()`

4. **Integrate** in `main.py`:
   - Add `run_with_swot()` or similar orchestration
   - Handle caching and optimization flags
   - Add observability spans

5. **Test** in `test_swot_agent.py`:
   - Unit tests for agent creation
   - Integration tests with vendor discovery
   - Optimization tests

## Important Conventions

### Error Handling
- Optimization failures fall back to base agents
- KeyboardInterrupt during optimization preserves partial results
- Missing API keys raise ValueError immediately

### Retry Configuration
All DSPy LM instances use `num_retries=30` (configurable via `DSPY_NUM_RETRIES` env var) with exponential backoff for resilience against API failures and rate limits. DSPy automatically uses LiteLLM's `exponential_backoff_retry` strategy.

### Max Iterations
- Vendor agent: 50 iterations (complex multi-vendor search)
- PESTLE agent: 30 iterations (market analysis)
- Porter's agent: 30 iterations (industry analysis)

### Threading
GEPA optimization uses `GEPA_NUM_THREADS=3` by default for parallel metric evaluation.