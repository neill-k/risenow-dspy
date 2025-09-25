#!/usr/bin/env python
"""CLI interface for the complete analysis pipeline."""

import click
import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.columns import Columns
from rich.live import Live
from rich.layout import Layout
from rich import box
from dotenv import load_dotenv
import logging
from scripts.pipeline import run_complete_pipeline
from tools.web_tools import set_tool_ui_log

# Configure logging to be less verbose for CLI
logging.basicConfig(level=logging.WARNING)

load_dotenv(override=True)

console = Console()


@click.command()
@click.option(
    '--category', '-c',
    default='General Industrial Supplies',
    help='Business category to analyze'
)
@click.option(
    '--vendors', '-n',
    default=15,
    type=int,
    help='Number of vendors to discover'
)
@click.option(
    '--region', '-r',
    default='United States',
    help='Geographic region for analysis'
)
@click.option(
    '--swot-count', '-s',
    default=15,
    type=int,
    help='Number of top vendors for SWOT analysis'
)
@click.option(
    '--rfp-questions', '-q',
    default=150,
    type=int,
    help='Target number of RFP questions'
)
@click.option(
    '--optimize/--no-optimize',
    default=False,
    help='Optimize agents if not cached'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Save RFP to file (optional)'
)
@click.option(
    '--format', '-f', 'output_format',
    type=click.Choice(['table', 'json', 'markdown'], case_sensitive=False),
    default='markdown',
    help='Output format',
)
@click.option(
    '--save-markdown/--no-markdown',
    default=True,
    help='Save all analysis steps as markdown files'
)
@click.option(
    '--output-dir',
    default='pipeline_outputs',
    help='Directory for markdown output files'
)
@click.option(
    '--no-intermediate',
    is_flag=True,
    default=False,
    help='Skip intermediate markdown files, only generate complete report'
)
def analyze(category, vendors, region, swot_count, rfp_questions, optimize, output, output_format, save_markdown, output_dir, no_intermediate):
    """
    🚀 Run complete vendor analysis pipeline

    Executes parallel market analysis, vendor discovery, SWOT assessments, and RFP generation.
    """

    # Display configuration
    console.print("\n[bold cyan]Analysis Pipeline Configuration[/bold cyan]")

    config_table = Table(show_header=False, box=box.SIMPLE)
    config_table.add_column("Setting", style="dim")
    config_table.add_column("Value", style="cyan")

    config_table.add_row("📦 Category", category)
    config_table.add_row("🌍 Region", region)
    config_table.add_row("🏢 Vendors to Find", str(vendors))
    config_table.add_row("🎯 SWOT Analyses", str(swot_count))
    config_table.add_row("📋 RFP Questions", str(rfp_questions))
    config_table.add_row("⚡ Optimization", "Enabled" if optimize else "Disabled")

    console.print(config_table)
    console.print()

    # Start timing
    start_time = time.time()

    # Progress tracking
    overall_total = 3 + swot_count + 1  # 3 (vendor, PESTLE, Porter's) + swot_count + 1 (RFP)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:

        # Main pipeline task
        pipeline_task = progress.add_task(
            "[cyan]Running analysis pipeline...",
            total=overall_total
        )

        # Phase indicators
        phases = {
            "phase1": progress.add_task("[yellow]Phase 1: Parallel Analysis", total=3),
            "phase2": progress.add_task("[green]Phase 2: SWOT Analysis", total=swot_count),
            "phase3": progress.add_task("[blue]Phase 3: RFP Generation", total=1),
        }

        def progress_callback(step: int, description: str, advance: int = 1):
            phase_key = f"phase{step}"
            progress.update(phases[phase_key], description=f"[yellow]Phase {step}: {description}...")
            progress.advance(phases[phase_key], advance=advance)
            progress.advance(pipeline_task, advance=advance)

        # Wire tool UI log to the live progress logger
        def progress_log(msg: str):
            # Route messages from pipeline/tools to the Progress console safely
            progress.log(msg)

        set_tool_ui_log(progress_log)
        try:
            result = run_complete_pipeline(
                category=category,
                region=region,
                vendors=vendors,
                max_vendor_iters=100,
                swot_count=swot_count,
                expected_rfp_questions=rfp_questions,
                output_dir=output_dir,
                max_porters_iters=30,
                max_pestle_iters=30,
                max_swot_iters=25,
                max_rfp_iters=50,
                disable_cache=optimize,
                progress_callback=progress_callback,
                log=progress_log,
            )
            # Ensure overall task shows as complete
            progress.update(pipeline_task, completed=overall_total)

        except Exception as e:
            console.print(f"\n[red bold]❌ Pipeline failed: {e}[/red bold]")
            return
        finally:
            # Detach the UI log hook after pipeline finishes
            set_tool_ui_log(None)

    elapsed = time.time() - start_time

    # Display results
    console.print(f"\n[bold green]✅ Pipeline completed in {elapsed:.1f} seconds[/bold green]\n")

    # Check if we have results to display
    if not result:
        console.print("[red]❌ No results returned from pipeline[/red]")
        return

    # Results summary
    if output_format == 'table':
        display_table_results(result)
    elif output_format == 'json':
        display_json_results(result)
    else:  # markdown
        display_markdown_results(result)

    # Show markdown generation status if enabled
    if save_markdown:
        markdown_files = getattr(result, 'markdown_files', None)
        if markdown_files:
            console.print(f"\n[bold cyan]📝 Markdown Reports Generated:[/bold cyan]")
            for report_type, filepath in markdown_files.items():
                console.print(f"  • {report_type}: [green]{filepath}[/green]")

    # Save RFP if requested
    if output and hasattr(result, 'rfp_question_set') and result.rfp_question_set:
        save_rfp_output(result, output, output_format)
        console.print(f"\n💾 RFP saved to: [cyan]{output}[/cyan]")


