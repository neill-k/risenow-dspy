"""Porter's 5 Forces models and DSPy signatures for competitive analysis."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import dspy


class ThreatOfNewEntrants(BaseModel):
    """Threat of new entrants force in Porter's 5 Forces analysis."""
    barriers_to_entry: List[str] = Field(
        default_factory=list,
        description="Key barriers preventing new competitors from entering"
    )
    capital_requirements: str = Field(
        ...,
        description="Capital investment needed to enter the market"
    )
    economies_of_scale: str = Field(
        ...,
        description="Scale advantages enjoyed by existing players"
    )
    regulatory_barriers: List[str] = Field(
        default_factory=list,
        description="Government policies and regulations affecting entry"
    )
    brand_loyalty: str = Field(
        ...,
        description="Customer loyalty to existing brands"
    )
    threat_level: str = Field(
        ...,
        description="Overall threat level: Low, Medium, or High"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key insights about new entrant threats"
    )


class BargainingPowerSuppliers(BaseModel):
    """Bargaining power of suppliers force in Porter's 5 Forces analysis."""
    supplier_concentration: str = Field(
        ...,
        description="Number and concentration of suppliers in the market"
    )
    switching_costs: str = Field(
        ...,
        description="Cost of switching between suppliers"
    )
    unique_resources: List[str] = Field(
        default_factory=list,
        description="Unique or differentiated resources controlled by suppliers"
    )
    forward_integration_threat: str = Field(
        ...,
        description="Risk of suppliers integrating forward into the industry"
    )
    supplier_dependency: str = Field(
        ...,
        description="Industry's dependency on key suppliers"
    )
    power_level: str = Field(
        ...,
        description="Overall power level: Low, Medium, or High"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key insights about supplier power"
    )


class BargainingPowerBuyers(BaseModel):
    """Bargaining power of buyers force in Porter's 5 Forces analysis."""
    buyer_concentration: str = Field(
        ...,
        description="Number and concentration of buyers"
    )
    price_sensitivity: str = Field(
        ...,
        description="How sensitive buyers are to price changes"
    )
    switching_costs: str = Field(
        ...,
        description="Cost for buyers to switch to alternatives"
    )
    backward_integration_threat: str = Field(
        ...,
        description="Risk of buyers integrating backward into the industry"
    )
    information_availability: str = Field(
        ...,
        description="Buyer access to market and product information"
    )
    power_level: str = Field(
        ...,
        description="Overall power level: Low, Medium, or High"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key insights about buyer power"
    )


class ThreatOfSubstitutes(BaseModel):
    """Threat of substitute products/services in Porter's 5 Forces analysis."""
    substitute_products: List[str] = Field(
        default_factory=list,
        description="Key substitute products or services"
    )
    relative_price_performance: str = Field(
        ...,
        description="Price-performance comparison with substitutes"
    )
    switching_costs: str = Field(
        ...,
        description="Cost for customers to switch to substitutes"
    )
    buyer_propensity_to_substitute: str = Field(
        ...,
        description="Customer willingness to use substitutes"
    )
    innovation_trends: List[str] = Field(
        default_factory=list,
        description="Innovations that could create new substitutes"
    )
    threat_level: str = Field(
        ...,
        description="Overall threat level: Low, Medium, or High"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key insights about substitute threats"
    )


class CompetitiveRivalry(BaseModel):
    """Competitive rivalry among existing competitors in Porter's 5 Forces."""
    industry_concentration: str = Field(
        ...,
        description="Market concentration and key competitors"
    )
    industry_growth_rate: str = Field(
        ...,
        description="Industry growth rate and market maturity"
    )
    differentiation_level: str = Field(
        ...,
        description="Degree of product/service differentiation"
    )
    exit_barriers: List[str] = Field(
        default_factory=list,
        description="Barriers preventing companies from leaving the industry"
    )
    competitive_strategies: List[str] = Field(
        default_factory=list,
        description="Common competitive strategies in the industry"
    )
    major_competitors: List[str] = Field(
        default_factory=list,
        description="Major competitors and their market positions"
    )
    intensity_level: str = Field(
        ...,
        description="Overall rivalry intensity: Low, Medium, or High"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key insights about competitive rivalry"
    )


