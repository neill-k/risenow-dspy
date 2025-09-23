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

# Configure logging to be less verbose for CLI
logging.basicConfig(level=logging.WARNING)

load_dotenv()

from main import run_complete_pipeline

console = Console()


@click.command()
@click.option(
    '--category', '-c',
    default='General Industrial Supplies',
    help='Business category to analyze'
)
@click.option(
    '--vendors', '-n',
    default=10,
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
    default=3,
    type=int,
    help='Number of top vendors for SWOT analysis'
)
@click.option(
    '--rfp-questions', '-q',
    default=50,
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
    '--format', '-f',
    type=click.Choice(['table', 'json', 'markdown'], case_sensitive=False),
    default='table',
    help='Output format'
)
@click.option(
    '--save-markdown/--no-markdown',
    default=False,
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
def analyze(category, vendors, region, swot_count, rfp_questions, optimize, output, format, save_markdown, output_dir, no_intermediate):
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

    # Progress tracking
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
            total=100
        )

        # Phase indicators
        phases = {
            "phase1": progress.add_task("[yellow]Phase 1: Parallel Analysis", total=3),
            "phase2": progress.add_task("[green]Phase 2: SWOT Analysis", total=swot_count),
            "phase3": progress.add_task("[blue]Phase 3: RFP Generation", total=1),
        }

        # Mock progress updates (in real implementation, would hook into pipeline)
        start_time = time.time()

        try:
            # Update Phase 1
            progress.update(phases["phase1"], advance=1, description="[yellow]Phase 1: Vendor Discovery...")
            progress.update(pipeline_task, advance=10)

            progress.update(phases["phase1"], advance=1, description="[yellow]Phase 1: PESTLE Analysis...")
            progress.update(pipeline_task, advance=10)

            progress.update(phases["phase1"], advance=1, description="[yellow]Phase 1: Porter's Analysis...")
            progress.update(pipeline_task, advance=10)

            # Run the actual pipeline
            result = run_complete_pipeline(
                category=category,
                n_vendors=vendors,
                region=region,
                swot_top_n=swot_count,
                optimize_if_missing=optimize,
                reuse_cached_programs=not optimize,
                expected_rfp_questions=rfp_questions,
                save_markdown=save_markdown,
                output_dir=output_dir,
                save_intermediate=not no_intermediate,
            )

            # Update Phase 2
            for i in range(swot_count):
                progress.update(phases["phase2"], advance=1)
                progress.update(pipeline_task, advance=10)

            # Update Phase 3
            progress.update(phases["phase3"], advance=1)
            progress.update(pipeline_task, advance=40)

            progress.update(pipeline_task, completed=100)

        except Exception as e:
            console.print(f"\n[red bold]❌ Pipeline failed: {e}[/red bold]")
            return

    elapsed = time.time() - start_time

    # Display results
    console.print(f"\n[bold green]✅ Pipeline completed in {elapsed:.1f} seconds[/bold green]\n")

    # Results summary
    if format == 'table':
        display_table_results(result)
    elif format == 'json':
        display_json_results(result)
    else:  # markdown
        display_markdown_results(result)

    # Show markdown generation status if enabled
    if save_markdown and hasattr(result, 'markdown_files'):
        console.print(f"\n[bold cyan]📝 Markdown Reports Generated:[/bold cyan]")
        for report_type, filepath in result.markdown_files.items():
            console.print(f"  • {report_type}: [green]{filepath}[/green]")

    # Save RFP if requested
    if output and result.rfp_question_set:
        save_rfp_output(result, output, format)
        console.print(f"\n💾 RFP saved to: [cyan]{output}[/cyan]")


