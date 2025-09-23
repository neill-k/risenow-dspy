"""Bootstrap optimization for SWOT analysis agent."""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import dspy
from dspy import Example, BootstrapFewShot

from agents.swot_agent import create_swot_agent
from metrics.swot_scoring import make_swot_llm_judge_metric
from models.swot import SWOTAnalysis

logger = logging.getLogger(__name__)


def bootstrap_swot_agent(
    seed_vendors: Optional[List[Dict[str, Any]]] = None,
    max_bootstrapped_demos: int = 10,
    max_rounds: int = 3,
    use_tools: bool = True,
    save_path: Optional[str] = None
) -> dspy.Module:
    """
    Bootstrap a SWOT agent using BootstrapFewShot with synthetic examples.

    Parameters
    ----------
    seed_vendors : List[Dict], optional
        Seed vendor examples for bootstrapping
    max_bootstrapped_demos : int
        Maximum number of demonstrations to generate
    max_rounds : int
        Maximum bootstrapping rounds
    use_tools : bool
        Whether to use Tavily tools
    save_path : str, optional
        Path to save bootstrapped demos

    Returns
    -------
    dspy.Module
        Bootstrapped SWOT agent with demonstrations
    """
    logger.info(f"Starting SWOT bootstrap with max {max_bootstrapped_demos} demos")

    # Default seed vendors if none provided
    if seed_vendors is None:
        seed_vendors = [
            {
                "vendor_name": "Grainger",
                "vendor_website": "https://www.grainger.com",
                "vendor_description": "Leading distributor of maintenance, repair, and operating supplies",
                "market_category": "Industrial Supplies",
                "region": "United States"
            },
            {
                "vendor_name": "Amazon Business",
                "vendor_website": "https://business.amazon.com",
                "vendor_description": "B2B marketplace for business and industrial supplies",
                "market_category": "General Business Supplies",
                "region": None
            },
            {
                "vendor_name": "Uline",
                "vendor_website": "https://www.uline.com",
                "vendor_description": "Shipping and packaging supplies distributor",
                "market_category": "Packaging and Shipping Supplies",
                "region": "North America"
            }
        ]

    # Create training examples
    trainset = []
    for vendor in seed_vendors:
        example = Example(
            vendor_name=vendor["vendor_name"],
            vendor_website=vendor["vendor_website"],
            vendor_description=vendor["vendor_description"],
            market_category=vendor["market_category"],
            region=vendor.get("region")
        ).with_inputs(
            "vendor_name", "vendor_website", "vendor_description",
            "market_category", "region"
        )
        trainset.append(example)

    # Create agent and metric
    agent = create_swot_agent(use_tools=use_tools, max_iters=20)
    metric = make_swot_llm_judge_metric(include_details=True)

    # Configure bootstrapper
    bootstrapper = BootstrapFewShot(
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_rounds=max_rounds,
        metric=metric
    )

    logger.info(f"Running bootstrap with {len(trainset)} seed examples...")

    # Run bootstrap
    bootstrapped_agent = bootstrapper.compile(
        student=agent,
        trainset=trainset
    )

    # Save bootstrapped demonstrations if requested
    if save_path:
        save_swot_bootstrap(bootstrapper, save_path)

    logger.info(f"Bootstrap completed with {len(bootstrapper.demos)} demonstrations")

    return bootstrapped_agent