class PortersFiveForcesAnalysis(BaseModel):
    """Complete Porter's 5 Forces analysis for a market or industry."""
    category: str = Field(..., description="The market category being analyzed")
    region: Optional[str] = Field(None, description="Geographic region of analysis")
    threat_of_new_entrants: ThreatOfNewEntrants = Field(
        ..., description="Analysis of new entrant threats"
    )
    bargaining_power_suppliers: BargainingPowerSuppliers = Field(
        ..., description="Analysis of supplier bargaining power"
    )
    bargaining_power_buyers: BargainingPowerBuyers = Field(
        ..., description="Analysis of buyer bargaining power"
    )
    threat_of_substitutes: ThreatOfSubstitutes = Field(
        ..., description="Analysis of substitute threats"
    )
    competitive_rivalry: CompetitiveRivalry = Field(
        ..., description="Analysis of competitive rivalry"
    )
    industry_attractiveness: str = Field(
        ...,
        description="Overall industry attractiveness assessment"
    )
    strategic_recommendations: List[str] = Field(
        default_factory=list,
        description="Strategic recommendations based on 5 Forces analysis"
    )
    opportunities: List[str] = Field(
        default_factory=list,
        description="Key opportunities identified"
    )
    threats: List[str] = Field(
        default_factory=list,
        description="Key threats identified"
    )
    executive_summary: str = Field(
        ...,
        description="Executive summary of the Porter's 5 Forces analysis"
    )


class PortersFiveForcesSignature(dspy.Signature):
    """You are a strategic business analyst specializing in Porter's 5 Forces analysis.
    Your task is to conduct a comprehensive competitive analysis using Porter's 5 Forces
    framework for the specified market category and region.

    Use the provided tools to research each force thoroughly:
    - Threat of New Entrants: Entry barriers, capital requirements, regulations
    - Bargaining Power of Suppliers: Supplier concentration, switching costs, integration
    - Bargaining Power of Buyers: Buyer concentration, price sensitivity, alternatives
    - Threat of Substitutes: Alternative products, switching costs, performance
    - Competitive Rivalry: Industry concentration, growth, differentiation

    Provide actionable strategic insights, recommendations, and identify key
    opportunities and threats based on your competitive analysis.
    """

    category: str = dspy.InputField(
        description="The market category to analyze (e.g., 'Cloud Computing', 'E-commerce')"
    )
    region: Optional[str] = dspy.InputField(
        default=None,
        description="Geographic region for the analysis (e.g., 'United States', 'Europe')"
    )
    focus_areas: Optional[List[str]] = dspy.InputField(
        default=None,
        description="Specific forces to emphasize in the analysis"
    )
    porters_analysis: PortersFiveForcesAnalysis = dspy.OutputField(
        description="Comprehensive Porter's 5 Forces analysis with all forces and recommendations"
    )


class JudgePorters(dspy.Signature):
    """You are an expert business strategist evaluating Porter's 5 Forces analyses.

    Task: Given a Porter's 5 Forces analysis for the target category and region, evaluate:
    - Comprehensiveness: All five forces thoroughly analyzed
    - Depth: Detailed insights with supporting evidence
    - Relevance: Forces directly relevant to the category/region
    - Actionability: Clear, practical strategic recommendations
    - Accuracy: Factually correct competitive assessment

    Return:
    - score: Overall quality value ∈ [0, 1]
    - feedback: ≤50-word actionable comment on improvements needed
    """

    category: str = dspy.InputField()
    region: Optional[str] = dspy.InputField()
    porters_analysis: dict = dspy.InputField()
    score: float = dspy.OutputField(desc="Overall quality ∈ [0,1]")
    feedback: str = dspy.OutputField(desc="≤50 words, concrete improvements")