def display_table_results(result):
    """Display results in rich tables."""

    # Create layout
    layout = Layout()

    # Vendors table
    vendor_table = Table(title="🏢 Top Vendors", box=box.ROUNDED)
    vendor_table.add_column("#", style="dim", width=3)
    vendor_table.add_column("Company", style="cyan")
    vendor_table.add_column("Website", style="blue")

    for i, vendor in enumerate(result.vendor_list[:5], 1):
        vendor_table.add_row(
            str(i),
            getattr(vendor, 'name', 'Unknown'),
            getattr(vendor, 'website', 'N/A')
        )

    console.print(vendor_table)

    # Analysis status panel
    analyses = []
    if result.pestle_analysis:
        pestle_summary = getattr(result.pestle_analysis, 'executive_summary', '')[:100] + "..."
        analyses.append(f"[green]✓[/green] PESTLE: {pestle_summary}")
    else:
        analyses.append("[red]✗[/red] PESTLE: Not completed")

    if result.porters_analysis:
        attractiveness = getattr(result.porters_analysis, 'overall_attractiveness', 'N/A')
        analyses.append(f"[green]✓[/green] Porter's: Market attractiveness: {attractiveness}")
    else:
        analyses.append("[red]✗[/red] Porter's: Not completed")

    if result.swot_analyses:
        analyses.append(f"[green]✓[/green] SWOT: {len(result.swot_analyses)} vendors analyzed")
    else:
        analyses.append("[red]✗[/red] SWOT: Not completed")

    console.print(Panel("\n".join(analyses), title="📊 Analysis Status", box=box.ROUNDED))

    # RFP summary
    if result.rfp_question_set:
        rfp_table = Table(title="📋 RFP Question Set", box=box.ROUNDED)
        rfp_table.add_column("Section", style="cyan")
        rfp_table.add_column("Questions", justify="right")

        for section in result.rfp_question_set.sections[:5]:
            rfp_table.add_row(
                section.title,
                str(len(section.questions))
            )

        if len(result.rfp_question_set.sections) > 5:
            rfp_table.add_row(
                f"... and {len(result.rfp_question_set.sections) - 5} more sections",
                "...",
                style="dim"
            )

        console.print(rfp_table)
        console.print(f"\n[bold]Total RFP Questions: {result.rfp_question_set.total_questions}[/bold]")


def display_json_results(result):
    """Display results as JSON."""
    import json

    output = {
        "vendors": len(result.vendor_list),
        "pestle_complete": result.pestle_analysis is not None,
        "porters_complete": result.porters_analysis is not None,
        "swot_count": len(result.swot_analyses or []),
        "rfp_questions": result.rfp_question_set.total_questions if result.rfp_question_set else 0,
        "rfp_sections": len(result.rfp_question_set.sections) if result.rfp_question_set else 0,
    }

    console.print_json(data=output)


def display_markdown_results(result):
    """Display results as markdown."""
    from rich.markdown import Markdown

    md_text = f"""# Analysis Results

## Vendors Discovered: {len(result.vendor_list)}

## Market Analyses
- PESTLE: {'✓ Complete' if result.pestle_analysis else '✗ Not completed'}
- Porter's Five Forces: {'✓ Complete' if result.porters_analysis else '✗ Not completed'}
- SWOT Analyses: {len(result.swot_analyses or [])} vendors

## RFP Generation
- Total Questions: {result.rfp_question_set.total_questions if result.rfp_question_set else 0}
- Sections: {len(result.rfp_question_set.sections) if result.rfp_question_set else 0}
"""

    console.print(Markdown(md_text))


def save_rfp_output(result, filepath, format):
    """Save RFP questions to file."""
    if not result.rfp_question_set:
        return

    with open(filepath, 'w') as f:
        if format == 'json':
            import json
            rfp_data = {
                "category": result.category,
                "region": result.region,
                "total_questions": result.rfp_question_set.total_questions,
                "sections": [
                    {
                        "title": section.title,
                        "questions": [
                            {
                                "question": q.question,
                                "context": q.context,
                                "type": q.expected_response_type
                            }
                            for q in section.questions
                        ]
                    }
                    for section in result.rfp_question_set.sections
                ]
            }
            json.dump(rfp_data, f, indent=2)

        elif format == 'markdown':
            f.write(f"# RFP for {result.category}\n")
            f.write(f"**Region:** {result.region}\n\n")

            for section in result.rfp_question_set.sections:
                f.write(f"\n## {section.title}\n\n")
                for i, q in enumerate(section.questions, 1):
                    f.write(f"{i}. **{q.question}**\n")
                    if q.context:
                        f.write(f"   *Context: {q.context}*\n")
                    f.write("\n")

        else:  # table/text format
            f.write(f"RFP for {result.category}\n")
            f.write(f"Region: {result.region}\n")
            f.write("=" * 60 + "\n\n")

            for section in result.rfp_question_set.sections:
                f.write(f"\n{section.title.upper()}\n")
                f.write("-" * 40 + "\n")
                for i, q in enumerate(section.questions, 1):
                    f.write(f"\n{i}. {q.question}\n")
                    if q.context:
                        f.write(f"   Context: {q.context}\n")


if __name__ == '__main__':
    analyze()