"""DSPy signatures and models for report generation."""

from typing import List, Optional, Any
import dspy
from pydantic import BaseModel, Field


class MarkdownReport(BaseModel):
    """Structured markdown report output."""
    content: str = Field(description="Markdown formatted content")
    filename: str = Field(description="Filename for the report")
    section_title: str = Field(description="Section title for the report")
    metadata: dict = Field(default_factory=dict, description="Report metadata")


class ReportGenerationSignature(dspy.Signature):
    """Generate a markdown report from analysis results."""

    # Input fields
    category: str = dspy.InputField(desc="Business category being analyzed")
    region: str = dspy.InputField(desc="Geographic region for analysis")
    analysis_type: str = dspy.InputField(desc="Type of analysis (vendor, pestle, porters, swot, rfp)")
    analysis_data: Any = dspy.InputField(desc="Analysis results data")

    # Output field
    markdown_content: str = dspy.OutputField(desc="Generated markdown report content")


class CombinedReportSignature(dspy.Signature):
    """Combine multiple markdown reports into a single comprehensive report."""

    # Input fields
    category: str = dspy.InputField(desc="Business category")
    region: str = dspy.InputField(desc="Geographic region")
    vendor_content: Optional[str] = dspy.InputField(desc="Vendor discovery markdown content", default=None)
    pestle_content: Optional[str] = dspy.InputField(desc="PESTLE analysis markdown content", default=None)
    porters_content: Optional[str] = dspy.InputField(desc="Porter's Five Forces markdown content", default=None)
    swot_content: Optional[str] = dspy.InputField(desc="SWOT analyses markdown content", default=None)
    rfp_content: Optional[str] = dspy.InputField(desc="RFP questions markdown content", default=None)

    # Output field
    combined_report: str = dspy.OutputField(desc="Combined comprehensive markdown report")


class ReportMetadata(BaseModel):
    """Metadata for generated reports."""
    category: str
    region: str
    timestamp: str
    analysis_types: List[str]
    vendor_count: Optional[int] = None
    swot_count: Optional[int] = None
    rfp_questions: Optional[int] = None
    output_directory: str
    individual_reports: List[str] = Field(default_factory=list)
    combined_report_path: Optional[str] = None