"""DSPy tools for markdown report generation."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Dict
import dspy


# Individual report signatures
class GenerateVendorReport(dspy.Signature):
    """Generate a vendor discovery report."""
    vendor_list: List[Any] = dspy.InputField(desc="List of discovered vendors with details")
    category: str = dspy.InputField(desc="Business category")
    region: str = dspy.InputField(desc="Geographic region")
    markdown: str = dspy.OutputField(desc="Well-formatted markdown report with vendor table, all details, capabilities, etc.")


class GeneratePESTLEReport(dspy.Signature):
    """Generate a PESTLE analysis report."""
    pestle_analysis: Any = dspy.InputField(desc="PESTLE analysis results")
    category: str = dspy.InputField(desc="Business category")
    region: str = dspy.InputField(desc="Geographic region")
    markdown: str = dspy.OutputField(desc="Comprehensive PESTLE report with all six factors, insights, and recommendations")


class GeneratePortersReport(dspy.Signature):
    """Generate a Porter's Five Forces report."""
    porters_analysis: Any = dspy.InputField(desc="Porter's Five Forces analysis results")
    category: str = dspy.InputField(desc="Business category")
    region: str = dspy.InputField(desc="Geographic region")
    markdown: str = dspy.OutputField(desc="Porter's Five Forces report with force analysis and strategic implications")


class GenerateSWOTReport(dspy.Signature):
    """Generate SWOT analyses report."""
    swot_analyses: List[Any] = dspy.InputField(desc="List of SWOT analyses for vendors")
    category: str = dspy.InputField(desc="Business category")
    region: str = dspy.InputField(desc="Geographic region")
    markdown: str = dspy.OutputField(desc="SWOT report with summary table and detailed analysis per vendor")


class GenerateRFPReport(dspy.Signature):
    """Generate RFP questions report."""
    rfp_question_set: Any = dspy.InputField(desc="RFP question set with sections")
    category: str = dspy.InputField(desc="Business category")
    region: str = dspy.InputField(desc="Geographic region")
    markdown: str = dspy.OutputField(desc="RFP document with organized sections, questions, and evaluation criteria")


class GenerateCombinedReport(dspy.Signature):
    """Generate a combined analysis report from individual section reports."""
    category: str = dspy.InputField(desc="Business category")
    region: str = dspy.InputField(desc="Geographic region")
    vendor_report: Optional[str] = dspy.InputField(desc="Vendor discovery report content", default=None)
    pestle_report: Optional[str] = dspy.InputField(desc="PESTLE analysis report content", default=None)
    porters_report: Optional[str] = dspy.InputField(desc="Porter's Five Forces report content", default=None)
    swot_report: Optional[str] = dspy.InputField(desc="SWOT analyses report content", default=None)
    rfp_report: Optional[str] = dspy.InputField(desc="RFP questions report content", default=None)

    markdown: str = dspy.OutputField(desc="""
        Combined executive report that:
        1. Synthesizes insights from all available reports
        2. Includes executive summary with key findings
        3. Maintains logical flow between sections
        4. Adds table of contents
        5. Cross-references insights between analyses
        6. Provides integrated strategic recommendations
        """)


class ReportGenerator(dspy.Module):
    """DSPy module for generating all types of markdown reports."""

    def __init__(self, model: Optional[dspy.LM] = None):
        super().__init__()
        self.model = model or dspy.settings.lm

        # Individual report generators
        self.vendor_gen = dspy.ChainOfThought(GenerateVendorReport)
        self.pestle_gen = dspy.ChainOfThought(GeneratePESTLEReport)
        self.porters_gen = dspy.ChainOfThought(GeneratePortersReport)
        self.swot_gen = dspy.ChainOfThought(GenerateSWOTReport)
        self.rfp_gen = dspy.ChainOfThought(GenerateRFPReport)
        self.combined_gen = dspy.ChainOfThought(GenerateCombinedReport)

    def generate_vendor_report(self, vendor_list: List[Any], category: str, region: str) -> str:
        """Generate vendor discovery report."""
        with dspy.context(lm=self.model):
            result = self.vendor_gen(vendor_list=vendor_list, category=category, region=region)
        return result.markdown

    def generate_pestle_report(self, pestle_analysis: Any, category: str, region: str) -> str:
        """Generate PESTLE analysis report."""
        with dspy.context(lm=self.model):
            result = self.pestle_gen(pestle_analysis=pestle_analysis, category=category, region=region)
        return result.markdown

    def generate_porters_report(self, porters_analysis: Any, category: str, region: str) -> str:
        """Generate Porter's Five Forces report."""
        with dspy.context(lm=self.model):
            result = self.porters_gen(porters_analysis=porters_analysis, category=category, region=region)
        return result.markdown

    def generate_swot_report(self, swot_analyses: List[Any], category: str, region: str) -> str:
        """Generate SWOT analyses report."""
        with dspy.context(lm=self.model):
            result = self.swot_gen(swot_analyses=swot_analyses, category=category, region=region)
        return result.markdown

    def generate_rfp_report(self, rfp_question_set: Any, category: str, region: str) -> str:
        """Generate RFP questions report."""
        with dspy.context(lm=self.model):
            result = self.rfp_gen(rfp_question_set=rfp_question_set, category=category, region=region)
        return result.markdown

    def generate_combined_report(
        self,
        category: str,
        region: str,
        vendor_report: Optional[str] = None,
        pestle_report: Optional[str] = None,
        porters_report: Optional[str] = None,
        swot_report: Optional[str] = None,
        rfp_report: Optional[str] = None
    ) -> str:
        """Generate combined analysis report."""
        with dspy.context(lm=self.model):
            result = self.combined_gen(
                category=category,
                region=region,
                vendor_report=vendor_report,
                pestle_report=pestle_report,
                porters_report=porters_report,
                swot_report=swot_report,
                rfp_report=rfp_report
            )
        return result.markdown


