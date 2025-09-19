"""Quick test of the PESTLE analysis agent using DSPy ReAct harness."""

import logging
from typing import Optional
from datetime import datetime
from pathlib import Path
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
from models.pestle import PESTLEAnalysis
from tools.web_tools import create_dspy_tools
from agents.pestle_agent import create_pestle_agent

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


def write_markdown_report(analysis: PESTLEAnalysis, test_inputs: dict, trace_output: str = "", output_dir: str = "outputs"):
    """Write PESTLE analysis results to a markdown file."""
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pestle_analysis_{timestamp}.md"
    filepath = output_path / filename

    # Build markdown content
    md_lines = []
    md_lines.append("# PESTLE Analysis Report")
    md_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append("\n## Analysis Parameters")
    md_lines.append(f"- **Category:** {test_inputs['category']}")
    md_lines.append(f"- **Region:** {test_inputs.get('region', 'Global')}")
    if test_inputs.get('focus_areas'):
        md_lines.append(f"- **Focus Areas:** {', '.join(test_inputs['focus_areas'])}")

    md_lines.append(f"\n## Executive Summary")
    md_lines.append(f"\n{analysis.executive_summary}")

    # Political Factors
    md_lines.append("\n## Political Factors")
    md_lines.append(f"\n**Political Stability:** {analysis.political.political_stability}")
    if analysis.political.government_policies:
        md_lines.append("\n**Government Policies:**")
        for policy in analysis.political.government_policies:
            md_lines.append(f"- {policy}")
    if analysis.political.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.political.key_insights:
            md_lines.append(f"- {insight}")

    # Economic Factors
    md_lines.append("\n## Economic Factors")
    md_lines.append(f"\n**Market Size:** {analysis.economic.market_size}")
    md_lines.append(f"\n**Growth Rate:** {analysis.economic.growth_rate}")
    md_lines.append(f"\n**Investment Climate:** {analysis.economic.investment_climate}")
    if analysis.economic.market_trends:
        md_lines.append("\n**Market Trends:**")
        for trend in analysis.economic.market_trends:
            md_lines.append(f"- {trend}")
    if analysis.economic.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.economic.key_insights:
            md_lines.append(f"- {insight}")

    # Social Factors
    md_lines.append("\n## Social Factors")
    if analysis.social.consumer_trends:
        md_lines.append("\n**Consumer Trends:**")
        for trend in analysis.social.consumer_trends:
            md_lines.append(f"- {trend}")
    if analysis.social.lifestyle_changes:
        md_lines.append("\n**Lifestyle Changes:**")
        for change in analysis.social.lifestyle_changes:
            md_lines.append(f"- {change}")
    if analysis.social.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.social.key_insights:
            md_lines.append(f"- {insight}")

    # Technological Factors
    md_lines.append("\n## Technological Factors")
    md_lines.append(f"\n**Digital Transformation:** {analysis.technological.digital_transformation}")
    md_lines.append(f"\n**Automation Impact:** {analysis.technological.automation_impact}")
    if analysis.technological.innovations:
        md_lines.append("\n**Key Innovations:**")
        for innovation in analysis.technological.innovations:
            md_lines.append(f"- {innovation}")
    if analysis.technological.emerging_technologies:
        md_lines.append("\n**Emerging Technologies:**")
        for tech in analysis.technological.emerging_technologies:
            md_lines.append(f"- {tech}")
    if analysis.technological.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.technological.key_insights:
            md_lines.append(f"- {insight}")

    # Legal Factors
    md_lines.append("\n## Legal Factors")
    if analysis.legal.compliance_requirements:
        md_lines.append("\n**Compliance Requirements:**")
        for req in analysis.legal.compliance_requirements:
            md_lines.append(f"- {req}")
    if analysis.legal.legal_changes:
        md_lines.append("\n**Recent/Upcoming Legal Changes:**")
        for change in analysis.legal.legal_changes:
            md_lines.append(f"- {change}")
    if analysis.legal.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.legal.key_insights:
            md_lines.append(f"- {insight}")

    # Environmental Factors
    md_lines.append("\n## Environmental Factors")
    md_lines.append(f"\n**Climate Impact:** {analysis.environmental.climate_impact}")
    if analysis.environmental.sustainability_requirements:
        md_lines.append("\n**Sustainability Requirements:**")
        for req in analysis.environmental.sustainability_requirements:
            md_lines.append(f"- {req}")
    if analysis.environmental.green_initiatives:
        md_lines.append("\n**Green Initiatives:**")
        for initiative in analysis.environmental.green_initiatives:
            md_lines.append(f"- {initiative}")
    if analysis.environmental.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.environmental.key_insights:
            md_lines.append(f"- {insight}")

    # Strategic Analysis
    md_lines.append("\n## Strategic Analysis")

    if analysis.opportunities:
        md_lines.append("\n### Opportunities")
        for opp in analysis.opportunities:
            md_lines.append(f"- {opp}")

    if analysis.threats:
        md_lines.append("\n### Threats")
        for threat in analysis.threats:
            md_lines.append(f"- {threat}")

    if analysis.strategic_recommendations:
        md_lines.append("\n### Strategic Recommendations")
        for rec in analysis.strategic_recommendations:
            md_lines.append(f"- {rec}")

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
    """Run a simple test of the PESTLE analysis agent."""

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

    # Create the PESTLE agent with tools (ReAct mode)
    logger.info("Creating PESTLE analysis agent...")
    agent = create_pestle_agent(use_tools=True, max_iters=60)

    # Define test inputs
    test_inputs = {
        "category": "General Industrial Supplies",
        "region": "United States",
        "focus_areas": None
    }

    logger.info("Running PESTLE analysis with inputs:")
    logger.info(f"  Category: {test_inputs['category']}")
    logger.info(f"  Region: {test_inputs['region']}")
    logger.info(f"  Focus Areas: {test_inputs['focus_areas'] or 'None'}")

    # Execute the agent with observability span
    try:
        span_attributes = {
            "test.category": test_inputs['category'],
            "test.region": test_inputs.get('region', 'Global'),
            "test.agent_type": "ReAct",
            "test.use_tools": True,
            "test.max_iters": 60,
            "session.id": session_id
        }

        with observability_span("test_pestle_agent.execute", span_attributes, session_id=session_id) as span:
            logger.info("Executing agent (this may take a moment)...")
            result = agent(**test_inputs)

            # Update span with result status
            if hasattr(result, 'pestle_analysis') and result.pestle_analysis:
                set_span_attributes(span, {
                    "result.has_analysis": True,
                    "result.success": True
                })
            else:
                set_span_attributes(span, {
                    "result.has_analysis": False,
                    "result.success": False
                })

        # Capture DSPy trace history
        logger.info("\n" + "="*60)
        logger.info("CAPTURING LLM CALL HISTORY")
        logger.info("="*60)
        trace_output = capture_inspect_history(n=10)

        # Display results
        logger.info("\n" + "="*60)
        logger.info("PESTLE ANALYSIS RESULTS")
        logger.info("="*60)

        if hasattr(result, 'pestle_analysis') and result.pestle_analysis:
            analysis: PESTLEAnalysis = result.pestle_analysis

            print(f"\n📊 PESTLE Analysis for: {analysis.category}")
            print(f"📍 Region: {analysis.region or 'Global'}")
            print(f"\n📝 Executive Summary:")
            print(f"   {analysis.executive_summary}")

            print(f"\n🏛️ Political: {analysis.political.political_stability}")
            if analysis.political.key_insights:
                print(f"   Key Insight: {analysis.political.key_insights[0]}")

            print(f"\n💰 Economic: Market Size - {analysis.economic.market_size}")
            print(f"   Growth Rate: {analysis.economic.growth_rate}")

            print(f"\n👥 Social: {len(analysis.social.consumer_trends)} consumer trends identified")

            print(f"\n💻 Technological: {analysis.technological.digital_transformation}")

            print(f"\n⚖️ Legal: {len(analysis.legal.compliance_requirements)} compliance requirements")

            print(f"\n🌱 Environmental: {analysis.environmental.climate_impact}")

            print(f"\n✅ Opportunities: {len(analysis.opportunities)} identified")
            for i, opp in enumerate(analysis.opportunities[:3], 1):
                print(f"   {i}. {opp}")

            print(f"\n⚠️ Threats: {len(analysis.threats)} identified")
            for i, threat in enumerate(analysis.threats[:3], 1):
                print(f"   {i}. {threat}")

            print(f"\n🎯 Strategic Recommendations: {len(analysis.strategic_recommendations)} provided")
            for i, rec in enumerate(analysis.strategic_recommendations[:3], 1):
                print(f"   {i}. {rec}")

            # Write results to markdown file with trace
            output_file = write_markdown_report(analysis, test_inputs, trace_output)
            logger.info(f"\n✅ Results saved to: {output_file}")
        else:
            logger.warning("No PESTLE analysis found in the result")

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