def save_swot_bootstrap(
    bootstrapper: BootstrapFewShot,
    path: str = "data/artifacts/swot_bootstrap.jsonl"
) -> None:
    """
    Save bootstrapped SWOT demonstrations to JSONL file.

    Parameters
    ----------
    bootstrapper : BootstrapFewShot
        Bootstrapper with demonstrations
    path : str
        Path to save demonstrations
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    demos_data = []
    for demo in bootstrapper.demos:
        # Convert demo to serializable format
        demo_dict = {
            "inputs": {},
            "outputs": {}
        }

        # Extract input fields
        for field in ["vendor_name", "vendor_website", "vendor_description",
                      "market_category", "region", "competitors"]:
            if hasattr(demo, field):
                value = getattr(demo, field)
                if value is not None:
                    demo_dict["inputs"][field] = value

        # Extract SWOT analysis output
        if hasattr(demo, "swot_analysis"):
            swot = demo.swot_analysis
            if isinstance(swot, SWOTAnalysis):
                demo_dict["outputs"]["swot_analysis"] = swot.model_dump()
            elif isinstance(swot, dict):
                demo_dict["outputs"]["swot_analysis"] = swot

        demos_data.append(demo_dict)

    # Write to JSONL
    with open(output_path, 'w') as f:
        for demo in demos_data:
            f.write(json.dumps(demo) + '\n')

    logger.info(f"Saved {len(demos_data)} SWOT demonstrations to {output_path}")


def load_swot_bootstrap(
    path: str = "data/artifacts/swot_bootstrap.jsonl"
) -> List[Example]:
    """
    Load bootstrapped SWOT demonstrations from JSONL file.

    Parameters
    ----------
    path : str
        Path to load demonstrations from

    Returns
    -------
    List[Example]
        List of DSPy examples
    """
    input_path = Path(path)

    if not input_path.exists():
        logger.warning(f"No bootstrap file found at {input_path}")
        return []

    examples = []

    with open(input_path, 'r') as f:
        for line in f:
            demo_data = json.loads(line)

            # Create Example from loaded data
            inputs = demo_data.get("inputs", {})
            outputs = demo_data.get("outputs", {})

            example = Example(
                vendor_name=inputs.get("vendor_name"),
                vendor_website=inputs.get("vendor_website"),
                vendor_description=inputs.get("vendor_description"),
                market_category=inputs.get("market_category"),
                region=inputs.get("region"),
                competitors=inputs.get("competitors")
            )

            # Add output if available
            if "swot_analysis" in outputs:
                swot_data = outputs["swot_analysis"]
                if isinstance(swot_data, dict):
                    example.swot_analysis = SWOTAnalysis(**swot_data)
                else:
                    example.swot_analysis = swot_data

            examples.append(example)

    logger.info(f"Loaded {len(examples)} SWOT demonstrations from {input_path}")

    return examples


def main():
    """Run SWOT bootstrap optimization."""
    from dotenv import load_dotenv
    from config.environment import validate_environment, get_primary_lm_config
    from config.observability import setup_langfuse

    # Load environment and configure
    load_dotenv()
    validate_environment()
    setup_langfuse()

    # Configure DSPy
    primary_config = get_primary_lm_config()
    primary_lm = dspy.LM(**primary_config)
    dspy.configure(lm=primary_lm)

    logger.info("Starting SWOT agent bootstrap...")

    # Run bootstrap
    bootstrapped_agent = bootstrap_swot_agent(
        max_bootstrapped_demos=8,
        max_rounds=2,
        use_tools=True,
        save_path="data/artifacts/swot_bootstrap.jsonl"
    )

    logger.info("Bootstrap completed!")

    # Test the bootstrapped agent
    test_vendor = {
        "vendor_name": "McMaster-Carr",
        "vendor_website": "https://www.mcmaster.com",
        "vendor_description": "Industrial supplies and hardware distributor",
        "market_category": "Industrial Hardware",
        "region": "United States"
    }

    logger.info(f"Testing bootstrapped agent with {test_vendor['vendor_name']}...")

    result = bootstrapped_agent(
        vendor_name=test_vendor["vendor_name"],
        vendor_website=test_vendor["vendor_website"],
        vendor_description=test_vendor["vendor_description"],
        market_category=test_vendor["market_category"],
        region=test_vendor["region"]
    )

    if hasattr(result, 'swot_analysis'):
        swot = result.swot_analysis
        print(f"\n✅ Bootstrap test successful!")
        print(f"\nVendor: {swot.vendor_name}")
        print(f"Executive Summary: {swot.executive_summary[:200]}...")
        print(f"Recommendations: {len(swot.strategic_recommendations)} generated")
    else:
        print("\n❌ Bootstrap test failed - no SWOT analysis generated")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()