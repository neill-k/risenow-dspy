"""RFP generation models and DSPy signatures."""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import dspy
from models.citation import Citation


class InsightSourceSummary(BaseModel):
    """Normalized insight bundle aggregated from upstream analyses."""
    source: str = Field(..., description="Source identifier such as 'pestle', 'porters', 'swot', or 'vendor'.")
    key_points: List[str] = Field(default_factory=list, description="Bullet points to surface during RFP drafting.")
    confidence_notes: Optional[str] = Field(default=None, description="Optional commentary on confidence or caveats.")
    citation_ids: List[str] = Field(
        default_factory=list,
        description="Citation identifiers supporting this insight summary.",
    )


class ReferenceDocument(BaseModel):
    """Minimal representation of a public RFP or comparable document."""
    title: str = Field(..., description="Name or headline of the reference document.")
    url: str = Field(..., description="Resolvable link to the reference source.")
    citation_id: Optional[str] = Field(
        default=None,
        description="Citation identifier matching the Tavily source for this document.",
    )
    summary: str = Field(..., description="Short summary of why this reference matters.")
    extracted_requirements: List[str] = Field(
        default_factory=list,
        description="Key requirements or clauses worth reusing."
    )


class RFPQuestion(BaseModel):
    """Single RFP question with supporting metadata."""
    section: str = Field(..., description="Section tag the question belongs to.")
    prompt: str = Field(..., description="Actual question text to include in the RFP.")
    rationale: Optional[str] = Field(None, description="Why this question matters for evaluation.")
    referenced_insights: List[str] = Field(
        default_factory=list,
        description="Identifiers or snippets that informed this question.",
    )
    citation_ids: List[str] = Field(
        default_factory=list,
        description="Citation identifiers supporting this question.",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Resolved citation records backing this question"
    )


class RFPSection(BaseModel):
    """Logical grouping of related RFP questions."""
    name: str = Field(..., description="Human-readable section label.")
    description: Optional[str] = Field(None, description="Brief explanation of the section focus.")
    questions: List[RFPQuestion] = Field(..., description="Questions belonging to this section.")


class RFPQuestionSet(BaseModel):
    """Complete RFP question set composed of multiple sections."""
    category: str = Field(..., description="Market category or project context.")
    region: Optional[str] = Field(None, description="Geographic focus if applicable.")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        description="UTC timestamp of generation in ISO-8601 format."
    )
    sections: List[RFPSection] = Field(..., description="Ordered sections covering the RFP questionnaire.")
    total_questions: int = Field(..., description="Number of questions contained across all sections.")
    reference_documents: List[ReferenceDocument] = Field(
        default_factory=list,
        description="Reference RFPs or resources consulted during generation."
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Evidence sources aggregated across the question set"
    )


class RFPInsightExtractionSignature(dspy.Signature):
    """Distill actionable insights from prior analyses (PESTLE, Porter's, SWOT, vendors)."""

    category: str = dspy.InputField(description="Market category under consideration.")
    region: Optional[str] = dspy.InputField(default=None, description="Geographic focus if provided.")
    pestle_analysis: Optional[dict] = dspy.InputField(default=None, description="Serialized PESTLE analysis results.")
    porters_analysis: Optional[dict] = dspy.InputField(default=None, description="Serialized Porter's Five Forces analysis.")
    swot_analyses: Optional[List[dict]] = dspy.InputField(default=None, description="List of vendor SWOT analyses.")
    vendor_list: Optional[List[dict]] = dspy.InputField(default=None, description="Vendor discovery results to mine for insights.")
    insight_summaries: List[InsightSourceSummary] = dspy.OutputField(
        description="Normalized insight bundles grouped by source."
    )
    synthesis_notes: Optional[str] = dspy.OutputField(
        default=None,
        description="High-level takeaways for downstream RFP drafting."
    )


class RFPReferenceGatherSignature(dspy.Signature):
    """Search and extract requirements from public RFP exemplars."""

    category: str = dspy.InputField(description="Target procurement category.")
    vendor_names: Optional[List[str]] = dspy.InputField(default=None, description="Vendors to use as search anchors.")
    region: Optional[str] = dspy.InputField(default=None, description="Regional qualifier for search results.")
    max_documents: int = dspy.InputField(default=10, description="Maximum number of reference RFPs to summarize.")
    reference_documents: List[ReferenceDocument] = dspy.OutputField(
        description="Reference RFP summaries with extracted requirements."
    )


class RFPQuestionGeneratorSignature(dspy.Signature):
    """Generate an RFP organized into logical sections. You should search for publicly available RFPs in the target category and region to inform your question set. Make sure to add them to the reference documents. Use the insights provided to tailor the questions to the specific market context and challenges. Ensure that the questions are clear, concise, and relevant to evaluating vendors effectively."""

    category: str = dspy.InputField(description="Market category or project scope.")
    region: Optional[str] = dspy.InputField(default=None, description="Geographic focus if applicable.")
    insight_summaries: List[dict] = dspy.InputField(description="Normalized insights from prior analyses.")
    reference_documents: List[dict] = dspy.InputField(description="Extracted reference RFP content.")
    expected_question_count: int = dspy.InputField(default=100, description="Target number of questions to produce.")
    question_set: RFPQuestionSet = dspy.OutputField(
        description="Structured RFP question set with questions grouped by section."
    )


class JudgeRFP(dspy.Signature):
    """Evaluate RFP question set quality, completeness, and alignment."""

    category: str = dspy.InputField()
    region: Optional[str] = dspy.InputField()
    question_set: dict = dspy.InputField()
    score: float = dspy.OutputField(desc="Overall quality score in [0,1].")
    feedback: str = dspy.OutputField(desc="Actionable feedback, ≤50 words.")


