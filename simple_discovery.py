"""Simple vendor discovery script without GEPA optimization."""

import asyncio
import dspy
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

from config.environment import (
    validate_environment, 
    setup_instrumentation, 
    get_tavily_stream_url
)
from models.vendor import VendorSearchResult
from metrics.scoring import make_llm_judge_metric


async def run_vendor_discovery():
    """Run vendor discovery using ReAct agent with Tavily tools."""
    
    # Validate environment and setup instrumentation
    validate_environment()
    setup_instrumentation()
    
    # Configure DSPy with OpenAI models
    dspy.configure(lm="openai/gpt-4o-mini")
    
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
            
            # Run vendor search
            result = await react.acall(
                category="General Industrial Supplies", 
                n=15,
                country_or_region="United States"
            )
            
            return result


def evaluate_vendors(vendor_list):
    """Evaluate vendor list using the LLM judge metric."""
    llm_metric = make_llm_judge_metric(max_items=15, include_individual_scores=True)
    
    # Create a simple prediction object for evaluation
    class VendorPrediction:
        def __init__(self, vendors):
            self.vendor_list = vendors
    
    # Create a simple gold object
    gold = {
        "category": "General Industrial Supplies",
        "country_or_region": "United States"
    }
    
    pred = VendorPrediction(vendor_list)
    evaluation = llm_metric(gold, pred)
    
    return evaluation


async def main():
    """Main execution function."""
    print("Starting vendor discovery...")
    
    try:
        # Run vendor discovery
        result = await run_vendor_discovery()
        
        print(f"\n✅ Vendor discovery completed!")
        print(f"Found {len(result.vendor_list)} vendors:\n")
        
        # Display results
        for i, vendor in enumerate(result.vendor_list, 1):
            print(f"{i:2d}. {vendor.name}")
            print(f"    Website: {vendor.website}")
            print(f"    Description: {vendor.description[:100]}...")
            if vendor.contact_emails:
                print(f"    Email: {vendor.contact_emails[0].email}")
            if vendor.countries_served:
                print(f"    Countries: {', '.join(vendor.countries_served[:3])}")
            print()
        
        # Evaluate the results
        print("Evaluating vendor list quality...")
        evaluation = evaluate_vendors(result.vendor_list)
        print(f"Quality Score: {evaluation.score:.2f}")
        print(f"Feedback: {evaluation.feedback}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during vendor discovery: {e}")
        raise


if __name__ == "__main__":
    result = asyncio.run(main())