def display_table_results(result):
    """Display results in rich tables."""
    if not result:
        console.print("[red]No results to display[/red]")
        return

    # Vendors table
    vendor_table = Table(title="🏢 Top Vendors", box=box.ROUNDED)
    vendor_table.add_column("#", style="dim", width=3)
    vendor_table.add_column("Company", style="cyan")
    vendor_table.add_column("Website", style="blue")

    vendor_list = getattr(result, 'vendor_list', [])
    for i, vendor in enumerate(vendor_list[:5], 1):
        vendor_table.add_row(
            str(i),
            getattr(vendor, 'name', 'Unknown'),
            getattr(vendor, 'website', 'N/A')
        )

    console.print(vendor_table)

    # Analysis status panel
    analyses = []
    pestle_analysis = getattr(result, 'pestle_analysis', None)
    if pestle_analysis:
        pestle_summary = getattr(pestle_analysis, 'executive_summary', '')[:100] + "..."
        analyses.append(f"[green]✓[/green] PESTLE: {pestle_summary}")
    else:
        analyses.append("[red]✗[/red] PESTLE: Not completed")

    porters_analysis = getattr(result, 'porters_analysis', None)
    if porters_analysis:
        attractiveness = getattr(porters_analysis, 'overall_attractiveness', 'N/A')
        analyses.append(f"[green]✓[/green] Porter's: Market attractiveness: {attractiveness}")
    else:
        analyses.append("[red]✗[/red] Porter's: Not completed")

    swot_analyses = getattr(result, 'swot_analyses', [])
    if swot_analyses:
        analyses.append(f"[green]✓[/green] SWOT: {len(swot_analyses)} vendors analyzed")
    else:
        analyses.append("[red]✗[/red] SWOT: Not completed")

    console.print(Panel("\n".join(analyses), title="📊 Analysis Status", box=box.ROUNDED))

    # RFP summary
    rfp_question_set = getattr(result, 'rfp_question_set', None)
    if rfp_question_set:
        rfp_table = Table(title="📋 RFP Question Set", box=box.ROUNDED)
        rfp_table.add_column("Section", style="cyan")
        rfp_table.add_column("Questions", justify="right")

        sections = getattr(rfp_question_set, 'sections', [])
        for section in sections[:5]:
            rfp_table.add_row(
                getattr(section, 'title', 'Unknown'),
                str(len(getattr(section, 'questions', [])))
            )

        if len(sections) > 5:
            rfp_table.add_row(
                f"... and {len(sections) - 5} more sections",
                "...",
                style="dim"
            )

        console.print(rfp_table)
        total_questions = getattr(rfp_question_set, 'total_questions', 0)
        console.print(f"\n[bold]Total RFP Questions: {total_questions}[/bold]")


