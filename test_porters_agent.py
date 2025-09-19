"""Quick test of the Porter's 5 Forces analysis agent using DSPy ReAct harness."""

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
from models.porters import PortersFiveForcesAnalysis
from tools.web_tools import create_dspy_tools
from agents.porters_agent import create_porters_agent

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


def write_markdown_report(analysis: PortersFiveForcesAnalysis, test_inputs: dict, trace_output: str = "", output_dir: str = "outputs"):
    """Write Porter's 5 Forces analysis results to a markdown file."""
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"porters_analysis_{timestamp}.md"
    filepath = output_path / filename

    # Build markdown content
    md_lines = []
    md_lines.append("# Porter's 5 Forces Analysis Report")
    md_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append("\n## Analysis Parameters")
    md_lines.append(f"- **Category:** {test_inputs['category']}")
    md_lines.append(f"- **Region:** {test_inputs.get('region', 'Global')}")
    if test_inputs.get('focus_areas'):
        md_lines.append(f"- **Focus Areas:** {', '.join(test_inputs['focus_areas'])}")

    md_lines.append(f"\n## Executive Summary")
    md_lines.append(f"\n{analysis.executive_summary}")

    md_lines.append(f"\n## Industry Attractiveness")
    md_lines.append(f"\n{analysis.industry_attractiveness}")

    # Force 1: Threat of New Entrants
    md_lines.append("\n## 1️⃣ Threat of New Entrants")
    md_lines.append(f"\n**Threat Level:** {analysis.threat_of_new_entrants.threat_level}")
    md_lines.append(f"\n**Capital Requirements:** {analysis.threat_of_new_entrants.capital_requirements}")
    md_lines.append(f"\n**Economies of Scale:** {analysis.threat_of_new_entrants.economies_of_scale}")
    md_lines.append(f"\n**Brand Loyalty:** {analysis.threat_of_new_entrants.brand_loyalty}")
    if analysis.threat_of_new_entrants.barriers_to_entry:
        md_lines.append("\n**Barriers to Entry:**")
        for barrier in analysis.threat_of_new_entrants.barriers_to_entry:
            md_lines.append(f"- {barrier}")
    if analysis.threat_of_new_entrants.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.threat_of_new_entrants.key_insights:
            md_lines.append(f"- {insight}")

    # Force 2: Bargaining Power of Suppliers
    md_lines.append("\n## 2️⃣ Bargaining Power of Suppliers")
    md_lines.append(f"\n**Power Level:** {analysis.bargaining_power_suppliers.power_level}")
    md_lines.append(f"\n**Supplier Concentration:** {analysis.bargaining_power_suppliers.supplier_concentration}")
    md_lines.append(f"\n**Switching Costs:** {analysis.bargaining_power_suppliers.switching_costs}")
    md_lines.append(f"\n**Forward Integration Threat:** {analysis.bargaining_power_suppliers.forward_integration_threat}")
    md_lines.append(f"\n**Supplier Dependency:** {analysis.bargaining_power_suppliers.supplier_dependency}")
    if analysis.bargaining_power_suppliers.unique_resources:
        md_lines.append("\n**Unique Resources:**")
        for resource in analysis.bargaining_power_suppliers.unique_resources:
            md_lines.append(f"- {resource}")
    if analysis.bargaining_power_suppliers.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.bargaining_power_suppliers.key_insights:
            md_lines.append(f"- {insight}")

    # Force 3: Bargaining Power of Buyers
    md_lines.append("\n## 3️⃣ Bargaining Power of Buyers")
    md_lines.append(f"\n**Power Level:** {analysis.bargaining_power_buyers.power_level}")
    md_lines.append(f"\n**Buyer Concentration:** {analysis.bargaining_power_buyers.buyer_concentration}")
    md_lines.append(f"\n**Price Sensitivity:** {analysis.bargaining_power_buyers.price_sensitivity}")
    md_lines.append(f"\n**Switching Costs:** {analysis.bargaining_power_buyers.switching_costs}")
    md_lines.append(f"\n**Backward Integration Threat:** {analysis.bargaining_power_buyers.backward_integration_threat}")
    md_lines.append(f"\n**Information Availability:** {analysis.bargaining_power_buyers.information_availability}")
    if analysis.bargaining_power_buyers.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.bargaining_power_buyers.key_insights:
            md_lines.append(f"- {insight}")

    # Force 4: Threat of Substitutes
    md_lines.append("\n## 4️⃣ Threat of Substitute Products/Services")
    md_lines.append(f"\n**Threat Level:** {analysis.threat_of_substitutes.threat_level}")
    md_lines.append(f"\n**Price-Performance:** {analysis.threat_of_substitutes.relative_price_performance}")
    md_lines.append(f"\n**Switching Costs:** {analysis.threat_of_substitutes.switching_costs}")
    md_lines.append(f"\n**Buyer Propensity:** {analysis.threat_of_substitutes.buyer_propensity_to_substitute}")
    if analysis.threat_of_substitutes.substitute_products:
        md_lines.append("\n**Key Substitutes:**")
        for substitute in analysis.threat_of_substitutes.substitute_products:
            md_lines.append(f"- {substitute}")
    if analysis.threat_of_substitutes.innovation_trends:
        md_lines.append("\n**Innovation Trends:**")
        for trend in analysis.threat_of_substitutes.innovation_trends:
            md_lines.append(f"- {trend}")
    if analysis.threat_of_substitutes.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.threat_of_substitutes.key_insights:
            md_lines.append(f"- {insight}")

    # Force 5: Competitive Rivalry
    md_lines.append("\n## 5️⃣ Competitive Rivalry")
    md_lines.append(f"\n**Intensity Level:** {analysis.competitive_rivalry.intensity_level}")
    md_lines.append(f"\n**Industry Concentration:** {analysis.competitive_rivalry.industry_concentration}")
    md_lines.append(f"\n**Growth Rate:** {analysis.competitive_rivalry.industry_growth_rate}")
    md_lines.append(f"\n**Differentiation Level:** {analysis.competitive_rivalry.differentiation_level}")
    if analysis.competitive_rivalry.major_competitors:
        md_lines.append("\n**Major Competitors:**")
        for competitor in analysis.competitive_rivalry.major_competitors:
            md_lines.append(f"- {competitor}")
    if analysis.competitive_rivalry.competitive_strategies:
        md_lines.append("\n**Common Strategies:**")
        for strategy in analysis.competitive_rivalry.competitive_strategies:
            md_lines.append(f"- {strategy}")
    if analysis.competitive_rivalry.exit_barriers:
        md_lines.append("\n**Exit Barriers:**")
        for barrier in analysis.competitive_rivalry.exit_barriers:
            md_lines.append(f"- {barrier}")
    if analysis.competitive_rivalry.key_insights:
        md_lines.append("\n**Key Insights:**")
        for insight in analysis.competitive_rivalry.key_insights:
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
    """Run a simple test of the Porter's 5 Forces analysis agent."""

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

    # Create the Porter's agent with tools (ReAct mode)
    logger.info("Creating Porter's 5 Forces analysis agent...")
    agent = create_porters_agent(use_tools=True, max_iters=60)

    # Define test inputs
    test_inputs = {
        "category": "General Industrial Supplies",
        "region": "United States",
        "focus_areas": None
    }

    logger.info("Running Porter's 5 Forces analysis with inputs:")
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

        with observability_span("test_porters_agent.execute", span_attributes, session_id=session_id) as span:
            logger.info("Executing agent (this may take a moment)...")
            result = agent(**test_inputs)

            # Update span with result status
            if hasattr(result, 'porters_analysis') and result.porters_analysis:
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
        logger.info("PORTER'S 5 FORCES ANALYSIS RESULTS")
        logger.info("="*60)

        if hasattr(result, 'porters_analysis') and result.porters_analysis:
            analysis: PortersFiveForcesAnalysis = result.porters_analysis

            print(f"\n💼 Porter's 5 Forces Analysis for: {analysis.category}")
            print(f"📍 Region: {analysis.region or 'Global'}")
            print(f"\n📝 Executive Summary:")
            print(f"   {analysis.executive_summary}")
            print(f"\n🎯 Industry Attractiveness: {analysis.industry_attractiveness}")

            print(f"\n=== FIVE FORCES SUMMARY ===")

            print(f"\n1️⃣ Threat of New Entrants: {analysis.threat_of_new_entrants.threat_level}")
            print(f"   Capital Requirements: {analysis.threat_of_new_entrants.capital_requirements}")
            if analysis.threat_of_new_entrants.key_insights:
                print(f"   Key Insight: {analysis.threat_of_new_entrants.key_insights[0]}")

            print(f"\n2️⃣ Supplier Power: {analysis.bargaining_power_suppliers.power_level}")
            print(f"   Concentration: {analysis.bargaining_power_suppliers.supplier_concentration}")
            if analysis.bargaining_power_suppliers.key_insights:
                print(f"   Key Insight: {analysis.bargaining_power_suppliers.key_insights[0]}")

            print(f"\n3️⃣ Buyer Power: {analysis.bargaining_power_buyers.power_level}")
            print(f"   Price Sensitivity: {analysis.bargaining_power_buyers.price_sensitivity}")
            if analysis.bargaining_power_buyers.key_insights:
                print(f"   Key Insight: {analysis.bargaining_power_buyers.key_insights[0]}")

            print(f"\n4️⃣ Threat of Substitutes: {analysis.threat_of_substitutes.threat_level}")
            if analysis.threat_of_substitutes.substitute_products:
                print(f"   Main Substitute: {analysis.threat_of_substitutes.substitute_products[0]}")
            if analysis.threat_of_substitutes.key_insights:
                print(f"   Key Insight: {analysis.threat_of_substitutes.key_insights[0]}")

            print(f"\n5️⃣ Competitive Rivalry: {analysis.competitive_rivalry.intensity_level}")
            print(f"   Market Growth: {analysis.competitive_rivalry.industry_growth_rate}")
            if analysis.competitive_rivalry.major_competitors:
                print(f"   Top Competitor: {analysis.competitive_rivalry.major_competitors[0]}")

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
            logger.warning("No Porter's 5 Forces analysis found in the result")

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