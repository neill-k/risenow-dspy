"""Main script for vendor discovery optimization using GEPA and Tavily MCP."""

import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from typing import Any
import dspy
from dspy import GEPA, Prediction
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

from config.environment import (
    validate_environment, 
    setup_instrumentation, 
    get_tavily_stream_url,
    get_gepa_settings,
)
from models.vendor import VendorSearchResult
from metrics.scoring import make_llm_judge_metric

logger = logging.getLogger(__name__)


async def main():
    """Main execution function for vendor discovery optimization."""
    
    # Validate environment and setup instrumentation
    validate_environment()
    setup_instrumentation()
    
    # Configure DSPy with OpenAI models
    primary_lm = dspy.LM(model="openai/gpt-5-mini", temperature=1, max_tokens=100000)
    dspy.configure(lm=primary_lm, allow_tool_async_sync_conversion=True)
    reflection_lm = dspy.LM(model="openai/gpt-5", temperature=1, max_tokens=32000)
    
    # Create LLM judge metric
    llm_metric = make_llm_judge_metric(max_items=15, include_individual_scores=True)
    metric_call_count = 0

    def gepa_metric(
        gold: Any,
        pred: Any,
        trace: Any | None = None,
        pred_name: str | None = None,
        pred_trace: Any | None = None,
    ) -> dict[str, Any]:
        nonlocal metric_call_count
        metric_call_count += 1
        raw = llm_metric(gold, pred, trace, pred_name, pred_trace)
        if isinstance(raw, Prediction):
            score = float(getattr(raw, "score", 0.0) or 0.0)
            feedback = (getattr(raw, "feedback", "") or "").strip()
        elif isinstance(raw, dict):
            score = float(raw.get("score", 0.0) or 0.0)
            feedback = str(raw.get("feedback", "") or "").strip()
        else:
            score = float(raw or 0.0)
            feedback = f"Scored {score:.2f}."
        logger.info("GEPA metric call %s -> score %.3f", metric_call_count, score)
        return {"score": score, "feedback": feedback or f"Scored {score:.2f}."}


    # Configure GEPA behaviour from environment variables
    gepa_settings = get_gepa_settings()
    gepa_enabled = gepa_settings["enabled"]
    gepa_max_metric_calls = max(0, gepa_settings["max_metric_calls"])
    gepa_num_threads = max(1, gepa_settings["num_threads"])
    
    # Get Tavily MCP stream URL
    tavily_stream_url = get_tavily_stream_url()
    
    # Connect to Tavily MCP and run vendor search
    async with streamablehttp_client(tavily_stream_url) as (read, write, _):
        print("Connected to Tavily MCP stream.")
        async with ClientSession(read, write) as session:
            print("Initialized Tavily MCP client session.")
            await session.initialize()
            # List available tools from MCP
            print("Listing available tools from MCP...")
            tools = await session.list_tools()
            print(f"Retrieved {len(tools.tools)} tools from MCP.")
            # Convert MCP tools to DSPy tools
            dspy_tools = [dspy.Tool.from_mcp_tool(session, t) for t in tools.tools]
            print(f"Converted {len(dspy_tools)} MCP tools to DSPy tools.")
            # Create ReAct agent with tools
            react = dspy.ReAct(VendorSearchResult, tools=dspy_tools, max_iters=50)
            print("Created ReAct agent with DSPy tools.")
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
            print(f"Constructed GEPA trainset with {len(trainset)} examples.")

            # Optionally run GEPA compile step (can be disabled or tuned via env)
            optimized_program = react
            if gepa_enabled and gepa_max_metric_calls > 0:
                effective_max_calls = max(len(trainset), gepa_max_metric_calls)
                gepa_optimizer = GEPA(
                    metric=gepa_metric,
                    reflection_lm=reflection_lm,
                    max_metric_calls=effective_max_calls,
                    num_threads=gepa_num_threads,
                )
                print("Starting GEPA optimization...")
                optimized_program = gepa_optimizer.compile(student=react, trainset=trainset)
                print("GEPA optimization completed.")
                logger.info(
                    "GEPA compile running with max_metric_calls=%s",
                    effective_max_calls,
                )
            else:
                if not gepa_enabled:
                    logger.info("GEPA disabled via GEPA_ENABLED; running base agent.")
                else:
                    logger.info("GEPA_MAX_METRIC_CALLS <= 0; running base agent.")

            # Run vendor search with the optimized (or base) program
            result = await optimized_program.acall(
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
