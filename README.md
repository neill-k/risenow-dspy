# DSPy Vendor Discovery & Market Analysis System

A comprehensive system for vendor discovery and market analysis using DSPy, featuring GEPA optimization, Tavily integration, and PESTLE analysis capabilities.

## Structure

```
risenow-dspy/
├── __init__.py                 # Main package init
├── main.py                     # Main script for vendor discovery and PESTLE analysis
├── example_pestle.py           # Example usage of PESTLE analysis
├── config/
│   ├── __init__.py
│   └── environment.py          # Environment setup and configuration
├── models/
│   ├── __init__.py
│   ├── vendor.py              # Vendor-related Pydantic models and DSPy signatures
│   └── pestle.py              # PESTLE analysis models and signatures
├── agents/
│   ├── __init__.py
│   └── pestle_agent.py        # PESTLE analysis agent implementation
├── tools/
│   ├── __init__.py
│   └── web_tools.py           # Tavily-based web search and extraction tools
├── metrics/
│   ├── __init__.py
│   ├── scoring.py             # Vendor scoring and evaluation metrics
│   └── pestle_scoring.py      # PESTLE analysis quality metrics
└── data/
    ├── __init__.py
    └── examples.py            # Example data and test cases
```

## Components

### Config (`config/`)
- **environment.py**: Environment variable validation and setup
- Handles OpenAI, Langfuse, and Tavily API keys
- Sets up DSPy instrumentation

### Models (`models/`)
- **vendor.py**: Vendor-related models and signatures
  - `ContactEmail`: Email contact information
  - `PhoneNumber`: Phone contact information
  - `Vendor`: Complete vendor information model
  - `VendorSearchResult`: DSPy signature for vendor discovery
  - `JudgeVendors`: DSPy signature for vendor evaluation

- **pestle.py**: PESTLE analysis models and signatures
  - `PoliticalFactors`: Government policies, regulations, trade agreements
  - `EconomicFactors`: Market size, growth rates, economic indicators
  - `SocialFactors`: Consumer trends, demographics, cultural factors
  - `TechnologicalFactors`: Innovation, disruption, digital transformation
  - `LegalFactors`: Compliance requirements, liability issues, contracts
  - `EnvironmentalFactors`: Sustainability, climate impact, green initiatives
  - `PESTLEAnalysis`: Complete PESTLE analysis model
  - `PESTLEMarketAnalysis`: DSPy signature for PESTLE analysis
  - `JudgePESTLE`: DSPy signature for PESTLE evaluation

### Agents (`agents/`)
- **pestle_agent.py**: PESTLE analysis agent implementation
  - `create_pestle_agent()`: Create ReAct or ChainOfThought PESTLE agent
  - `run_pestle_analysis()`: Execute PESTLE analysis for a market category
  - `create_pestle_trainset()`: Generate training examples for optimization
  - `optimize_pestle_agent()`: Optimize agent with GEPA or other DSPy optimizers
- **vendor_agent.py**: Vendor discovery agent implementation
  - `create_vendor_agent()`: Create ReAct or ChainOfThought vendor agent
  - `create_vendor_metric()`: Build LLM judge metric with call counter
  - `create_vendor_trainset()`: Generate reusable vendor training examples
  - `optimize_vendor_agent()`: Optimize vendor agent with GEPA or other DSPy optimizers

### Optimize (`optimize/`)
- **bootstrap_vendor.py**: Vendor BootstrapFewShot helpers
  - `bootstrap_vendor_agent()`: Compile a vendor agent given a handful of seed prompts
  - `save_vendor_bootstrap()`: Persist bootstrapped demos to JSONL for later reuse
- **bootstrap_pestle.py**: PESTLE BootstrapFewShot helpers
  - `bootstrap_pestle_agent()`: Compile a PESTLE agent with synthetic demos
  - `save_pestle_bootstrap()`: Persist bootstrapped PESTLE demos to JSONL for later reuse

### Tools (`tools/`)
- **web_tools.py**: Tavily-based web tools for research
  - `tavily_search()`: Web search with Tavily API
  - `tavily_extract()`: Extract content from URLs
  - `tavily_crawl()`: Crawl websites for comprehensive data
  - `tavily_map()`: Create knowledge maps of topics
  - `create_dspy_tools()`: Factory for DSPy tool instances

### Metrics (`metrics/`)
- **scoring.py**: Vendor quality scoring and evaluation
  - `contains_phone_number()`: Phone number validation scoring
  - `contains_contact_email()`: Email validation scoring
  - `contains_countries_served()`: Geographic coverage scoring
  - `comprehensive_vendor_score()`: Complete vendor quality assessment
  - `make_llm_judge_metric()`: LLM-based vendor list evaluation

- **pestle_scoring.py**: PESTLE analysis quality metrics
  - `evaluate_pestle_completeness()`: Assess factor coverage completeness
  - `evaluate_pestle_actionability()`: Score actionability of recommendations
  - `comprehensive_pestle_score()`: Complete PESTLE quality assessment
  - `make_pestle_llm_judge_metric()`: LLM-based PESTLE evaluation

