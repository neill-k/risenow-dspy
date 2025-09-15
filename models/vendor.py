"""Pydantic models and DSPy signatures for the vendor discovery system."""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
import dspy


class ContactEmail(BaseModel):
    """Model for vendor contact email information."""
    email: str = Field(..., description="The email address")
    description: Optional[str] = Field(None, description="1-3 words describing the purpose of this email address")


class PhoneNumber(BaseModel):
    """Model for vendor phone number information."""
    number: str = Field(..., description="The phone number, in E.164 format")
    description: Optional[str] = Field(None, description="1-3 words describing the purpose of this phone number")


class Vendor(BaseModel):
    """Model for vendor information."""
    name: str = Field(..., description="The name of the vendor")
    website: HttpUrl = Field(..., description="The vendor's website URL")
    description: str = Field(..., description="A brief description of the vendor")
    justification: str = Field(..., description="A brief justification for why this vendor was chosen")
    contact_emails: Optional[List[ContactEmail]] = Field(default=None, description="A list of contact email addresses for the vendor")
    phone_numbers: Optional[List[PhoneNumber]] = Field(default=None, description="A list of contact phone numbers for the vendor")
    countries_served: Optional[List[str]] = Field(default=None, description="A list of countries where the vendor operates")


class VendorSearchResult(dspy.Signature):
    """DSPy signature for vendor discovery AI assistant."""
    
    """You are a vendor discovery AI assistant. You are given a list of tools to use to find the top 'n' vendors for a given category.
    You should decide the right tool to use, and how to use it, to find the best vendors for the given category."""
    
    category: str = dspy.InputField(description="The category of vendors to find, e.g. 'cloud hosting providers', 'CRM systems', etc.")
    n: int = dspy.InputField(description="The number of top vendors to find")
    country_or_region: Optional[str] = dspy.InputField(default=None, description="An optional country or region to focus the search on, e.g. 'United States', 'Europe', etc.")
    vendor_list: List[Vendor] = dspy.OutputField(description="A list of the top 'n' vendors found, with details as specified in the Vendor model")


class JudgeVendors(dspy.Signature):
    """DSPy signature for evaluating vendor lists."""
    
    """
    You are an expert procurement evaluator.
    Task: Given a vendor_list for the target category and optional region, return a single overall quality score in [0,1]
    and a brief feedback string (<= 50 words).

    Definition of "quality":
      • Relevance to "General Industrial Supplies" (broad MRO/catalog; not a single-product vendor; not a marketplace).
      • Region fit (serves the requested country_or_region if provided).
      • Non-duplication (unique suppliers).
      • Basic contact completeness (site + at least one email/phone per vendor).
      • Overall credibility (well-known or plausibly legitimate suppliers).

    Output strictly as a number in [0,1] and a short feedback sentence. Do not restate the vendor list.
    """
    
    category: str = dspy.InputField()
    country_or_region: Optional[str] = dspy.InputField()
    vendor_list: List[dict] = dspy.InputField()
    score: float = dspy.OutputField(desc="Overall quality ∈ [0,1]")
    feedback: str = dspy.OutputField(desc="≤50 words, concrete fixes")