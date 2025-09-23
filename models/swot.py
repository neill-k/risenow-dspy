"""SWOT analysis models and DSPy signatures for vendor-specific strategic analysis."""

from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field
import dspy
from models.citation import Citation


class Strengths(BaseModel):
    """Vendor strengths in SWOT analysis."""
    competitive_advantages: List[str] = Field(
        default_factory=list,
        description="Unique selling propositions and differentiators"
    )
    core_competencies: List[str] = Field(
        default_factory=list,
        description="Key capabilities and expertise areas"
    )
    market_position: str = Field(
        ...,
        description="Current market share and positioning assessment"
    )
    resources: List[str] = Field(
        default_factory=list,
        description="Key resources (financial, human, technological, physical)"
    )
    brand_reputation: str = Field(
        ...,
        description="Brand strength and market perception assessment"
    )
    customer_base: str = Field(
        ...,
        description="Description of customer segments and loyalty"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Strategic insights about vendor strengths"
    )
    confidence_level: str = Field(
        default="Medium",
        description="Confidence in strength assessment: Low, Medium, or High"
    )


class Weaknesses(BaseModel):
    """Vendor weaknesses in SWOT analysis."""
    limitations: List[str] = Field(
        default_factory=list,
        description="Operational or capability limitations"
    )
    competitive_disadvantages: List[str] = Field(
        default_factory=list,
        description="Areas where competitors have advantages"
    )
    resource_gaps: List[str] = Field(
        default_factory=list,
        description="Missing capabilities or resources"
    )
    improvement_areas: List[str] = Field(
        default_factory=list,
        description="Areas requiring development or enhancement"
    )
    market_vulnerabilities: List[str] = Field(
        default_factory=list,
        description="Market position weaknesses and risks"
    )
    operational_challenges: List[str] = Field(
        default_factory=list,
        description="Internal operational issues and inefficiencies"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Strategic insights about vendor weaknesses"
    )
    confidence_level: str = Field(
        default="Medium",
        description="Confidence in weakness assessment: Low, Medium, or High"
    )


class Opportunities(BaseModel):
    """External opportunities in SWOT analysis."""
    market_opportunities: List[str] = Field(
        default_factory=list,
        description="Market expansion and growth possibilities"
    )
    technology_trends: List[str] = Field(
        default_factory=list,
        description="Technological advancement opportunities"
    )
    partnership_potential: List[str] = Field(
        default_factory=list,
        description="Strategic collaboration and partnership opportunities"
    )
    geographic_expansion: List[str] = Field(
        default_factory=list,
        description="New market entry and regional expansion possibilities"
    )
    product_development: List[str] = Field(
        default_factory=list,
        description="Product or service innovation opportunities"
    )
    customer_segments: List[str] = Field(
        default_factory=list,
        description="Untapped or emerging customer segments"
    )
    regulatory_changes: List[str] = Field(
        default_factory=list,
        description="Favorable regulatory or policy changes"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Strategic insights about market opportunities"
    )
    confidence_level: str = Field(
        default="Medium",
        description="Confidence in opportunity assessment: Low, Medium, or High"
    )


class Threats(BaseModel):
    """External threats in SWOT analysis."""
    competitive_threats: List[str] = Field(
        default_factory=list,
        description="Competitor actions and market competition risks"
    )
    market_risks: List[str] = Field(
        default_factory=list,
        description="Market conditions and demand-side threats"
    )
    regulatory_risks: List[str] = Field(
        default_factory=list,
        description="Compliance and regulatory challenges"
    )
    technology_disruption: List[str] = Field(
        default_factory=list,
        description="Disruptive technology and innovation threats"
    )
    economic_risks: List[str] = Field(
        default_factory=list,
        description="Economic and financial market threats"
    )
    supply_chain_risks: List[str] = Field(
        default_factory=list,
        description="Supply chain and operational continuity threats"
    )
    reputational_risks: List[str] = Field(
        default_factory=list,
        description="Brand and reputation damage risks"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Strategic insights about external threats"
    )
    confidence_level: str = Field(
        default="Medium",
        description="Confidence in threat assessment: Low, Medium, or High"
    )


