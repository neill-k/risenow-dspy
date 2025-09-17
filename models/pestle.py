"""PESTLE analysis models and DSPy signatures for comprehensive market analysis."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import dspy


class PoliticalFactors(BaseModel):
    """Political factors in PESTLE analysis."""
    government_policies: List[str] = Field(
        default_factory=list,
        description="Relevant government policies affecting the market"
    )
    regulations: List[str] = Field(
        default_factory=list,
        description="Key regulations and compliance requirements"
    )
    trade_agreements: List[str] = Field(
        default_factory=list,
        description="Trade agreements and international relations impacts"
    )
    political_stability: str = Field(
        ...,
        description="Assessment of political stability and risk"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key political insights and their business implications"
    )


class EconomicFactors(BaseModel):
    """Economic factors in PESTLE analysis."""
    market_size: str = Field(
        ...,
        description="Current market size and valuation"
    )
    growth_rate: str = Field(
        ...,
        description="Market growth rate and projections"
    )
    economic_indicators: Dict[str, str] = Field(
        default_factory=dict,
        description="Key economic indicators (GDP, inflation, interest rates, etc.)"
    )
    market_trends: List[str] = Field(
        default_factory=list,
        description="Major economic and market trends"
    )
    investment_climate: str = Field(
        ...,
        description="Assessment of investment climate and opportunities"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key economic insights and their business implications"
    )


class SocialFactors(BaseModel):
    """Social factors in PESTLE analysis."""
    demographics: Dict[str, str] = Field(
        default_factory=dict,
        description="Key demographic information and trends"
    )
    consumer_trends: List[str] = Field(
        default_factory=list,
        description="Current consumer behavior trends and preferences"
    )
    cultural_factors: List[str] = Field(
        default_factory=list,
        description="Cultural influences on the market"
    )
    lifestyle_changes: List[str] = Field(
        default_factory=list,
        description="Lifestyle shifts affecting demand"
    )
    social_values: List[str] = Field(
        default_factory=list,
        description="Evolving social values and their impact"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key social insights and their business implications"
    )


class TechnologicalFactors(BaseModel):
    """Technological factors in PESTLE analysis."""
    innovations: List[str] = Field(
        default_factory=list,
        description="Key technological innovations in the sector"
    )
    disruptions: List[str] = Field(
        default_factory=list,
        description="Potential technological disruptions"
    )
    digital_transformation: str = Field(
        ...,
        description="State of digital transformation in the industry"
    )
    automation_impact: str = Field(
        ...,
        description="Impact of automation and AI on the market"
    )
    emerging_technologies: List[str] = Field(
        default_factory=list,
        description="Emerging technologies to watch"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key technological insights and their business implications"
    )


class LegalFactors(BaseModel):
    """Legal factors in PESTLE analysis."""
    compliance_requirements: List[str] = Field(
        default_factory=list,
        description="Major compliance and regulatory requirements"
    )
    liability_issues: List[str] = Field(
        default_factory=list,
        description="Potential liability concerns and risks"
    )
    contract_considerations: List[str] = Field(
        default_factory=list,
        description="Important contract and legal agreement factors"
    )
    intellectual_property: List[str] = Field(
        default_factory=list,
        description="IP considerations and protections"
    )
    legal_changes: List[str] = Field(
        default_factory=list,
        description="Upcoming or recent legal changes affecting the market"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key legal insights and their business implications"
    )


class EnvironmentalFactors(BaseModel):
    """Environmental factors in PESTLE analysis."""
    sustainability_requirements: List[str] = Field(
        default_factory=list,
        description="Sustainability standards and requirements"
    )
    climate_impact: str = Field(
        ...,
        description="Climate change impacts on the industry"
    )
    green_initiatives: List[str] = Field(
        default_factory=list,
        description="Green initiatives and opportunities"
    )
    environmental_regulations: List[str] = Field(
        default_factory=list,
        description="Environmental regulations and compliance"
    )
    resource_availability: List[str] = Field(
        default_factory=list,
        description="Natural resource considerations"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key environmental insights and their business implications"
    )


class PESTLEAnalysis(BaseModel):
    """Complete PESTLE analysis for a market or category."""
    category: str = Field(..., description="The market category being analyzed")
    region: Optional[str] = Field(None, description="Geographic region of analysis")
    political: PoliticalFactors = Field(..., description="Political factors analysis")
    economic: EconomicFactors = Field(..., description="Economic factors analysis")
    social: SocialFactors = Field(..., description="Social factors analysis")
    technological: TechnologicalFactors = Field(..., description="Technological factors analysis")
    legal: LegalFactors = Field(..., description="Legal factors analysis")
    environmental: EnvironmentalFactors = Field(..., description="Environmental factors analysis")
    strategic_recommendations: List[str] = Field(
        default_factory=list,
        description="Strategic recommendations based on PESTLE analysis"
    )
    opportunities: List[str] = Field(
        default_factory=list,
        description="Key opportunities identified"
    )
    threats: List[str] = Field(
        default_factory=list,
        description="Key threats and risks identified"
    )
    executive_summary: str = Field(
        ...,
        description="Executive summary of the PESTLE analysis"
    )


class PESTLEMarketAnalysis(dspy.Signature):
    """You are a strategic market analyst specializing in PESTLE analysis.
    Your task is to conduct a comprehensive PESTLE (Political, Economic, Social,
    Technological, Legal, Environmental) analysis for the specified market category
    and region.

    Use the provided tools to research each factor thoroughly:
    - Political: Government policies, regulations, trade agreements, political stability
    - Economic: Market size, growth rates, economic indicators, investment climate
    - Social: Demographics, consumer trends, cultural factors, lifestyle changes
    - Technological: Innovation, disruption, digital transformation, emerging tech
    - Legal: Compliance requirements, liability issues, contracts, IP considerations
    - Environmental: Sustainability, climate impact, green initiatives, regulations

    Provide actionable insights, strategic recommendations, and identify key
    opportunities and threats based on your analysis.
    """

    category: str = dspy.InputField(
        description="The market category to analyze (e.g., 'Industrial Supplies', 'SaaS Solutions')"
    )
    region: Optional[str] = dspy.InputField(
        default=None,
        description="Geographic region for the analysis (e.g., 'United States', 'Europe')"
    )
    focus_areas: Optional[List[str]] = dspy.InputField(
        default=None,
        description="Specific areas to emphasize in the analysis"
    )
    pestle_analysis: PESTLEAnalysis = dspy.OutputField(
        description="Comprehensive PESTLE analysis with all factors and recommendations"
    )


class JudgePESTLE(dspy.Signature):
    """You are an expert business strategist evaluating PESTLE analyses.

    Task: Given a PESTLE analysis for the target category and region, evaluate:
    - Comprehensiveness: All PESTLE factors thoroughly covered
    - Depth: Detailed insights with supporting evidence
    - Relevance: Factors directly relevant to the category/region
    - Actionability: Clear, practical recommendations
    - Accuracy: Factually correct and current information

    Return:
    - score: Overall quality value ∈ [0, 1]
    - feedback: ≤50-word actionable comment on improvements needed
    """

    category: str = dspy.InputField()
    region: Optional[str] = dspy.InputField()
    pestle_analysis: dict = dspy.InputField()
    score: float = dspy.OutputField(desc="Overall quality ∈ [0,1]")
    feedback: str = dspy.OutputField(desc="≤50 words, concrete improvements")