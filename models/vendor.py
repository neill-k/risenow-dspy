"""Pydantic models and DSPy signatures for the vendor discovery system."""

from typing import List, Optional

from pydantic import BaseModel, Field, FieldValidationInfo, field_validator
import dspy



class ContactEmail(BaseModel):
    """Model for vendor contact email information."""

    email: str = Field(
        ...,
        description=(
            "Official vendor email address. Prefer addresses found on the vendor's"
            " own website or trustworthy directories."
        ),
    )
    description: Optional[str] = Field(
        None,
        description="1-3 words describing the purpose of this email address",
    )


class PhoneNumber(BaseModel):
    """Model for vendor phone number information."""

    number: str = Field(
        ...,
        description=(
            "The phone number, formatted to E.164 when possible and verified from an"
            " official vendor contact page."
        ),
    )
    description: Optional[str] = Field(
        None,
        description="1-3 words describing the purpose of this phone number",
    )


class Vendor(BaseModel):
    """Model for vendor information."""

    name: str = Field(..., description="The name of the vendor")
    website: str = Field(..., description="The vendor's website URL")
    description: str = Field(..., description="A brief description of the vendor")
    justification: str = Field(..., description="A brief justification for why this vendor was chosen")
    contact_emails: List[ContactEmail] = Field(
        default=...,
        description=(
            "One or more verified contact email addresses. Use the Tavily tools to"
            " inspect the vendor's contact or support pages and skip vendors without"
            " an email."
        ),
    )
    phone_numbers: List[PhoneNumber] = Field(
        default=...,
        description=(
            "One or more verified contact phone numbers from official sources."
            " Avoid generic directory listings unless the vendor website lacks a"
            " published number."
        ),
    )
    countries_served: Optional[List[str]] = Field(
        default=None,
        description="A list of countries where the vendor operates",
    )



class VendorSearchResult(dspy.Signature):
    """You are a vendor-discovery AI assistant. You are given a list of tools and
    must decide which tool(s) to invoke and how, in order to return the top *n*
    vendors for the requested `category` (optionally restricted to
    `country_or_region`).

    Always plan for contact completeness:
      1. Use `tavily_search` to find the vendor's official site and dedicated
         contact/support pages (queries like "<vendor> contact email").
      2. Call `tavily_extract` on those pages to capture phone numbers and
         email addresses; prefer the vendor's own domain over directories.

    Populate `vendor_list` with fully-specified `Vendor` objects that satisfy
    the data-model requirements and cite the sources you used.
    """
    
    category: str = dspy.InputField(description="The category of vendors to find, e.g. 'cloud hosting providers', 'CRM systems', etc.")
    n: int = dspy.InputField(description="The number of top vendors to find")
    country_or_region: Optional[str] = dspy.InputField(default=None, description="An optional country or region to focus the search on, e.g. 'United States', 'Europe', etc.")
    vendor_list: List[Vendor] = dspy.OutputField(description="A list of the top 'n' vendors found, with details as specified in the Vendor model")


class JudgeVendors(dspy.Signature):
    """DSPy signature for LLM-based vendor-list evaluation.

    You are an expert procurement evaluator.
    Task: Given a `vendor_list` for the target `category` (and optional
    `country_or_region`) return:
        • `score` – a single overall quality value ∈ [0, 1]
        • `feedback` – ≤ 50-word, actionable comment

    Quality considerations:
      • Relevance to `category`.
      • Region fit (serves `country_or_region`, if provided).
      • No duplicates.
      • Contact completeness (website + ≥1 email/phone).
      • Credibility (recognised or plausibly legitimate suppliers).

    Output MUST be a number between 0 and 1 and a short feedback sentence –
    do **not** restate the vendor list.
    """
    
    category: str = dspy.InputField()
    country_or_region: Optional[str] = dspy.InputField()
    vendor_list: List[dict] = dspy.InputField()
    score: float = dspy.OutputField(desc="Overall quality ∈ [0,1]")
    feedback: str = dspy.OutputField(desc="≤50 words, concrete fixes")
