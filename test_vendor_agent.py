"""Quick test of the vendor discovery agent using DSPy ReAct harness."""

import logging
from typing import List
from datetime import datetime
from pathlib import Path
from pprint import pprint
import io
import sys

import dspy
from config.environment import (
    OPENAI_API_KEY,
    TAVILY_API_KEY,
    get_primary_lm_config,
    validate_environment
)
from config.observability import (
    setup_langfuse,
    observability_span,
    generate_session_id,
    set_span_attributes
)
from models.vendor import VendorSearchResult, Vendor
from tools.web_tools import create_dspy_tools
from agents.vendor_agent import create_vendor_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def capture_inspect_history(n: int = 10) -> str:
    """Capture dspy.inspect_history output as a string."""
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        dspy.inspect_history(n=n)
        output = buffer.getvalue()
    finally:
        sys.stdout = old_stdout
    return output


def write_markdown_report(vendors: List[Vendor], test_inputs: dict, trace_output: str = "", output_dir: str = "outputs"):
    """Write vendor discovery results to a markdown file."""
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"vendor_discovery_{timestamp}.md"
    filepath = output_path / filename

    # Build markdown content
    md_lines = []
    md_lines.append("# Vendor Discovery Report")
    md_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append("\n## Search Parameters")
    md_lines.append(f"- **Category:** {test_inputs['category']}")
    md_lines.append(f"- **Number Requested:** {test_inputs['n']}")
    md_lines.append(f"- **Country/Region:** {test_inputs.get('country_or_region', 'Global')}")
    md_lines.append(f"\n## Results Summary")
    md_lines.append(f"Found **{len(vendors)}** vendors matching the criteria.")

    md_lines.append("\n## Vendor Details\n")

    for i, vendor in enumerate(vendors, 1):
        md_lines.append(f"### {i}. {vendor.name}")
        md_lines.append(f"\n**Website:** [{vendor.website}]({vendor.website})")
        md_lines.append(f"\n**Description:** {vendor.description}")
        md_lines.append(f"\n**Why Selected:** {vendor.justification}")

        if vendor.contact_emails:
            md_lines.append("\n**Contact Emails:**")
            for email in vendor.contact_emails:
                desc = f" ({email.description})" if email.description else ""
                md_lines.append(f"- {email.email}{desc}")

        if vendor.phone_numbers:
            md_lines.append("\n**Phone Numbers:**")
            for phone in vendor.phone_numbers:
                desc = f" ({phone.description})" if phone.description else ""
                md_lines.append(f"- {phone.number}{desc}")

        if vendor.countries_served:
            md_lines.append(f"\n**Countries Served:** {', '.join(vendor.countries_served)}")

        md_lines.append("\n---\n")

    # Add trace information if available
    if trace_output:
        md_lines.append("\n## Agent Execution Trace\n")
        md_lines.append("<details>")
        md_lines.append("<summary>Click to view detailed LLM call history</summary>")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(trace_output)
        md_lines.append("```")
        md_lines.append("</details>")
        md_lines.append("")

    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    return filepath


def main():
    """Run a simple test of the vendor discovery agent."""

    # Validate environment
    logger.info("Validating environment variables...")
    try:
        validate_environment()
        logger.info("Environment validation successful")
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        return

    # Setup Langfuse observability
    logger.info("Setting up Langfuse observability...")
    langfuse_client = setup_langfuse()
    if langfuse_client:
        logger.info("Langfuse tracing enabled")
    else:
        logger.info("Langfuse tracing not configured (optional)")

    # Generate session ID for trace grouping
    session_id = generate_session_id()
    logger.info(f"Session ID: {session_id}")

    # Configure DSPy with the primary language model
    logger.info("Configuring DSPy...")
    lm_config = get_primary_lm_config()
    lm = dspy.LM(
        model=lm_config["model"],
        api_key=OPENAI_API_KEY,
        temperature=lm_config["temperature"],
        max_tokens=lm_config["max_tokens"]
    )
    dspy.settings.configure(lm=lm)
    logger.info(f"DSPy configured with model: {lm_config['model']}")

    # Create the vendor agent with tools (ReAct mode)
    logger.info("Creating vendor discovery agent...")
    agent = create_vendor_agent(use_tools=True, max_iters=30)

    # Define test inputs
    test_inputs = {
        "category": "General Industrial Supplies",
        "n": 15,
        "country_or_region": "United States"
    }

    logger.info("Running vendor discovery agent with inputs:")
    logger.info(f"  Category: {test_inputs['category']}")
    logger.info(f"  Number of vendors: {test_inputs['n']}")
    logger.info(f"  Country/Region: {test_inputs['country_or_region']}")

    # Execute the agent with observability span
    try:
        span_attributes = {
            "test.category": test_inputs['category'],
            "test.n": test_inputs['n'],
            "test.country_or_region": test_inputs.get('country_or_region', 'Global'),
            "test.agent_type": "ReAct",
            "test.use_tools": True,
            "test.max_iters": 30,
            "session.id": session_id
        }

        with observability_span("test_vendor_agent.execute", span_attributes, session_id=session_id) as span:
            logger.info("Executing agent (this may take a moment)...")
            result = agent(**test_inputs)

            # Update span with result counts
            if hasattr(result, 'vendor_list') and result.vendor_list:
                set_span_attributes(span, {
                    "result.vendor_count": len(result.vendor_list),
                    "result.success": True
                })
            else:
                set_span_attributes(span, {
                    "result.vendor_count": 0,
                    "result.success": False
                })

        # Capture DSPy trace history
        logger.info("\n" + "="*60)
        logger.info("CAPTURING LLM CALL HISTORY")
        logger.info("="*60)
        trace_output = capture_inspect_history(n=10)

        # Display results
        logger.info("\n" + "="*60)
        logger.info("VENDOR DISCOVERY RESULTS")
        logger.info("="*60)

        if hasattr(result, 'vendor_list') and result.vendor_list:
            vendors: List[Vendor] = result.vendor_list
            logger.info(f"\nFound {len(vendors)} vendors:\n")

            for i, vendor in enumerate(vendors, 1):
                print(f"\n--- Vendor {i} ---")
                print(f"Name: {vendor.name}")
                print(f"Website: {vendor.website}")
                print(f"Description: {vendor.description}")
                print(f"Justification: {vendor.justification}")

                if vendor.contact_emails:
                    print(f"Emails: {', '.join([e.email for e in vendor.contact_emails])}")

                if vendor.phone_numbers:
                    print(f"Phone: {', '.join([p.number for p in vendor.phone_numbers])}")

                if vendor.countries_served:
                    print(f"Countries: {', '.join(vendor.countries_served)}")

            # Write results to markdown file with trace
            output_file = write_markdown_report(vendors, test_inputs, trace_output)
            logger.info(f"\n✅ Results saved to: {output_file}")
        else:
            logger.warning("No vendors found in the result")

        # Display LLM trace history to console (optional)
        logger.info("\n" + "="*60)
        logger.info("LLM CALL TRACE (Last 10 Calls)")
        logger.info("="*60)
        print(trace_output[:5000])  # Limit console output
        if len(trace_output) > 5000:
            print(f"\n... (truncated, full trace saved to markdown report)")

    except Exception as e:
        logger.error(f"Error executing agent: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\nTest complete!")


if __name__ == "__main__":
    main()