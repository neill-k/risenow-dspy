# DSPy Rewrite - Vendor Discovery System

This is a reorganized version of the vendor discovery system, extracted from the Jupyter notebook and organized into logical modules.

## Structure

```
dspy_rewrite/
├── __init__.py                 # Main package init
├── main.py                     # Main script for running vendor discovery
├── config/
│   ├── __init__.py
│   └── environment.py          # Environment setup and configuration
├── models/
│   ├── __init__.py
│   └── vendor.py              # Pydantic models and DSPy signatures
├── tools/
│   ├── __init__.py
│   └── web_tools.py           # Web search and page fetching utilities
├── metrics/
│   ├── __init__.py
│   └── scoring.py             # Vendor scoring and evaluation metrics
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
- **vendor.py**: Contains all Pydantic models and DSPy signatures
  - `ContactEmail`: Email contact information
  - `PhoneNumber`: Phone contact information  
  - `Vendor`: Complete vendor information model
  - `VendorSearchResult`: DSPy signature for vendor discovery
  - `JudgeVendors`: DSPy signature for vendor evaluation

### Tools (`tools/`)
- **web_tools.py**: Web search and page fetching functionality
  - `search_web()`: Tavily-based web search
  - `get_page()`: HTTP page fetching and parsing
  - `create_dspy_tools()`: Factory for DSPy tool instances

### Metrics (`metrics/`)
- **scoring.py**: Vendor quality scoring and evaluation
  - Phone number validation scoring
  - Email validation scoring
  - Geographic coverage scoring
  - LLM-based vendor list evaluation

### Data (`data/`)
- **examples.py**: Example data for testing and training
  - `general_industrial_supplies_example_n15`: Sample vendor list for industrial supplies

## Usage

The main script can be run to perform vendor discovery:

```python
python main.py
```

This will:
1. Validate environment variables
2. Set up DSPy configuration and instrumentation
3. Connect to Tavily MCP for web search tools
4. Use GEPA optimization to improve vendor discovery
5. Return a list of vendors for the specified category

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

Required environment variables:
- `OPENAI_API_KEY`: OpenAI API key
- `LANGFUSE_PUBLIC_KEY`: Langfuse public key for tracing
- `LANGFUSE_SECRET_KEY`: Langfuse secret key for tracing
- `TAVILY_API_KEY`: Tavily API key for web search
- `LANGFUSE_HOST`: Langfuse host URL (optional, defaults to US cloud)