def ensure_output_dir(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def add_timestamp_footer(content: str) -> str:
    """Add generation timestamp to content if not present."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer = f"\n\n---\n*Report generated on {timestamp}*"
    if footer not in content:
        return content + footer
    return content


def save_report(content: str, filepath: str) -> str:
    """Save markdown content to file."""
    content_with_footer = add_timestamp_footer(content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_with_footer)
    return filepath


def output_report(
    category: str,
    region: str,
    output_dir: str,
    vendor_list: Optional[List[Any]] = None,
    pestle_analysis: Optional[Any] = None,
    porters_analysis: Optional[Any] = None,
    swot_analyses: Optional[List[Any]] = None,
    rfp_question_set: Optional[Any] = None,
    save_intermediate: bool = True,
    model: Optional[dspy.LM] = None
) -> Dict[str, str]:
    """
    Generate and save comprehensive markdown reports.

    This tool generates individual markdown files for each analysis component
    and combines them into a comprehensive report, all using LLM for intelligent formatting.

    Parameters
    ----------
    category : str
        Business category being analyzed
    region : str
        Geographic region for analysis
    output_dir : str
        Directory where reports will be saved
    vendor_list : List[Any], optional
        List of discovered vendors
    pestle_analysis : Any, optional
        PESTLE analysis results
    porters_analysis : Any, optional
        Porter's Five Forces analysis results
    swot_analyses : List[Any], optional
        List of SWOT analyses for vendors
    rfp_question_set : Any, optional
        RFP question set
    save_intermediate : bool
        Whether to save individual reports (default True)
    model : dspy.LM, optional
        Language model to use for generation

    Returns
    -------
    Dict[str, str]
        Dictionary mapping report types to file paths
    """
    ensure_output_dir(output_dir)
    generator = ReportGenerator(model=model)
    generated_files = {}

    # Generate individual reports
    vendor_content = None
    pestle_content = None
    porters_content = None
    swot_content = None
    rfp_content = None

    if vendor_list:
        vendor_content = generator.generate_vendor_report(vendor_list, category, region)
        if save_intermediate:
            vendor_file = os.path.join(output_dir, "01_vendor_discovery.md")
            generated_files['vendors'] = save_report(vendor_content, vendor_file)

    if pestle_analysis:
        pestle_content = generator.generate_pestle_report(pestle_analysis, category, region)
        if save_intermediate:
            pestle_file = os.path.join(output_dir, "02_pestle_analysis.md")
            generated_files['pestle'] = save_report(pestle_content, pestle_file)

    if porters_analysis:
        porters_content = generator.generate_porters_report(porters_analysis, category, region)
        if save_intermediate:
            porters_file = os.path.join(output_dir, "03_porters_analysis.md")
            generated_files['porters'] = save_report(porters_content, porters_file)

    if swot_analyses:
        swot_content = generator.generate_swot_report(swot_analyses, category, region)
        if save_intermediate:
            swot_file = os.path.join(output_dir, "04_swot_analyses.md")
            generated_files['swot'] = save_report(swot_content, swot_file)

    if rfp_question_set:
        rfp_content = generator.generate_rfp_report(rfp_question_set, category, region)
        if save_intermediate:
            rfp_file = os.path.join(output_dir, "05_rfp_questions.md")
            generated_files['rfp'] = save_report(rfp_content, rfp_file)

    # Generate combined report
    combined_content = generator.generate_combined_report(
        category=category,
        region=region,
        vendor_report=vendor_content,
        pestle_report=pestle_content,
        porters_report=porters_content,
        swot_report=swot_content,
        rfp_report=rfp_content
    )

    complete_file = os.path.join(output_dir, "COMPLETE_ANALYSIS_REPORT.md")
    generated_files['complete'] = save_report(combined_content, complete_file)

    return generated_files


def create_dspy_report_tool():
    """
    Create a DSPy Tool instance for the output_report function.

    Returns
    -------
    dspy.Tool
        DSPy tool for report generation
    """
    return dspy.Tool(
        output_report,
        name="output_report",
        desc="Generate comprehensive markdown reports from analysis results. Creates individual reports per section and combined report. Args: category:str, region:str, output_dir:str, vendor_list:List=None, pestle_analysis=None, porters_analysis=None, swot_analyses:List=None, rfp_question_set=None, save_intermediate:bool=True -> Dict[str,str] of file paths"
    )