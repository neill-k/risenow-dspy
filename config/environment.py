"""Environment configuration and setup for the vendor discovery system."""

import os
from dotenv import load_dotenv
from openinference.instrumentation.dspy import DSPyInstrumentor

# Load environment variables
load_dotenv()

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def validate_environment():
    """Validate that all required environment variables are present."""
    if not OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY environment variable")
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        raise ValueError("Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY environment variable")
    if not TAVILY_API_KEY:
        raise ValueError("Missing TAVILY_API_KEY environment variable")

def setup_instrumentation():
    """Set up DSPy instrumentation for tracing."""
    DSPyInstrumentor().instrument()

def get_tavily_stream_url():
    """Get the Tavily MCP stream URL with API key."""
    return f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"