class SWOTAnalysis(BaseModel):
    """Complete SWOT analysis for a vendor."""
    vendor_name: str = Field(
        ...,
        description="Name of the vendor being analyzed"
    )
    vendor_website: str = Field(
        ...,
        description="Website URL of the vendor"
    )
    vendor_category: str = Field(
        ...,
        description="Market category or industry segment"
    )
    analysis_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="Date of analysis in YYYY-MM-DD format"
    )
    region: Optional[str] = Field(
        None,
        description="Geographic region of analysis focus"
    )
    strengths: Strengths = Field(
        ...,
        description="Vendor strengths analysis"
    )
    weaknesses: Weaknesses = Field(
        ...,
        description="Vendor weaknesses analysis"
    )
    opportunities: Opportunities = Field(
        ...,
        description="External opportunities analysis"
    )
    threats: Threats = Field(
        ...,
        description="External threats analysis"
    )
    strategic_recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable strategic recommendations based on SWOT"
    )
    competitive_positioning: str = Field(
        ...,
        description="Overall competitive position assessment"
    )
    risk_assessment: str = Field(
        ...,
        description="Overall risk profile and mitigation priorities"
    )
    growth_potential: str = Field(
        ...,
        description="Growth outlook and expansion potential assessment"
    )
    executive_summary: str = Field(
        ...,
        description="High-level summary of SWOT findings and implications"
    )
    data_sources: List[str] = Field(
        default_factory=list,
        description="Sources of information used in the analysis"
    )
    competitors_analyzed: Optional[List[str]] = Field(
        None,
        description="List of competitors considered in comparative analysis"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Evidence sources referenced in this SWOT analysis"
    )


class VendorSWOTAnalysis(dspy.Signature):
    """You are a strategic business analyst specializing in vendor assessment.

    Task: Perform a comprehensive SWOT analysis for the specified vendor.

    You must analyze the vendor's:
    - Internal STRENGTHS: competitive advantages, core competencies, resources
    - Internal WEAKNESSES: limitations, gaps, areas needing improvement
    - External OPPORTUNITIES: market trends, growth possibilities, partnerships
    - External THREATS: competition, market risks, regulatory challenges

    Requirements:
    - Be SPECIFIC to this vendor, not generic to the industry
    - Base insights on available data and research
    - Consider the vendor's position relative to competitors
    - Provide actionable strategic recommendations
    - Assess overall competitive positioning and growth potential

    Output a complete SWOTAnalysis with all sections thoroughly populated.

    IMPORTANT: Include Citation objects from your research in the citations field.
    Each major claim should be supported by source evidence.
    """

    vendor_name: str = dspy.InputField(
        description="Name of the vendor to analyze"
    )
    vendor_website: str = dspy.InputField(
        description="Website URL of the vendor"
    )
    vendor_description: str = dspy.InputField(
        description="Brief description of the vendor's business"
    )
    market_category: str = dspy.InputField(
        description="Market category or industry segment"
    )
    region: Optional[str] = dspy.InputField(
        default=None,
        description="Geographic region for analysis focus"
    )
    competitors: Optional[List[str]] = dspy.InputField(
        default=None,
        description="Key competitors for comparative analysis"
    )
    swot_analysis: SWOTAnalysis = dspy.OutputField(
        description="Complete SWOT analysis with strategic insights"
    )


class JudgeSWOT(dspy.Signature):
    """DSPy signature for LLM-based SWOT analysis evaluation.

    You are an expert strategic consultant evaluating SWOT analysis quality.

    Task: Assess the provided SWOT analysis and return:
    - score: quality rating ∈ [0, 1]
    - feedback: ≤75 words of actionable improvements

    Quality criteria:
    1. SPECIFICITY: Vendor-specific vs generic industry insights (30%)
    2. COMPLETENESS: All SWOT quadrants thoroughly analyzed (25%)
    3. ACTIONABILITY: Practical, implementable recommendations (20%)
    4. EVIDENCE: Data-backed vs unsupported claims (15%)
    5. BALANCE: Appropriate coverage across all four areas (10%)

    Penalize for:
    - Generic insights applicable to any vendor
    - Missing or superficial sections
    - Vague or impractical recommendations
    - Unsupported assertions
    - Excessive focus on one quadrant

    Output MUST be a score [0-1] and constructive feedback.
    """

    vendor_name: str = dspy.InputField(
        description="Name of the vendor analyzed"
    )
    market_category: str = dspy.InputField(
        description="Market category or industry"
    )
    swot_analysis: SWOTAnalysis = dspy.InputField(
        description="SWOT analysis to evaluate"
    )
    score: float = dspy.OutputField(
        desc="Overall quality score ∈ [0,1]"
    )
    feedback: str = dspy.OutputField(
        desc="≤75 words of specific improvements"
    )

