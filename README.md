# DSPy Complete Analysis Pipeline: Vendor Discovery → Market Analysis → RFP Generation

A comprehensive DSPy-based system that executes a complete procurement analysis pipeline: parallel vendor discovery, market analysis (PESTLE & Porter's), vendor-specific SWOT assessments, and automated RFP question generation. The system leverages Tavily-powered research, GEPA optimization, and structured Pydantic models for deterministic, auditable results.

## Repository Structure

```
risenow-dspy/
├── __init__.py                 # Package init
├── main.py                     # Vendor discovery orchestration entry point
├── agents/                     # Agent implementations
│   ├── pestle_agent.py         # PESTLE analysis agent
│   ├── porters_agent.py        # Porter's 5 Forces agent
│   ├── swot_agent.py           # Vendor SWOT agent
│   ├── vendor_agent.py         # Vendor discovery agent
│   └── rfp_agent.py            # Isolated RFP generation agent
├── config/                     # Environment + observability utilities
│   ├── environment.py          # API key validation and LM config
│   └── observability.py        # Langfuse/OpenInference instrumentation
├── data/
│   ├── examples.py             # Legacy fixtures
│   └── rfp_examples.py         # RFP agent sample payloads
├── metrics/
│   ├── scoring.py              # Vendor scoring helpers
│   ├── pestle_scoring.py       # PESTLE quality metrics
│   └── rfp_scoring.py          # RFP question-set metrics
├── models/
│   ├── pestle.py               # PESTLE models & signatures
│   ├── porters.py              # Porter's 5 Forces models & signatures
│   ├── rfp.py                  # RFP models & signatures
│   ├── swot.py                 # SWOT models & signatures
│   └── vendor.py               # Vendor models & signatures
├── tools/
│   └── web_tools.py            # Tavily-based DSPy tools
└── tests/
    └── test_rfp_agent.py       # Stubbed RFP agent tests
```

## Key Components

### Agents (`agents/`)
- **vendor_agent.py**: ReAct/Chain-of-Thought agent that surfaces vendors, with GEPA optimization helpers and persistence.
- **pestle_agent.py**: Market macro analysis across political, economic, social, technological, legal, and environmental factors.
- **porters_agent.py**: Competitive landscape analysis following Porter's 5 Forces.
- **swot_agent.py**: Vendor-specific SWOT assessment with caching and batch helpers.
- **rfp_agent.py**: Isolated pipeline that extracts insights from prior analyses, mines public RFP references, and generates 100 categorized questions.

### Models (`models/`)
Pydantic models describe agent IO, while DSPy signatures formalize prompts. New `rfp.py` introduces `RFPQuestion`, `RFPSection`, `RFPQuestionSet`, and the supporting signatures for insight extraction, reference gathering, and question generation.

### Metrics (`metrics/`)
`rfp_scoring.py` complements existing vendor and PESTLE metrics with heuristics (question count, section balance, reference coverage, uniqueness) plus an LLM judge factory for RFP evaluations.

### Data & Tests
`data/rfp_examples.py` seeds trainsets with realistic payloads. `tests/test_rfp_agent.py` stubs DSPy modules to validate the RFP pipeline without network access and ensures heuristics behave as expected.

## Complete Pipeline Architecture

The system now includes a comprehensive analysis pipeline that executes in three phases:

### Phase 1: Parallel Analysis
- **Vendor Discovery**: Identifies N vendors in the specified category/region
- **PESTLE Analysis**: Macro-environmental factors assessment
- **Porter's Five Forces**: Industry competitiveness analysis

### Phase 2: SWOT Analysis
- Analyzes top K vendors from Phase 1
- Generates detailed SWOT assessments
- Can run in parallel for multiple vendors

### Phase 3: RFP Generation
- Synthesizes all previous analyses
- Generates comprehensive RFP question set
- Produces categorized, contextual questions

## Quick Start

### Setup
1. Create a virtual environment (`python -m venv .venv && . .venv/bin/activate` or `.venv\Scripts\Activate.ps1`).
2. Install dependencies (`pip install -e .` or `pip install -r requirements.txt`).
3. Export required keys: `OPENAI_API_KEY`, `TAVILY_API_KEY`; optional Langfuse keys add observability. Set `TAVILY_MAX_EXTRACT_CALLS` to tune the Tavily extract budget (default 24).

### Run Complete Pipeline
```python
python main.py  # Runs the complete pipeline with defaults
```

Or use the test script:
```python
python test_complete_pipeline.py  # Detailed pipeline demo with formatted output
```

## Usage Examples

### Complete Pipeline (Recommended)

```python
from main import run_complete_pipeline

# Execute full analysis pipeline
result = run_complete_pipeline(
    category="Cloud Infrastructure Solutions",
    n_vendors=15,                    # Number of vendors to discover
    region="United States",
    swot_top_n=5,                    # Top vendors for SWOT analysis
    expected_rfp_questions=100,      # Target RFP question count
    optimize_if_missing=True,        # Auto-optimize agents if needed
    reuse_cached_programs=True,      # Use cached optimized programs
)

# Access results
print(f"Vendors found: {len(result.vendor_list)}")
print(f"PESTLE complete: {result.pestle_analysis is not None}")
print(f"Porter's complete: {result.porters_analysis is not None}")
print(f"SWOT analyses: {len(result.swot_analyses)}")
print(f"RFP questions: {result.rfp_question_set.total_questions}")
```

### RFP Agent Usage (Isolated)

```python
from agents.rfp_agent import generate_rfp_question_set

rfp_questions = generate_rfp_question_set(
    category="Industrial IoT Platforms",
    region="North America",
    pestle_analysis={"economic": {"key_insights": ["Capex scrutiny"]}},
    porters_analysis={"competitive_rivalry": "High"},
    swot_analyses=[{"vendor_name": "Vendor A", "strengths": {"key_insights": ["Edge coverage"]}}],
    vendor_list=[{"name": "Vendor A"}, {"name": "Vendor B"}],
    use_tools=False,
)
print(rfp_questions.total_questions)
for section in rfp_questions.sections:
    print(section.name, len(section.questions))
```

The helper sets up the isolated pipeline; swap `use_tools=True` to enable Tavily-backed reference searches in production environments.
