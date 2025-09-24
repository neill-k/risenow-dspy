#!/usr/bin/env python
"""Run each pipeline phase sequentially with real API calls and markdown snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import List

import dspy
from dotenv import load_dotenv

from config.environment import (
    validate_environment,
    get_primary_lm_config,
    get_vendor_program_path,
)
from config.observability import setup_langfuse, generate_session_id
from agents.vendor_agent import create_vendor_agent, load_vendor_agent
from agents.pestle_agent import create_pestle_agent
from agents.porters_agent import create_porters_agent
from agents.swot_agent import create_swot_agent, analyze_vendor_swot
from agents.rfp_agent import create_rfp_agent
from tools.markdown_tools import (
    output_report,
    ReportGenerator,
    save_report
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute each pipeline stage sequentially and emit markdown summaries.",
    )
    parser.add_argument(
        "--category",
        default="Cloud Infrastructure Solutions",
        help="Business category to analyse.",
    )
    parser.add_argument(
        "--region",
        default="United States",
        help="Geographic region focus.",
    )
    parser.add_argument(
        "--vendors",
        type=int,
        default=15,
        help="Number of vendors to discover in the first stage.",
    )
    parser.add_argument(
        "--max-vendor-iters",
        type=int,
        default=150,
        help="Max ReAct iterations for the vendor discovery agent.",
    )
    parser.add_argument(
        "--swot-count",
        type=int,
        default=15,
        help="Number of vendors to include in SWOT analysis.",
    )
    parser.add_argument(
        "--expected-rfp-questions",
        type=int,
        default=100,
        help="Target question count for the RFP stage.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/stepwise",
        help="Directory where markdown artefacts will be written.",
    )
    parser.add_argument(
        "--max-porters-iters",
        type=int,
        default=90,
        help="Max ReAct iterations for Porter's agent.",
    )
    parser.add_argument(
        "--max-pestle-iters",
        type=int,
        default=90,
        help="Max ReAct iterations for PESTLE agent.",
    )
    parser.add_argument(
        "--max-swot-iters",
        type=int,
        default=50,
        help="Max ReAct iterations for the SWOT agent.",
    )
    parser.add_argument(
        "--max-rfp-iters",
        type=int,
        default=90,
        help="Max ReAct iterations for the RFP generator.",
    )
    return parser.parse_args()


def configure_primary_lm() -> None:
    """Instantiate and register the primary LM with DSPy."""
    primary_config = get_primary_lm_config()
    # DSPy automatically uses exponential_backoff_retry strategy with LiteLLM
    # num_retries is now configured via environment.py
    primary_lm = dspy.LM(**primary_config)
    dspy.configure(lm=primary_lm)

    # Truncate long-running ReAct agent trajectories to prevent context window overflow
    dspy.settings.configure(
        rm=None,  # No retriever model used in this pipeline
        max_bootstrapped_demos=3,  # Max examples retrieved by RMs in training
        max_discussion_tokens=250000,  # Max tokens for ReAct agent trajectory (per step)
        max_thought_tokens=4000,  # Max tokens for a single 'thought' step
        max_steps=None,  # Not necessary since max_iters is set on agent
    )


def main() -> None:
    load_dotenv()
    args = parse_args()

    validate_environment()
    setup_langfuse()

    session_id = generate_session_id()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create the report generator that will be used throughout
    configure_primary_lm()
    report_generator = ReportGenerator()

    # STEP 1 — Vendor discovery using the vendor agent.
    vendor_program_path = get_vendor_program_path()
    vendor_agent = load_vendor_agent(
        path=vendor_program_path,
        use_tools=True,
        max_iters=args.max_vendor_iters,
    )
    if vendor_agent is None:
        vendor_agent = create_vendor_agent(
            use_tools=True,
            max_iters=args.max_vendor_iters,
        )

    vendor_prediction = vendor_agent(
        category=args.category,
        n=args.vendors,
        country_or_region=args.region,
    )
    vendor_list = list(getattr(vendor_prediction, "vendor_list", []) or [])
    if not vendor_list:
        raise RuntimeError("Vendor agent did not return any vendors")

    # Generate and save vendor report immediately
    vendor_markdown = report_generator.generate_vendor_report(vendor_list, args.category, args.region)
    vendor_file = save_report(vendor_markdown, str(output_dir / "01_vendor_discovery.md"))
    print(f"[STEP 1] Vendor discovery complete - {len(vendor_list)} vendors found")
    print(f"         Report saved to: {vendor_file}")

    # STEP 2 — PESTLE analysis using live tools.
    configure_primary_lm()
    pestle_agent = create_pestle_agent(use_tools=True, max_iters=args.max_pestle_iters)
    pestle_prediction = pestle_agent(
        category=args.category,
        region=args.region,
        focus_areas=None,
    )
    pestle_analysis = getattr(pestle_prediction, "pestle_analysis", None)
    if pestle_analysis is None:
        raise RuntimeError("PESTLE agent did not return an analysis")

    # Generate and save PESTLE report immediately
    pestle_markdown = report_generator.generate_pestle_report(pestle_analysis, args.category, args.region)
    pestle_file = save_report(pestle_markdown, str(output_dir / "02_pestle_analysis.md"))
    print(f"[STEP 2] PESTLE analysis complete")
    print(f"         Report saved to: {pestle_file}")

    # STEP 3 — Porter's Five Forces analysis.
    configure_primary_lm()
    porters_agent = create_porters_agent(use_tools=True, max_iters=args.max_porters_iters)
    porters_prediction = porters_agent(
        category=args.category,
        region=args.region,
        focus_areas=None,
    )
    porters_analysis = getattr(porters_prediction, "porters_analysis", None)
    if porters_analysis is None:
        raise RuntimeError("Porter's agent did not return an analysis")

    # Generate and save Porter's report immediately
    porters_markdown = report_generator.generate_porters_report(porters_analysis, args.category, args.region)
    porters_file = save_report(porters_markdown, str(output_dir / "03_porters_analysis.md"))
    print(f"[STEP 3] Porter's Five Forces complete")
    print(f"         Report saved to: {porters_file}")

    # STEP 4 — SWOT across selected vendors.
    configure_primary_lm()
    swot_vendors = vendor_list[: max(args.swot_count, 0)]
    if not swot_vendors:
        raise RuntimeError("No vendors available for SWOT analysis")
    swot_agent = create_swot_agent(use_tools=True, max_iters=args.max_swot_iters)
    swot_analyses = []
    for vendor in swot_vendors:
        swot = analyze_vendor_swot(
            vendor=vendor,
            category=args.category,
            region=args.region,
            agent=swot_agent,
            use_cache=False,
        )
        swot_analyses.append(swot)

    # Generate and save SWOT report immediately
    swot_markdown = report_generator.generate_swot_report(swot_analyses, args.category, args.region)
    swot_file = save_report(swot_markdown, str(output_dir / "04_swot_analyses.md"))
    print(f"[STEP 4] SWOT analyses complete - {len(swot_analyses)} vendors analyzed")
    print(f"         Report saved to: {swot_file}")

    # STEP 5 — RFP generation using preceding outputs.
    configure_primary_lm()
    rfp_agent = create_rfp_agent(use_tools=True, max_iters=args.max_rfp_iters)
    pestle_payload = pestle_analysis.dict() if hasattr(pestle_analysis, "dict") else pestle_analysis
    porters_payload = (
        porters_analysis.dict() if hasattr(porters_analysis, "dict") else porters_analysis
    )
    swot_payloads = [
        swot.dict() if hasattr(swot, "dict") else swot
        for swot in swot_analyses
        if swot is not None
    ]
    vendor_payloads = [
        vendor.dict() if hasattr(vendor, "dict") else vendor
        for vendor in vendor_list
    ]
    rfp_prediction = rfp_agent(
        category=args.category,
        region=args.region,
        pestle_analysis=pestle_payload,
        porters_analysis=porters_payload,
        swot_analyses=swot_payloads,
        vendor_list=vendor_payloads,
        expected_question_count=args.expected_rfp_questions,
    )
    rfp_question_set = getattr(rfp_prediction, "question_set", None)
    if rfp_question_set is None:
        raise RuntimeError("RFP agent did not return a question set")

    # Generate and save RFP report immediately
    rfp_markdown = report_generator.generate_rfp_report(rfp_question_set, args.category, args.region)
    rfp_file = save_report(rfp_markdown, str(output_dir / "05_rfp_questions.md"))
    print(f"[STEP 5] RFP generation complete - {rfp_question_set.total_questions} questions generated")
    print(f"         Report saved to: {rfp_file}")

    # Now generate the combined report from all the individual reports
    print(f"\nGenerating combined analysis report...")

    # Read back the individual reports we just saved
    with open(vendor_file, 'r', encoding='utf-8') as f:
        vendor_content = f.read()
    with open(pestle_file, 'r', encoding='utf-8') as f:
        pestle_content = f.read()
    with open(porters_file, 'r', encoding='utf-8') as f:
        porters_content = f.read()
    with open(swot_file, 'r', encoding='utf-8') as f:
        swot_content = f.read()
    with open(rfp_file, 'r', encoding='utf-8') as f:
        rfp_content = f.read()

    # Generate the combined report
    combined_markdown = report_generator.generate_combined_report(
        category=args.category,
        region=args.region,
        vendor_report=vendor_content,
        pestle_report=pestle_content,
        porters_report=porters_content,
        swot_report=swot_content,
        rfp_report=rfp_content
    )

    complete_file = save_report(combined_markdown, str(output_dir / "COMPLETE_ANALYSIS_REPORT.md"))

    print(f"\n✅ All reports generated successfully!")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\n📄 Individual reports:")
    print(f"  - Vendor Discovery: {Path(vendor_file).name}")
    print(f"  - PESTLE Analysis: {Path(pestle_file).name}")
    print(f"  - Porter's Five Forces: {Path(porters_file).name}")
    print(f"  - SWOT Analyses: {Path(swot_file).name}")
    print(f"  - RFP Questions: {Path(rfp_file).name}")
    print(f"\n📑 Combined report: {Path(complete_file).name}")


if __name__ == "__main__":
    main()