def display_json_results(result):
    """Display results as JSON."""
    import json
    
    if not result:
        console.print_json(data={"error": "No results available"})
        return

    vendor_list = getattr(result, 'vendor_list', [])
    pestle_analysis = getattr(result, 'pestle_analysis', None)
    porters_analysis = getattr(result, 'porters_analysis', None)
    swot_analyses = getattr(result, 'swot_analyses', [])
    rfp_question_set = getattr(result, 'rfp_question_set', None)

    output = {
        "vendors": len(vendor_list),
        "pestle_complete": pestle_analysis is not None,
        "porters_complete": porters_analysis is not None,
        "swot_count": len(swot_analyses),
        "rfp_questions": getattr(rfp_question_set, 'total_questions', 0) if rfp_question_set else 0,
        "rfp_sections": len(getattr(rfp_question_set, 'sections', [])) if rfp_question_set else 0,
    }

    console.print_json(data=output)


def display_markdown_results(result):
    """Display results as markdown."""
    from rich.markdown import Markdown
    
    if not result:
        console.print(Markdown("# Analysis Results\n\n**Error:** No results available"))
        return

    vendor_list = getattr(result, 'vendor_list', [])
    pestle_analysis = getattr(result, 'pestle_analysis', None)
    porters_analysis = getattr(result, 'porters_analysis', None)
    swot_analyses = getattr(result, 'swot_analyses', [])
    rfp_question_set = getattr(result, 'rfp_question_set', None)

    md_text = f"""# Analysis Results

## Vendors Discovered: {len(vendor_list)}

## Market Analyses
- PESTLE: {'✓ Complete' if pestle_analysis else '✗ Not completed'}
- Porter's Five Forces: {'✓ Complete' if porters_analysis else '✗ Not completed'}
- SWOT Analyses: {len(swot_analyses)} vendors

## RFP Generation
- Total Questions: {getattr(rfp_question_set, 'total_questions', 0) if rfp_question_set else 0}
- Sections: {len(getattr(rfp_question_set, 'sections', [])) if rfp_question_set else 0}
"""

    console.print(Markdown(md_text))


def save_rfp_output(result, filepath, output_format):
    """Save RFP questions to file."""
    rfp_question_set = getattr(result, 'rfp_question_set', None)
    if not rfp_question_set:
        return

    category = getattr(result, 'category', 'Unknown')
    region = getattr(result, 'region', 'Unknown')

    with open(filepath, 'w') as f:
        if output_format == 'json':
            import json
            sections = getattr(rfp_question_set, 'sections', [])
            rfp_data = {
                "category": category,
                "region": region,
                "total_questions": getattr(rfp_question_set, 'total_questions', 0),
                "sections": [
                    {
                        "title": getattr(section, 'title', 'Unknown'),
                        "questions": [
                            {
                                "question": getattr(q, 'question', ''),
                                "context": getattr(q, 'context', ''),
                                "type": getattr(q, 'expected_response_type', '')
                            }
                            for q in getattr(section, 'questions', [])
                        ]
                    }
                    for section in sections
                ]
            }
            json.dump(rfp_data, f, indent=2)

        elif output_format == 'markdown':
            f.write(f"# RFP for {category}\n")
            f.write(f"**Region:** {region}\n\n")

            sections = getattr(rfp_question_set, 'sections', [])
            for section in sections:
                section_title = getattr(section, 'title', 'Unknown')
                f.write(f"\n## {section_title}\n\n")
                questions = getattr(section, 'questions', [])
                for i, q in enumerate(questions, 1):
                    question_text = getattr(q, 'question', '')
                    context = getattr(q, 'context', '')
                    f.write(f"{i}. **{question_text}**\n")
                    if context:
                        f.write(f"   *Context: {context}*\n")
                    f.write("\n")

        else:  # table/text format
            f.write(f"RFP for {category}\n")
            f.write(f"Region: {region}\n")
            f.write("=" * 60 + "\n\n")

            sections = getattr(rfp_question_set, 'sections', [])
            for section in sections:
                section_title = getattr(section, 'title', 'Unknown')
                f.write(f"\n{section_title.upper()}\n")
                f.write("-" * 40 + "\n")
                questions = getattr(section, 'questions', [])
                for i, q in enumerate(questions, 1):
                    question_text = getattr(q, 'question', '')
                    context = getattr(q, 'context', '')
                    f.write(f"\n{i}. {question_text}\n")
                    if context:
                        f.write(f"   Context: {context}\n")


if __name__ == '__main__':
    analyze()