### Data (`data/`)
- **examples.py**: Example data for testing and training
  - `general_industrial_supplies_example_n15`: Sample vendor list for industrial supplies

## Usage

### Basic Vendor Discovery

Run vendor discovery with GEPA optimization:

```python
python main.py
```

The first run optimizes the vendor agent and caches the compiled program to `VENDOR_PROGRAM_PATH` (default `data/artifacts/vendor_program.json`). Subsequent runs reuse that cache unless you delete the file or pass `reuse_cached_program=False` when calling `run()`. Set the `VENDOR_OPTIMIZE_ON_MISS=0` environment variable (or call `run(optimize_if_missing=False)`) to skip GEPA entirely when the cache is absent.

### Vendor Discovery with PESTLE Analysis

The `run_with_pestle()` function combines vendor discovery with comprehensive market analysis:

```python
from main import run_with_pestle

result = run_with_pestle(
    category="General Industrial Supplies",
    n=15,
    country_or_region="United States",
    include_pestle=True
)

# Access vendor list
vendors = result.vendor_list

# Access PESTLE analysis
pestle = result.pestle_analysis
print(pestle.executive_summary)
print(pestle.opportunities)
print(pestle.threats)
```

### Standalone PESTLE Analysis

Run PESTLE analysis examples:

```python
python example_pestle.py
```

Or use the PESTLE agent directly:

```python
from agents import create_pestle_agent

agent = create_pestle_agent(use_tools=True, max_iters=30)
result = agent(
    category="Cloud Computing Services",
    region="Europe",
    focus_areas=["legal", "technological", "environmental"]
)

pestle = result.pestle_analysis
```

## Features

### Vendor Discovery
- Searches for vendors in specified categories
- Validates contact information (emails, phone numbers)
- Assesses geographic coverage
- Uses GEPA optimization for improved results

### PESTLE Analysis
- **Political**: Government policies, regulations, trade agreements
- **Economic**: Market size, growth rates, economic indicators
- **Social**: Consumer trends, demographics, cultural factors
- **Technological**: Innovation, disruption, digital transformation
- **Legal**: Compliance requirements, liability issues, contracts
- **Environmental**: Sustainability, climate impact, green initiatives
- Provides strategic recommendations, opportunities, and threats
- Generates executive summaries

## Dependencies

- dspy-ai
- openai
- tavily-python
- httpx
- beautifulsoup4
- pydantic
- python-dotenv
- openinference-instrumentation-dspy
- mcp (Model Context Protocol)

## Environment Variables

### Required
- `OPENAI_API_KEY`: OpenAI API key
- `TAVILY_API_KEY`: Tavily API key for web search

### Optional
- `LANGFUSE_PUBLIC_KEY`: Langfuse public key for tracing
- `LANGFUSE_SECRET_KEY`: Langfuse secret key for tracing
- `LANGFUSE_HOST`: Langfuse host URL (defaults to US cloud)
- `VENDOR_PROGRAM_PATH`: Optional path for caching the optimized vendor program (default: `data/artifacts/vendor_program.json`)
- `VENDOR_OPTIMIZE_ON_MISS`: Set to `0`/`false` to skip GEPA when no cached program exists (defaults to `true`).

### DSPy Configuration
- `DSPY_MODEL`: Primary model (default: openai/gpt-5-mini)
- `DSPY_TEMPERATURE`: Temperature setting (default: 1.0)
- `DSPY_MAX_TOKENS`: Max tokens (default: 100000)
- `DSPY_REFLECTION_MODEL`: Reflection model for GEPA (default: openai/gpt-5)
- `DSPY_REFLECTION_TEMPERATURE`: Reflection temperature (default: 1.0)
- `DSPY_REFLECTION_MAX_TOKENS`: Reflection max tokens (default: 32000)

### GEPA Optimization
- `GEPA_MAX_METRIC_CALLS`: Number of optimization iterations (default: 60)
- `GEPA_NUM_THREADS`: Parallel threads for GEPA (default: 3)

### Observability (Langfuse)
- Provide `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`; set `LANGFUSE_HOST` (for example `https://us.cloud.langfuse.com`) if you use a non-default Langfuse region.
- `main.run()` and the example scripts invoke `config.setup_langfuse()` automatically; traces are emitted whenever Langfuse credentials are present.
- To instrument custom code paths, import `setup_langfuse` from `config` or `config.observability` and call it once before configuring DSPy.
- Langfuse uses OpenTelemetry under the hood, so DSPy spans, Tavily tool calls, and GEPA metrics appear in the Langfuse UI for replay and analytics.
- Spans capture vendor coverage (emails, phones, geography) and PESTLE insight counts so you can filter runs by data quality inside Langfuse.

### BootstrapFewShot Seed Pipeline
- Run `python -m optimize.bootstrap_vendor` (or call `optimize.bootstrap_vendor.bootstrap_vendor_agent()` from your own script) to generate synthetic vendor demos when you lack labeled data.
- Bootstrapped demos are written to `data/artifacts/vendor_bootstrap.jsonl` by default and can seed future GEPA runs.
- Adjust `max_bootstrapped_demos`, `max_rounds`, or supply custom seed examples to control how many synthetic traces are collected.



