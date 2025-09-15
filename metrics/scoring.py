"""Scoring and evaluation metrics for vendor quality assessment."""

import re
from typing import List, Dict, Any, Optional
import dspy
from dspy import Example
from ..models.vendor import Vendor, JudgeVendors
from ..data.examples import general_industrial_supplies_example_n15


def contains_phone_number(vendor: Vendor) -> float:
    """Score based on phone number presence and format quality."""
    if not vendor.phone_numbers or len(vendor.phone_numbers) == 0:
        return 0.0
    
    score = 0.5  # Base score for having any phone number
    
    # Bonus for properly formatted numbers
    phone_pattern = r'^[\+]?[1-9][\d\s\-\(\)]{7,15}$'
    for phone in vendor.phone_numbers:
        if re.match(phone_pattern, phone.number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
            score += 0.2
            break
    
    # Bonus for having description
    if any(phone.description for phone in vendor.phone_numbers):
        score += 0.1
    
    return min(score, 1.0)


def contains_contact_email(vendor: Vendor) -> float:
    """Score based on email presence, format, and type quality."""
    if not vendor.contact_emails or len(vendor.contact_emails) == 0:
        return 0.0
    
    score = 0.5  # Base score for having any email
    
    # Email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    valid_emails = [email for email in vendor.contact_emails 
                   if re.match(email_pattern, email.email)]
    
    if valid_emails:
        score += 0.2
    
    # Bonus for business-appropriate email domains (not Gmail, Yahoo, etc.)
    business_domains = any(
        not any(domain in email.email.lower() for domain in ['gmail', 'yahoo', 'hotmail', 'outlook'])
        for email in valid_emails
    )
    if business_domains:
        score += 0.2
    
    # Bonus for having description
    if any(email.description for email in vendor.contact_emails):
        score += 0.1
    
    return min(score, 1.0)


def contains_countries_served(vendor: Vendor) -> float:
    """Score based on geographic coverage appropriateness."""
    if not vendor.countries_served or len(vendor.countries_served) == 0:
        return 0.0
    
    # Base score for having any country info
    score = 0.3
    
    # Bonus for multiple countries (shows scale)
    if len(vendor.countries_served) > 1:
        score += 0.2
    
    # Bonus for including major markets
    major_markets = {'United States', 'Canada', 'United Kingdom', 'Germany', 'Japan', 'China'}
    if any(country in major_markets for country in vendor.countries_served):
        score += 0.3
    
    # Bonus for regional coverage
    if len(vendor.countries_served) >= 5:
        score += 0.2
    
    return min(score, 1.0)


def comprehensive_vendor_score(vendor: Vendor, weights: Optional[dict] = None) -> dict:
    """Calculate comprehensive vendor quality score with breakdown."""
    
    default_weights = {
        'phone': 0.4,
        'email': 0.4,
        'countries': 0.2,
    }
    
    weights = weights or default_weights
    
    scores = {
        'phone': contains_phone_number(vendor),
        'email': contains_contact_email(vendor),
        'countries': contains_countries_served(vendor),
    }
    
    weighted_score = sum(scores[key] * weights[key] for key in scores)
    
    return {
        'overall_score': weighted_score,
        'component_scores': scores,
        'weights_used': weights
    }


def make_llm_judge_metric(max_items: int = 8, include_individual_scores: bool = False, gold: Example = general_industrial_supplies_example_n15):
    """Create an LLM-based metric for evaluating vendor lists."""
    judge = dspy.Predict(JudgeVendors)
    
    def _enhanced_slim(v: Any) -> Dict[str, Any]:
        """Enhanced slimming with quality indicators."""
        if isinstance(v, dict):
            name = v.get("name")
            website = str(v.get("website") or "")
            desc = v.get("description") or ""
            just = v.get("justification") or ""
            emails = v.get("contact_emails") or []
            phones = v.get("phone_numbers") or []
            countries = v.get("countries_served") or []
        else:
            name = getattr(v, "name", None)
            website = str(getattr(v, "website", "") or "")
            desc = getattr(v, "description", "") or ""
            just = getattr(v, "justification", "") or ""
            emails = list(getattr(v, "contact_emails", []) or [])
            phones = list(getattr(v, "phone_numbers", []) or [])
            countries = list(getattr(v, "countries_served", []) or [])
        
        # Add quality indicators
        result = {
            "name": name,
            "website": website,
            "countries_served": countries,
            "has_email": bool(emails),
            "has_phone": bool(phones),
            "description": desc[:200] + "..." if len(desc) > 200 else desc,  # Truncate long descriptions
            "justification": just[:150] + "..." if len(just) > 150 else just,  # Truncate long justifications
            "contact_completeness": len([x for x in [emails, phones] if x]),
            "geographic_reach": len(countries) if countries else 0
        }
        
        return result
    
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        """Evaluate a vendor list prediction against gold standard."""
        cat = (gold.get("category") if isinstance(gold, dict) else getattr(gold, "category", None))
        region = (gold.get("country_or_region") if isinstance(gold, dict) else getattr(gold, "country_or_region", None))
        vendors = getattr(pred, "vendor_list", []) or []
        
        # Calculate individual scores if requested
        individual_scores = []
        if include_individual_scores and vendors:
            for vendor in vendors[:max_items]:
                if hasattr(vendor, '__dict__') or isinstance(vendor, dict):
                    # Convert dict to Vendor if needed
                    if isinstance(vendor, dict):
                        try:
                            vendor_obj = Vendor(**vendor)
                            individual_scores.append(comprehensive_vendor_score(vendor_obj))
                        except Exception:
                            continue
                    else:
                        individual_scores.append(comprehensive_vendor_score(vendor))
        
        slim = [_enhanced_slim(v) for v in vendors[:max_items]]
        
        # Initialize variables to avoid UnboundLocalError if judge fails
        j: Optional[Any] = None
        fb: str = ""

        try:
            j = judge(category=cat, country_or_region=region, vendor_list=slim)
            s = float(getattr(j, "score", 0.0))
            if s > 1.0 and s <= 100.0: 
                s = s / 100.0
            fb = (getattr(j, "feedback", "") or "").strip()
        except Exception as e:
            s = 0.0
            fb = f"Scored {s:.2f}."
            
        # Clamp score and ensure feedback is populated
        s = max(0.0, min(1.0, s))
        if not fb:
            fb = f"Scored {s:.2f}."
        
        result = dspy.Prediction(score=float(s), feedback=fb)
            
        return result
    
    return metric