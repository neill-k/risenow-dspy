"""Example script demonstrating PESTLE analysis usage."""

import logging
logging.basicConfig(level=logging.INFO)
from dotenv import load_dotenv
import dspy

from config.environment import (
    validate_environment,
    get_primary_lm_config,
)
from agents.pestle_agent import create_pestle_agent

# Load environment variables
load_dotenv()

# Validate environment
validate_environment()

# Configure DSPy
primary_config = get_primary_lm_config()
primary_lm = dspy.LM(**primary_config)
dspy.configure(lm=primary_lm)


def demo_pestle_analysis():
    """Demonstrate PESTLE analysis capabilities."""

    print("=" * 60)
    print("PESTLE ANALYSIS DEMO")
    print("=" * 60)

    # Create PESTLE agent
    pestle_agent = create_pestle_agent(use_tools=True, max_iters=30)

    # Example 1: Industrial Supplies Market
    print("\n1. Analyzing General Industrial Supplies Market...")
    result1 = pestle_agent(
        category="General Industrial Supplies",
        region="United States",
        focus_areas=["economic", "technological", "regulatory"]
    )

    if hasattr(result1, 'pestle_analysis'):
        pestle = result1.pestle_analysis
        print(f"\nExecutive Summary: {pestle.executive_summary[:200]}...")
        print(f"Opportunities: {len(pestle.opportunities)} identified")
        print(f"Threats: {len(pestle.threats)} identified")
        print(f"Recommendations: {len(pestle.strategic_recommendations)} provided")

    # Example 2: Cloud Computing Services
    print("\n2. Analyzing Cloud Computing Services Market...")
    result2 = pestle_agent(
        category="Cloud Computing Services",
        region="Europe",
        focus_areas=["legal", "technological", "environmental"]
    )

    if hasattr(result2, 'pestle_analysis'):
        pestle = result2.pestle_analysis
        print(f"\nKey Political Insights:")
        for insight in pestle.political.key_insights[:2]:
            print(f"  - {insight}")

        print(f"\nKey Economic Factors:")
        print(f"  - Market Size: {pestle.economic.market_size}")
        print(f"  - Growth Rate: {pestle.economic.growth_rate}")

    # Example 3: Renewable Energy Solutions (Global)
    print("\n3. Analyzing Renewable Energy Solutions Market (Global)...")
    result3 = pestle_agent(
        category="Renewable Energy Solutions",
        region=None,  # Global analysis
        focus_areas=["environmental", "political", "economic"]
    )

    if hasattr(result3, 'pestle_analysis'):
        pestle = result3.pestle_analysis
        print(f"\nEnvironmental Factors:")
        print(f"  - Climate Impact: {pestle.environmental.climate_impact}")
        print(f"  - Green Initiatives: {len(pestle.environmental.green_initiatives)} identified")

        print(f"\nTop 3 Strategic Recommendations:")
        for i, rec in enumerate(pestle.strategic_recommendations[:3], 1):
            print(f"  {i}. {rec}")


def demo_focused_analysis():
    """Demonstrate focused PESTLE analysis on specific factors."""

    print("\n" + "=" * 60)
    print("FOCUSED PESTLE ANALYSIS DEMO")
    print("=" * 60)

    # Create agent
    agent = create_pestle_agent(use_tools=True, max_iters=20)

    # Focus on technological and legal factors for AI/ML services
    print("\nAnalyzing AI/ML Services with focus on Tech & Legal factors...")
    result = agent(
        category="Artificial Intelligence and Machine Learning Services",
        region="United States",
        focus_areas=["technological", "legal", "intellectual property", "compliance"]
    )

    if hasattr(result, 'pestle_analysis'):
        pestle = result.pestle_analysis

        print(f"\nTechnological Analysis:")
        print(f"  Innovations: {len(pestle.technological.innovations)} key innovations")
        print(f"  Disruptions: {len(pestle.technological.disruptions)} potential disruptions")
        print(f"  Digital Transformation: {pestle.technological.digital_transformation}")

        print(f"\nLegal Analysis:")
        print(f"  Compliance Requirements: {len(pestle.legal.compliance_requirements)} requirements")
        print(f"  IP Considerations: {len(pestle.legal.intellectual_property)} considerations")

        if pestle.legal.key_insights:
            print(f"\nKey Legal Insights:")
            for insight in pestle.legal.key_insights[:3]:
                print(f"  - {insight}")


if __name__ == "__main__":
    # Run demonstrations
    demo_pestle_analysis()
    demo_focused_analysis()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)