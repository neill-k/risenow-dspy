"""Pydantic models and DSPy signatures for the vendor discovery system."""

from typing import List, Optional

from pydantic import BaseModel, Field
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
            "One or more verified contact email addresses. Use the vendor contact"
            " lookup tool before falling back to raw Tavily calls."
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


class VendorContactDetails(BaseModel):
    """Normalized contact artifact returned by the vendor contact sub-agent."""

    vendor_name: str = Field(..., description="Vendor name copied from the parent request")
    vendor_website: Optional[str] = Field(
        default=None,
        description="Seed website used to locate the contact page, if known",
    )
    contact_emails: List[ContactEmail] = Field(
        default_factory=list,
        description="Verified email addresses surfaced by the contact lookup sub-agent",
    )
    phone_numbers: List[PhoneNumber] = Field(
        default_factory=list,
        description="Verified phone numbers surfaced by the contact lookup sub-agent",
    )
    supporting_urls: List[str] = Field(
        default_factory=list,
        description="List of contact/support page URLs that back the discovered details",
    )
    summary: Optional[str] = Field(
        default=None,
        description="≤40 word recap of the contact findings and any caveats",
    )


class VendorContactLookup(dspy.Signature):
    """You are a specialized contact discovery assistant.

    Objective: Find up-to-date contact email(s) and phone number(s) for the
    specified vendor. Prefer official pages owned by the vendor. You are limited
    to at most 8 reasoning/tool steps, so plan carefully:

      • If a `vendor_website` is provided, start from that domain and look for
        `contact`, `support`, or `about` pages.
      • Use `tavily_search` for targeted queries ("<vendor> contact email",
        "<vendor> phone number") and fall back to `tavily_extract` only when
        snippets are insufficient.
      • Return structured contact details only when you can cite supporting URLs;
        otherwise return empty lists.

    Respond with normalized contact details that the parent agent can merge into
    its vendor record without additional parsing.
    """

    vendor_name: str = dspy.InputField(description="The vendor's name")
    vendor_website: Optional[str] = dspy.InputField(
        default=None,
        description="Known vendor website to seed the lookup (optional)",
    )
    country_or_region: Optional[str] = dspy.InputField(
        default=None,
        description="Country or region to prioritize when multiple contacts exist",
    )
    contact_emails: List[ContactEmail] = dspy.OutputField(
        description="Verified email contacts (may be empty if none found)",
    )
    phone_numbers: List[PhoneNumber] = dspy.OutputField(
        description="Verified phone contacts (may be empty if none found)",
    )
    supporting_urls: List[str] = dspy.OutputField(
        description="Contact/support URLs used to verify the details",
    )
    summary: Optional[str] = dspy.OutputField(
        description="≤40 word recap of findings or blockers",
    )



class VendorSearchResult(dspy.Signature):
    """You are a vendor-discovery AI assistant. You are given a list of tools and
    must decide which tool(s) to invoke and how, in order to return the top *n*
    vendors for the requested `category` (optionally restricted to
    `country_or_region`).

    Always plan for contact completeness:
      1. Collect candidate vendors and official domains with `tavily_search`.
      2. Delegate contact discovery to the `lookup_vendor_contacts` tool whenever
         you need phone/email details (pass the vendor website when known).
      3. Only fall back to direct `tavily_extract` calls if the contact tool
         fails to return any details and you still believe contacts exist.

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
