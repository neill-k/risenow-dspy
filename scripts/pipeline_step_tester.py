#!/usr/bin/env python
"""Run each pipeline phase sequentially with real API calls and markdown snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Iterable, List, Optional

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


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def sanitize_markdown(text: str | None) -> str:
    if not text:
        return "—"
    return text.replace("|", "\\|").strip()


def vendor_markdown(category: str, region: str | None, vendors: List) -> str:
    rows = [
        "| # | Vendor | Website | Contact Email | Phone | Countries | Justification |",
        "|---|--------|---------|----------------|-------|-----------|---------------|",
    ]
    for index, vendor in enumerate(vendors, start=1):
        name = getattr(vendor, "name", "Unknown")
        website = getattr(vendor, "website", "N/A")
        emails = getattr(vendor, "contact_emails", []) or []
        email = '-'
        if emails:
            email_obj = emails[0]
            address = getattr(email_obj, 'email', '') or ''
            label = getattr(email_obj, 'description', '') or ''
            email = f"{address} ({label})" if label else address or '-'
        email = sanitize_markdown(email)
        phones = getattr(vendor, "phone_numbers", []) or []
        phone = '-'
        if phones:
            phone_obj = phones[0]
            number = getattr(phone_obj, 'number', '') or ''
            label = getattr(phone_obj, 'description', '') or ''
            phone = f"{number} ({label})" if label else number or '-'
        phone = sanitize_markdown(phone)
        countries = getattr(vendor, "countries_served", []) or []
        countries_text = ", ".join(countries) if countries else "—"
        justification = sanitize_markdown(getattr(vendor, "justification", ""))
        rows.append(
            f"| {index} | {name} | {website} | {email} | {phone} | {countries_text} | {justification} |"
        )

    body = "\n".join(rows) if vendors else "No vendors returned."
    return dedent(
        f"""
        # Step 1 · Vendor Discovery

        - Category: {category}
        - Region: {region or 'Global'}
        - Vendors returned: {len(vendors)}

        {body}
        """
    ).strip() + "\n"


def pestle_markdown(analysis) -> str:
    summary = sanitize_markdown(getattr(analysis, "executive_summary", ""))

    def list_section(title: str, items: Iterable[str]) -> str:
        cleaned = [f"- {sanitize_markdown(item)}" for item in items if item]
        if not cleaned:
            cleaned = ["- —"]
        section = "\n".join(cleaned)
        return f"## {title}\n\n{section}\n"

    sections = []
    for pillar in [
        "political",
        "economic",
        "social",
        "technological",
        "legal",
        "environmental",
    ]:
        pillar_obj = getattr(analysis, pillar, None)
        insights = getattr(pillar_obj, "key_insights", []) if pillar_obj else []
        title = f"{pillar.title()} Insights"
        sections.append(list_section(title, insights))

    opportunities = list_section("Opportunities", getattr(analysis, "opportunities", []))
    threats = list_section("Threats", getattr(analysis, "threats", []))

    return dedent(
        f"""
        # Step 2 · PESTLE Analysis

        - Region analysed: {sanitize_markdown(getattr(analysis, 'region', 'Global'))}
        - Recommendations: {len(getattr(analysis, 'strategic_recommendations', []) or [])}

        ## Executive Summary

        {summary or '—'}

        {opportunities}
        {threats}
        {''.join(sections)}
        """
    ).strip() + "\n"


def porters_markdown(analysis) -> str:
    def summarise_force(title: str, force_obj) -> str:
        if not force_obj:
            return f"### {title}\n\n—\n"
        insights = getattr(force_obj, "key_insights", []) or []
        bullets = "\n".join(f"- {sanitize_markdown(item)}" for item in insights) or "- —"
        return f"### {title}\n\n{bullets}\n"

    sections = [
        summarise_force("Threat of New Entrants", getattr(analysis, "threat_of_new_entrants", None)),
        summarise_force("Bargaining Power · Suppliers", getattr(analysis, "bargaining_power_suppliers", None)),
        summarise_force("Bargaining Power · Buyers", getattr(analysis, "bargaining_power_buyers", None)),
        summarise_force("Threat of Substitutes", getattr(analysis, "threat_of_substitutes", None)),
        summarise_force("Competitive Rivalry", getattr(analysis, "competitive_rivalry", None)),
    ]

    recommendations = getattr(analysis, "strategic_recommendations", []) or []
    recommendation_lines = "\n".join(
        f"- {sanitize_markdown(rec)}" for rec in recommendations
    ) or "- —"

    return dedent(
        f"""
        # Step 3 · Porter's Five Forces

        - Industry attractiveness: {sanitize_markdown(getattr(analysis, 'industry_attractiveness', 'Unknown'))}
        - Opportunities highlighted: {len(getattr(analysis, 'opportunities', []) or [])}
        - Threats highlighted: {len(getattr(analysis, 'threats', []) or [])}

        ## Strategic Recommendations

        {recommendation_lines}

        {''.join(sections)}
        """
    ).strip() + "\n"


def swot_markdown(swot_list: List) -> str:
    rows = [
        "| Vendor | Strengths | Weaknesses | Opportunities | Threats | Recommendations |",
        "|--------|-----------|------------|---------------|---------|----------------|",
    ]
    for swot in swot_list:
        if swot is None:
            continue
        name = getattr(swot, "vendor_name", "Unknown")
        strengths = len(getattr(getattr(swot, "strengths", None), "competitive_advantages", []) or [])
        weaknesses = len(getattr(getattr(swot, "weaknesses", None), "limitations", []) or [])
        opps = len(getattr(getattr(swot, "opportunities", None), "market_opportunities", []) or [])
        threats = len(getattr(getattr(swot, "threats", None), "competitive_threats", []) or [])
        recs = len(getattr(swot, "strategic_recommendations", []) or [])
        rows.append(
            f"| {sanitize_markdown(name)} | {strengths} | {weaknesses} | {opps} | {threats} | {recs} |"
        )

    body = "\n".join(rows) if swot_list else "No SWOT analyses produced."
    return dedent(
        f"""
        # Step 4 · SWOT Analyses

        - Vendors analysed: {len([s for s in swot_list if s is not None])}

        {body}
        """
    ).strip() + "\n"


def rfp_markdown(question_set) -> str:
    sections = []
    for section in getattr(question_set, "sections", []) or []:
        first_question = section.questions[0].question if section.questions else "—"
        sections.append(
            dedent(
                f"""
                ### {sanitize_markdown(section.title)}

                - Questions: {len(section.questions)}
                - Sample: {sanitize_markdown(first_question)}
                """
            ).strip()
        )

    section_text = "\n\n".join(sections) if sections else "No sections returned."
    return dedent(
        f"""
        # Step 5 · RFP Generation

        - Total questions: {getattr(question_set, 'total_questions', 0)}
        - Sections: {len(getattr(question_set, 'sections', []) or [])}

        {section_text}
        """
    ).strip() + "\n"


def main() -> None:
    load_dotenv()
    args = parse_args()

    validate_environment()
    setup_langfuse()

    session_id = generate_session_id()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # STEP 1 — Vendor discovery using the vendor agent.
    configure_primary_lm()
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
    vendor_path = output_dir / "step1_vendor_discovery.md"
    write_markdown(vendor_path, vendor_markdown(args.category, args.region, vendor_list))
    print(f"[STEP 1] Vendor discovery complete  {vendor_path}")

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
    pestle_path = output_dir / "step2_pestle.md"
    write_markdown(pestle_path, pestle_markdown(pestle_analysis))
    print(f"[STEP 2] PESTLE analysis complete → {pestle_path}")

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
    porters_path = output_dir / "step3_porters.md"
    write_markdown(porters_path, porters_markdown(porters_analysis))
    print(f"[STEP 3] Porter's Five Forces complete → {porters_path}")

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
    swot_path = output_dir / "step4_swot.md"
    write_markdown(swot_path, swot_markdown(swot_analyses))
    print(f"[STEP 4] SWOT analyses complete → {swot_path}")

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
    rfp_path = output_dir / "step5_rfp.md"
    write_markdown(rfp_path, rfp_markdown(rfp_question_set))
    print(f"[STEP 5] RFP generation complete → {rfp_path}")


if __name__ == "__main__":
    main()

