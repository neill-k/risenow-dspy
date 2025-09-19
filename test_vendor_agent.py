"""Quick test of the vendor discovery agent using DSPy ReAct harness."""

import logging
from typing import List
from pprint import pprint

import dspy
from config.environment import (
    OPENAI_API_KEY,
    TAVILY_API_KEY,
    get_primary_lm_config,
    validate_environment
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
        "category": "Cloud Infrastructure Services",
        "n": 5,
        "country_or_region": "United States"
    }

    logger.info("Running vendor discovery agent with inputs:")
    logger.info(f"  Category: {test_inputs['category']}")
    logger.info(f"  Number of vendors: {test_inputs['n']}")
    logger.info(f"  Country/Region: {test_inputs['country_or_region']}")

    # Execute the agent
    try:
        logger.info("Executing agent (this may take a moment)...")
        result = agent(**test_inputs)

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
        else:
            logger.warning("No vendors found in the result")

        # Optionally display the reasoning trace
        if hasattr(result, 'rationale') and result.rationale:
            logger.info("\n" + "="*60)
            logger.info("AGENT REASONING TRACE")
            logger.info("="*60)
            print(result.rationale)

    except Exception as e:
        logger.error(f"Error executing agent: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\nTest complete!")


if __name__ == "__main__":
    main()