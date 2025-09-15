"""Main script for vendor discovery optimization using GEPA and Tavily MCP."""

import asyncio
import dspy
from dspy import GEPA
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

from config.environment import (
    validate_environment, 
    setup_instrumentation, 
    get_tavily_stream_url
)
from models.vendor import VendorSearchResult
from metrics.scoring import make_llm_judge_metric


async def main():
    """Main execution function for vendor discovery optimization."""
    
    # Validate environment and setup instrumentation
    validate_environment()
    setup_instrumentation()
    
    # Configure DSPy with OpenAI models
    # Use a public model that exists today.
    dspy.configure(lm="openai/gpt-4o-mini")
    
    # Create LLM judge metric
    llm_metric = make_llm_judge_metric(max_items=15, include_individual_scores=True)
    
    # Setup GEPA optimizer (configured later once student & trainset are ready)
    gepa_optimizer: GEPA | None = None
    
    # Get Tavily MCP stream URL
    tavily_stream_url = get_tavily_stream_url()
    
    # Connect to Tavily MCP and run vendor search
    async with streamablehttp_client(tavily_stream_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Convert MCP tools to DSPy tools
            dspy_tools = [dspy.Tool.from_mcp_tool(session, t) for t in tools.tools]
            
            # Create ReAct agent with tools
            react = dspy.ReAct(VendorSearchResult, tools=dspy_tools, max_iters=50)
            
            # ------------------------------------------------------------------
            # Build a tiny trainset for GEPA (few-shot reflective optimization)
            # ------------------------------------------------------------------
            trainset = [
                dspy.Example(
                    category="General Industrial Supplies",
                    n=10,
                    country_or_region="United States",
                ).with_inputs("category", "n", "country_or_region"),
                dspy.Example(
                    category="General Industrial Supplies",
                    n=5,
                    country_or_region=None,
                ).with_inputs("category", "n", "country_or_region"),
            ]

            # Instantiate and compile GEPA
            gepa_optimizer = GEPA(metric=llm_metric, auto="light")
            optimized = gepa_optimizer.compile(student=react, trainset=trainset)

            # Run vendor search with the optimized program
            result = await optimized.acall(
                category="General Industrial Supplies",
                n=15,
                country_or_region="United States",
            )
            
            return result


if __name__ == "__main__":
    result = asyncio.run(main())
    print("Vendor discovery completed:")
    print(f"Found {len(result.vendor_list)} vendors")
    for i, vendor in enumerate(result.vendor_list, 1):
        print(f"{i}. {vendor.name} - {vendor.website}")