from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import dspy
from dotenv import load_dotenv

from config.environment import (
    validate_environment,
    get_vendor_program_path,
    get_sourcing_concurrency,
)
from config.lm import configure_primary_lm
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
from tools.web_tools import scoped_tavily_extract_budget
from utils.source_logger import reset_source_logger, get_source_logger

def run_complete_pipeline(
    category: str,
    region: str,
    vendors: int,
    max_vendor_iters: int,
    swot_count: int,
    expected_rfp_questions: int,
    output_dir: str,
    max_porters_iters: int,
    max_pestle_iters: int,
    max_swot_iters: int,
    max_rfp_iters: int,
    disable_cache: bool,
    progress_callback: callable = None,
    log: callable | None = None,
) -> None:
    validate_environment()
    setup_langfuse()

    session_id = generate_session_id()

    # Initialize source logger for this session
    reset_source_logger(session_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # Logging helper that respects an optional injected logger
    def _log(msg: str) -> None:
        if log is not None:
            try:
                log(msg)
                return
            except Exception:
                pass
        print(msg)

    # Create the report generator with session ID for citation matching
    configure_primary_lm()
    report_generator = ReportGenerator(session_id=session_id)

    # STEP 1–3 — Run Vendor, PESTLE, and Porter's analyses in parallel.
    if progress_callback:
        # Set description without advancing progress yet
        progress_callback(1, "Parallel Market Analyses", advance=0)

    vendor_program_path = get_vendor_program_path()
    vendor_agent = load_vendor_agent(
        path=vendor_program_path,
        max_iters=max_vendor_iters,
    )
    if vendor_agent is None:
        vendor_agent = create_vendor_agent(
            max_iters=max_vendor_iters,
        )

    # Ensure the loaded agent respects the configured iteration cap.
    if getattr(vendor_agent, "max_iters", None) != max_vendor_iters:
        vendor_agent.max_iters = max_vendor_iters

    pestle_agent = create_pestle_agent(use_tools=True, max_iters=max_pestle_iters)
    porters_agent = create_porters_agent(use_tools=True, max_iters=max_porters_iters)

    # Helper to scope Tavily extract budget per analysis task (runs inside worker thread)
    def _run_with_extract_budget(func, **kwargs):
        with scoped_tavily_extract_budget():
            return func(**kwargs)

    # Submit three independent tasks
    futures = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures[executor.submit(
            _run_with_extract_budget,
            vendor_agent,
            category=category,
            n=vendors,
            country_or_region=region,
        )] = "Vendor Discovery"

        futures[executor.submit(
            _run_with_extract_budget,
            pestle_agent,
            category=category,
            region=region,
            focus_areas=None,
        )] = "PESTLE Analysis"

        futures[executor.submit(
            _run_with_extract_budget,
            porters_agent,
            category=category,
            region=region,
            focus_areas=None,
        )] = "Porter's Analysis"

        vendor_prediction = None
        pestle_prediction = None
        porters_prediction = None

        for future in as_completed(futures):
            label = futures[future]
            try:
                result = future.result()
                if label == "Vendor Discovery":
                    vendor_prediction = result
                elif label == "PESTLE Analysis":
                    pestle_prediction = result
                elif label == "Porter's Analysis":
                    porters_prediction = result
            finally:
                if progress_callback:
                    progress_callback(1, label, advance=1)

    # Extract and validate results
    vendor_list = list(getattr(vendor_prediction, "vendor_list", []) or []) if vendor_prediction else []
    if not vendor_list:
        raise RuntimeError("Vendor agent did not return any vendors")

    pestle_analysis = getattr(pestle_prediction, "pestle_analysis", None) if pestle_prediction else None
    if pestle_analysis is None:
        raise RuntimeError("PESTLE agent did not return an analysis")

    porters_analysis = getattr(porters_prediction, "porters_analysis", None) if porters_prediction else None
    if porters_analysis is None:
        raise RuntimeError("Porter's agent did not return an analysis")

    # Generate and save reports immediately
    vendor_markdown = report_generator.generate_vendor_report(vendor_list, category, region)
    vendor_file = save_report(vendor_markdown, str(output_dir / "01_vendor_discovery.md"))
    _log(f"[STEP 1] Vendor discovery complete - {len(vendor_list)} vendors found")
    _log(f"         Report saved to: {vendor_file}")

    pestle_markdown = report_generator.generate_pestle_report(pestle_analysis, category, region)
    pestle_file = save_report(pestle_markdown, str(output_dir / "02_pestle_analysis.md"))
    _log(f"[STEP 2] PESTLE analysis complete")
    _log(f"         Report saved to: {pestle_file}")

    porters_markdown = report_generator.generate_porters_report(porters_analysis, category, region)
    porters_file = save_report(porters_markdown, str(output_dir / "03_porters_analysis.md"))
    _log(f"[STEP 3] Porter's Five Forces complete")
    _log(f"         Report saved to: {porters_file}")
# STEP 4 — SWOT across selected vendors (parallelized).
    if progress_callback:
        progress_callback(2, "SWOT Analysis")
    configure_primary_lm()
    swot_vendors = vendor_list[: max(swot_count, 0)]
    if not swot_vendors:
        raise RuntimeError("No vendors available for SWOT analysis")

    # Determine max concurrency from environment
    try:
        max_workers = int(get_sourcing_concurrency())
    except Exception:
        max_workers = 3
    max_workers = max(1, min(max_workers, len(swot_vendors)))

    # Create agent pool (one agent per worker) to avoid sharing agents across threads
    agents = [create_swot_agent(use_tools=True, max_iters=max_swot_iters) for _ in range(max_workers)]

    swot_results_indexed = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, vendor in enumerate(swot_vendors):
            agent = agents[i % len(agents)]
            future = executor.submit(
                analyze_vendor_swot,
                vendor,
                category,
                region,
                None,  # competitors
                agent,
            )
            futures[future] = (i, vendor)

        completed = 0
        total = len(swot_vendors)
        for future in as_completed(futures):
            idx, vendor = futures[future]
            try:
                swot = future.result()
                swot_results_indexed.append((idx, swot))
            except Exception:
                # Skip failed SWOTs but continue processing others
                pass
            finally:
                completed += 1
                if progress_callback:
                    vendor_name = (
                        vendor.get("name", "vendor") if isinstance(vendor, dict) else getattr(vendor, "name", "vendor")
                    )
                    progress_callback(2, f"SWOT: {vendor_name}", advance=1)

    # Restore original order and drop failures
    swot_results_indexed.sort(key=lambda x: x[0])
    swot_analyses = [sw for _, sw in swot_results_indexed if sw is not None]

    # Generate and save SWOT report immediately
    swot_markdown = report_generator.generate_swot_report(swot_analyses, category, region)
    swot_file = save_report(swot_markdown, str(output_dir / "04_swot_analyses.md"))
    _log(f"[STEP 4] SWOT analyses complete - {len(swot_analyses)} vendors analyzed")
    _log(f"         Report saved to: {swot_file}")

# STEP 5 — RFP generation using preceding outputs.
    if progress_callback:
        # Set description without advancing; we'll advance on completion
        progress_callback(3, "RFP Generation", advance=0)
    configure_primary_lm()
    rfp_agent = create_rfp_agent(use_tools=True, max_iters=max_rfp_iters)
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
    with scoped_tavily_extract_budget():
        rfp_prediction = rfp_agent(
            category=category,
            region=region,
            pestle_analysis=pestle_payload,
            porters_analysis=porters_payload,
            swot_analyses=swot_payloads,
            vendor_list=vendor_payloads,
            expected_question_count=expected_rfp_questions,
        )
    rfp_question_set = getattr(rfp_prediction, "question_set", None)
    if rfp_question_set is None:
        raise RuntimeError("RFP agent did not return a question set")

    # Generate and save RFP report immediately
    rfp_markdown = report_generator.generate_rfp_report(rfp_question_set, category, region)
    rfp_file = save_report(rfp_markdown, str(output_dir / "05_rfp_questions.md"))
    _log(f"[STEP 5] RFP generation complete - {rfp_question_set.total_questions} questions generated")
    _log(f"         Report saved to: {rfp_file}")
    if progress_callback:
        progress_callback(3, "RFP Generation", advance=1)

    # Now generate the combined report from all the individual reports
    _log(f"\nGenerating combined analysis report...")

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
        category=category,
        region=region,
        vendor_report=vendor_content,
        pestle_report=pestle_content,
        porters_report=porters_content,
        swot_report=swot_content,
        rfp_report=rfp_content
    )

    complete_file = save_report(combined_markdown, str(output_dir / "COMPLETE_ANALYSIS_REPORT.md"))

    _log(f"\n✅ All reports generated successfully!")
    _log(f"\n📁 Output directory: {output_dir}")
    _log(f"\n📄 Individual reports:")
    _log(f"  - Vendor Discovery: {Path(vendor_file).name}")
    _log(f"  - PESTLE Analysis: {Path(pestle_file).name}")
    _log(f"  - Porter's Five Forces: {Path(porters_file).name}")
    _log(f"  - SWOT Analyses: {Path(swot_file).name}")
    _log(f"  - RFP Questions: {Path(rfp_file).name}")
    _log(f"\n📑 Combined report: {Path(complete_file).name}")

    # Report on sources collected for citations
    source_logger = get_source_logger()
    manifest = source_logger.get_session_manifest()
    _log(f"\n📚 Citation Sources:")
    _log(f"  - Session ID: {manifest['session_id']}")
    _log(f"  - Total sources logged: {manifest['total_sources']}")
    _log(f"  - Source files: {len(manifest['files'])}")
    for file_name, count in manifest['files'].items():
        _log(f"    • {file_name}: {count} sources")

def main() -> None:
    load_dotenv(override=True)
    args = parse_args()
    run_complete_pipeline(
        category=args.category,
        region=args.region,
        vendors=args.vendors,
        max_vendor_iters=args.max_vendor_iters,
        swot_count=args.swot_count,
        expected_rfp_questions=args.expected_rfp_questions,
        output_dir=args.output_dir,
        max_porters_iters=args.max_porters_iters,
        max_pestle_iters=args.max_pestle_iters,
        max_swot_iters=args.max_swot_iters,
        max_rfp_iters=args.max_rfp_iters,
        disable_cache=args.disable_cache,
    )

if __name__ == "__main__":
    main()
