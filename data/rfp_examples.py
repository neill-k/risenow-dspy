"""Example payloads for RFP agent training and testing."""

from __future__ import annotations

from typing import List, Dict, Any

DEFAULT_RFP_EXAMPLES: List[Dict[str, Any]] = [
    {
        "category": "Industrial IoT Platforms",
        "region": "North America",
        "pestle_analysis": {
            "economic": {"key_insights": ["Market growing at 17% CAGR", "Capital expenditure scrutiny"]},
            "technological": {"key_insights": ["Edge analytics demand", "Cybersecurity expectations"]},
        },
        "porters_analysis": {
            "competitive_rivalry": "High due to diversified incumbents",
            "bargaining_power_buyers": "Moderate with procurement-led deals",
        },
        "swot_analyses": [
            {
                "vendor_name": "Vendor A",
                "strengths": {"key_insights": ["Robust device management"]},
                "weaknesses": {"key_insights": ["Limited integration partners"]},
                "opportunities": {"key_insights": ["Expand managed services"]},
                "threats": {"key_insights": ["Supply chain disruption"]},
            }
        ],
        "vendor_list": [
            {"name": "Vendor A", "website": "https://vendor-a.example", "description": "End-to-end IoT platform"},
            {"name": "Vendor B", "website": "https://vendor-b.example", "description": "Edge analytics specialist"},
        ],
        "expected_question_count": 100,
    },
    {
        "category": "Enterprise Resource Planning",
        "region": "Europe",
        "pestle_analysis": {
            "legal": {"key_insights": ["GDPR compliance critical", "Cross-border data residency"]},
            "economic": {"key_insights": ["Shift to subscription pricing"]},
        },
        "porters_analysis": {
            "threat_of_substitutes": "Low due to high switching costs",
            "bargaining_power_suppliers": "Moderate given hyperscaler dependency",
        },
        "swot_analyses": [],
        "vendor_list": [
            {"name": "Vendor C", "website": "https://vendor-c.example", "description": "Cloud ERP leader"},
        ],
        "expected_question_count": 100,
    },
]
