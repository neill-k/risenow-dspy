"""Markdown writer utilities for pipeline documentation."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Dict


def ensure_output_dir(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_timestamp() -> str:
    """Get formatted timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_vendor_markdown(
    vendors: List[Any],
    filepath: str,
    category: str,
    region: str,
    metadata: Optional[Dict] = None
) -> None:
    """Write vendor discovery results to markdown."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Vendor Discovery Report\n\n")
        f.write(f"**Generated:** {format_timestamp()}\n")
        f.write(f"**Category:** {category}\n")
        f.write(f"**Region:** {region}\n")
        f.write(f"**Total Vendors Found:** {len(vendors)}\n\n")

        if metadata:
            f.write("## Analysis Metadata\n\n")
            for key, value in metadata.items():
                f.write(f"- **{key}:** {value}\n")
            f.write("\n")

        f.write("## Vendor List\n\n")
        f.write("| # | Company Name | Website | Contact | Regions Served |\n")
        f.write("|---|-------------|---------|---------|----------------|\n")

        for i, vendor in enumerate(vendors, 1):
            name = getattr(vendor, 'name', 'Unknown')
            website = getattr(vendor, 'website', 'N/A')

            # Get first email if available
            emails = getattr(vendor, 'contact_emails', [])
            email = emails[0].email if emails and hasattr(emails[0], 'email') else 'N/A'

            # Get countries served
            countries = getattr(vendor, 'countries_served', [])
            regions = ', '.join(countries[:3]) if countries else 'N/A'
            if len(countries) > 3:
                regions += f" (+{len(countries)-3} more)"

            f.write(f"| {i} | {name} | {website} | {email} | {regions} |\n")

        f.write("\n## Vendor Details\n\n")
        for i, vendor in enumerate(vendors, 1):
            f.write(f"### {i}. {getattr(vendor, 'name', 'Unknown')}\n\n")

            if hasattr(vendor, 'description') and vendor.description:
                f.write(f"**Description:** {vendor.description}\n\n")

            if hasattr(vendor, 'capabilities') and vendor.capabilities:
                f.write("**Key Capabilities:**\n")
                for cap in vendor.capabilities[:5]:
                    f.write(f"- {cap}\n")
                f.write("\n")

            if hasattr(vendor, 'certifications') and vendor.certifications:
                f.write(f"**Certifications:** {', '.join(vendor.certifications)}\n\n")

            f.write("---\n\n")


def write_pestle_markdown(
    pestle_analysis: Any,
    filepath: str,
    category: str,
    region: str
) -> None:
    """Write PESTLE analysis results to markdown."""
    if not pestle_analysis:
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# PESTLE Analysis Report\n\n")
        f.write(f"**Generated:** {format_timestamp()}\n")
        f.write(f"**Category:** {category}\n")
        f.write(f"**Region:** {region}\n\n")

        # Executive Summary
        if hasattr(pestle_analysis, 'executive_summary'):
            f.write("## Executive Summary\n\n")
            f.write(f"{pestle_analysis.executive_summary}\n\n")

        # Each PESTLE factor
        factors = ['political', 'economic', 'social', 'technological', 'legal', 'environmental']

        for factor in factors:
            factor_obj = getattr(pestle_analysis, factor, None)
            if factor_obj:
                f.write(f"## {factor.capitalize()} Factors\n\n")

                if hasattr(factor_obj, 'key_insights'):
                    f.write("### Key Insights\n\n")
                    for insight in factor_obj.key_insights:
                        f.write(f"- {insight}\n")
                    f.write("\n")

                if hasattr(factor_obj, 'impact_level'):
                    f.write(f"**Impact Level:** {factor_obj.impact_level}\n\n")

                if hasattr(factor_obj, 'time_horizon'):
                    f.write(f"**Time Horizon:** {factor_obj.time_horizon}\n\n")

        # Opportunities and Threats
        if hasattr(pestle_analysis, 'opportunities'):
            f.write("## Strategic Opportunities\n\n")
            for i, opp in enumerate(pestle_analysis.opportunities, 1):
                f.write(f"{i}. {opp}\n")
            f.write("\n")

        if hasattr(pestle_analysis, 'threats'):
            f.write("## Key Threats\n\n")
            for i, threat in enumerate(pestle_analysis.threats, 1):
                f.write(f"{i}. {threat}\n")
            f.write("\n")

        # Strategic Recommendations
        if hasattr(pestle_analysis, 'strategic_recommendations'):
            f.write("## Strategic Recommendations\n\n")
            for i, rec in enumerate(pestle_analysis.strategic_recommendations, 1):
                f.write(f"{i}. {rec}\n")
            f.write("\n")


def write_porters_markdown(
    porters_analysis: Any,
    filepath: str,
    category: str,
    region: str
) -> None:
    """Write Porter's Five Forces analysis to markdown."""
    if not porters_analysis:
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Porter's Five Forces Analysis\n\n")
        f.write(f"**Generated:** {format_timestamp()}\n")
        f.write(f"**Category:** {category}\n")
        f.write(f"**Region:** {region}\n\n")

        # Overall Assessment
        if hasattr(porters_analysis, 'overall_attractiveness'):
            f.write("## Market Attractiveness\n\n")
            f.write(f"**Overall Rating:** {porters_analysis.overall_attractiveness}\n\n")

        # Five Forces
        forces = [
            ('competitive_rivalry', 'Competitive Rivalry'),
            ('supplier_power', 'Bargaining Power of Suppliers'),
            ('buyer_power', 'Bargaining Power of Buyers'),
            ('threat_of_substitution', 'Threat of Substitution'),
            ('threat_of_new_entry', 'Threat of New Entry')
        ]

        f.write("## Five Forces Analysis\n\n")

        for force_attr, force_name in forces:
            force = getattr(porters_analysis, force_attr, None)
            if force:
                f.write(f"### {force_name}\n\n")

                if hasattr(force, 'intensity'):
                    f.write(f"**Intensity:** {force.intensity}\n\n")

                if hasattr(force, 'key_factors'):
                    f.write("**Key Factors:**\n")
                    for factor in force.key_factors:
                        f.write(f"- {factor}\n")
                    f.write("\n")

                if hasattr(force, 'implications'):
                    f.write("**Strategic Implications:**\n")
                    for impl in force.implications:
                        f.write(f"- {impl}\n")
                    f.write("\n")

        # Strategic Recommendations
        if hasattr(porters_analysis, 'strategic_recommendations'):
            f.write("## Strategic Recommendations\n\n")
            for i, rec in enumerate(porters_analysis.strategic_recommendations, 1):
                f.write(f"{i}. {rec}\n")
            f.write("\n")

        # Key Success Factors
        if hasattr(porters_analysis, 'key_success_factors'):
            f.write("## Key Success Factors\n\n")
            for i, factor in enumerate(porters_analysis.key_success_factors, 1):
                f.write(f"{i}. {factor}\n")
            f.write("\n")


def write_swot_markdown(
    swot_analyses: List[Any],
    filepath: str,
    category: str,
    region: str
) -> None:
    """Write SWOT analyses to markdown."""
    if not swot_analyses:
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# SWOT Analysis Report\n\n")
        f.write(f"**Generated:** {format_timestamp()}\n")
        f.write(f"**Category:** {category}\n")
        f.write(f"**Region:** {region}\n")
        f.write(f"**Vendors Analyzed:** {len(swot_analyses)}\n\n")

        f.write("## Summary Table\n\n")
        f.write("| Vendor | Strengths | Weaknesses | Opportunities | Threats |\n")
        f.write("|--------|-----------|------------|---------------|----------|\n")

        for swot in swot_analyses:
            if not swot:
                continue

            vendor_name = getattr(swot, 'vendor_name', 'Unknown')

            strengths_count = len(swot.strengths.competitive_advantages) if hasattr(swot, 'strengths') and hasattr(swot.strengths, 'competitive_advantages') else 0
            weaknesses_count = len(swot.weaknesses.limitations) if hasattr(swot, 'weaknesses') and hasattr(swot.weaknesses, 'limitations') else 0
            opportunities_count = len(swot.opportunities.market_opportunities) if hasattr(swot, 'opportunities') and hasattr(swot.opportunities, 'market_opportunities') else 0
            threats_count = len(swot.threats.competitive_threats) if hasattr(swot, 'threats') and hasattr(swot.threats, 'competitive_threats') else 0

            f.write(f"| {vendor_name} | {strengths_count} | {weaknesses_count} | {opportunities_count} | {threats_count} |\n")

        f.write("\n## Detailed Analysis\n\n")

        for i, swot in enumerate(swot_analyses, 1):
            if not swot:
                continue

            vendor_name = getattr(swot, 'vendor_name', f'Vendor {i}')
            f.write(f"### {i}. {vendor_name}\n\n")

            # Strengths
            if hasattr(swot, 'strengths') and hasattr(swot.strengths, 'competitive_advantages'):
                f.write("#### Strengths\n\n")
                for strength in swot.strengths.competitive_advantages:
                    f.write(f"- {strength}\n")
                f.write("\n")

            # Weaknesses
            if hasattr(swot, 'weaknesses') and hasattr(swot.weaknesses, 'limitations'):
                f.write("#### Weaknesses\n\n")
                for weakness in swot.weaknesses.limitations:
                    f.write(f"- {weakness}\n")
                f.write("\n")

            # Opportunities
            if hasattr(swot, 'opportunities') and hasattr(swot.opportunities, 'market_opportunities'):
                f.write("#### Opportunities\n\n")
                for opp in swot.opportunities.market_opportunities:
                    f.write(f"- {opp}\n")
                f.write("\n")

            # Threats
            if hasattr(swot, 'threats') and hasattr(swot.threats, 'competitive_threats'):
                f.write("#### Threats\n\n")
                for threat in swot.threats.competitive_threats:
                    f.write(f"- {threat}\n")
                f.write("\n")

            # Strategic Recommendations
            if hasattr(swot, 'strategic_recommendations'):
                f.write("#### Strategic Recommendations\n\n")
                for j, rec in enumerate(swot.strategic_recommendations, 1):
                    f.write(f"{j}. {rec}\n")
                f.write("\n")

            f.write("---\n\n")


def write_rfp_markdown(
    rfp_question_set: Any,
    filepath: str,
    category: str,
    region: str
) -> None:
    """Write RFP questions to markdown."""
    if not rfp_question_set:
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Request for Proposal (RFP)\n\n")
        f.write(f"**Generated:** {format_timestamp()}\n")
        f.write(f"**Category:** {category}\n")
        f.write(f"**Region:** {region}\n")
        f.write(f"**Total Questions:** {rfp_question_set.total_questions}\n")
        f.write(f"**Sections:** {len(rfp_question_set.sections)}\n\n")

        # Table of Contents
        f.write("## Table of Contents\n\n")
        for i, section in enumerate(rfp_question_set.sections, 1):
            f.write(f"{i}. [{section.title}](#{section.title.lower().replace(' ', '-')})\n")
        f.write("\n")

        # Questions by Section
        for section in rfp_question_set.sections:
            f.write(f"## {section.title}\n\n")

            if hasattr(section, 'description') and section.description:
                f.write(f"*{section.description}*\n\n")

            for i, question in enumerate(section.questions, 1):
                f.write(f"### {section.title} - Question {i}\n\n")
                f.write(f"**{question.question}**\n\n")

                if question.context:
                    f.write(f"*Context: {question.context}*\n\n")

                if question.expected_response_type:
                    f.write(f"**Expected Response Type:** {question.expected_response_type}\n\n")

                if hasattr(question, 'evaluation_criteria') and question.evaluation_criteria:
                    f.write("**Evaluation Criteria:**\n")
                    for criterion in question.evaluation_criteria:
                        f.write(f"- {criterion}\n")
                    f.write("\n")

            f.write("---\n\n")


def write_complete_report(
    result: Any,
    output_dir: str,
    include_toc: bool = True,
    include_executive_summary: bool = True
) -> str:
    """Write comprehensive analysis report combining all results."""
    ensure_output_dir(output_dir)
    filepath = os.path.join(output_dir, "COMPLETE_ANALYSIS_REPORT.md")

    category = getattr(result, 'category', 'Unknown Category')
    region = getattr(result, 'region', 'Unknown Region')

    with open(filepath, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# Complete Analysis Report: {category}\n\n")
        f.write(f"**Generated:** {format_timestamp()}\n")
        f.write(f"**Category:** {category}\n")
        f.write(f"**Region:** {region}\n\n")

        # Executive Summary
        if include_executive_summary:
            f.write("## Executive Summary\n\n")

            vendor_count = len(result.vendor_list) if hasattr(result, 'vendor_list') else 0
            swot_count = len(result.swot_analyses) if hasattr(result, 'swot_analyses') else 0
            rfp_questions = result.rfp_question_set.total_questions if hasattr(result, 'rfp_question_set') and result.rfp_question_set else 0

            f.write(f"This comprehensive analysis covers the {category} market in {region}, ")
            f.write(f"identifying {vendor_count} key vendors, analyzing {swot_count} vendors in detail, ")
            f.write(f"and generating {rfp_questions} targeted RFP questions.\n\n")

            f.write("### Key Findings\n\n")

            # PESTLE Summary
            if hasattr(result, 'pestle_analysis') and result.pestle_analysis:
                if hasattr(result.pestle_analysis, 'executive_summary'):
                    f.write(f"**Market Environment:** {result.pestle_analysis.executive_summary[:200]}...\n\n")

            # Porter's Summary
            if hasattr(result, 'porters_analysis') and result.porters_analysis:
                if hasattr(result.porters_analysis, 'overall_attractiveness'):
                    f.write(f"**Market Attractiveness:** {result.porters_analysis.overall_attractiveness}\n\n")

            f.write("### Analysis Components\n\n")
            f.write("| Component | Status | Key Metrics |\n")
            f.write("|-----------|--------|-------------|\n")
            f.write(f"| Vendor Discovery | ✓ | {vendor_count} vendors identified |\n")
            f.write(f"| PESTLE Analysis | {'✓' if hasattr(result, 'pestle_analysis') and result.pestle_analysis else '✗'} | 6 factors analyzed |\n")
            f.write(f"| Porter's Five Forces | {'✓' if hasattr(result, 'porters_analysis') and result.porters_analysis else '✗'} | 5 forces evaluated |\n")
            f.write(f"| SWOT Analysis | {'✓' if swot_count > 0 else '✗'} | {swot_count} vendors analyzed |\n")
            f.write(f"| RFP Generation | {'✓' if rfp_questions > 0 else '✗'} | {rfp_questions} questions generated |\n\n")

        # Table of Contents
        if include_toc:
            f.write("## Table of Contents\n\n")
            f.write("1. [Vendor Discovery](#vendor-discovery)\n")
            f.write("2. [PESTLE Analysis](#pestle-analysis)\n")
            f.write("3. [Porter's Five Forces](#porters-five-forces)\n")
            f.write("4. [SWOT Analyses](#swot-analyses)\n")
            f.write("5. [RFP Questions](#rfp-questions)\n")
            f.write("6. [Conclusions and Recommendations](#conclusions-and-recommendations)\n\n")

        # Section 1: Vendors
        f.write("## Vendor Discovery\n\n")
        if hasattr(result, 'vendor_list') and result.vendor_list:
            f.write(f"Identified {len(result.vendor_list)} vendors in the {category} market.\n\n")
            f.write("### Top Vendors\n\n")
            f.write("| # | Company | Website | Primary Region |\n")
            f.write("|---|---------|---------|----------------|\n")
            for i, vendor in enumerate(result.vendor_list[:10], 1):
                name = getattr(vendor, 'name', 'Unknown')
                website = getattr(vendor, 'website', 'N/A')
                countries = getattr(vendor, 'countries_served', [])
                primary_region = countries[0] if countries else 'Global'
                f.write(f"| {i} | {name} | {website} | {primary_region} |\n")

            if len(result.vendor_list) > 10:
                f.write(f"\n*...and {len(result.vendor_list) - 10} more vendors*\n")
            f.write("\n")
        else:
            f.write("*No vendor data available*\n\n")

        # Section 2: PESTLE
        f.write("## PESTLE Analysis\n\n")
        if hasattr(result, 'pestle_analysis') and result.pestle_analysis:
            pestle = result.pestle_analysis

            if hasattr(pestle, 'executive_summary'):
                f.write(f"{pestle.executive_summary}\n\n")

            # Key factors summary
            factors = ['political', 'economic', 'social', 'technological', 'legal', 'environmental']
            for factor in factors:
                factor_obj = getattr(pestle, factor, None)
                if factor_obj and hasattr(factor_obj, 'key_insights'):
                    f.write(f"### {factor.capitalize()}\n")
                    for insight in factor_obj.key_insights[:3]:
                        f.write(f"- {insight}\n")
                    f.write("\n")
        else:
            f.write("*PESTLE analysis not available*\n\n")

        # Section 3: Porter's
        f.write("## Porter's Five Forces\n\n")
        if hasattr(result, 'porters_analysis') and result.porters_analysis:
            porters = result.porters_analysis

            if hasattr(porters, 'overall_attractiveness'):
                f.write(f"**Market Attractiveness:** {porters.overall_attractiveness}\n\n")

            forces_summary = []
            for force_name in ['competitive_rivalry', 'supplier_power', 'buyer_power']:
                force = getattr(porters, force_name, None)
                if force and hasattr(force, 'intensity'):
                    forces_summary.append(f"- **{force_name.replace('_', ' ').title()}:** {force.intensity}")

            if forces_summary:
                f.write("### Force Intensity Summary\n\n")
                for summary in forces_summary:
                    f.write(f"{summary}\n")
                f.write("\n")
        else:
            f.write("*Porter's analysis not available*\n\n")

        # Section 4: SWOT
        f.write("## SWOT Analyses\n\n")
        if hasattr(result, 'swot_analyses') and result.swot_analyses:
            f.write(f"Detailed SWOT analysis completed for {len(result.swot_analyses)} vendors.\n\n")

            for i, swot in enumerate(result.swot_analyses[:3], 1):
                if not swot:
                    continue
                vendor_name = getattr(swot, 'vendor_name', f'Vendor {i}')
                f.write(f"### {vendor_name}\n\n")

                # Count items in each category
                s_count = len(swot.strengths.competitive_advantages) if hasattr(swot, 'strengths') and hasattr(swot.strengths, 'competitive_advantages') else 0
                w_count = len(swot.weaknesses.limitations) if hasattr(swot, 'weaknesses') and hasattr(swot.weaknesses, 'limitations') else 0
                o_count = len(swot.opportunities.market_opportunities) if hasattr(swot, 'opportunities') and hasattr(swot.opportunities, 'market_opportunities') else 0
                t_count = len(swot.threats.competitive_threats) if hasattr(swot, 'threats') and hasattr(swot.threats, 'competitive_threats') else 0

                f.write(f"- **Strengths:** {s_count} identified\n")
                f.write(f"- **Weaknesses:** {w_count} identified\n")
                f.write(f"- **Opportunities:** {o_count} identified\n")
                f.write(f"- **Threats:** {t_count} identified\n\n")
        else:
            f.write("*SWOT analyses not available*\n\n")

        # Section 5: RFP
        f.write("## RFP Questions\n\n")
        if hasattr(result, 'rfp_question_set') and result.rfp_question_set:
            rfp = result.rfp_question_set
            f.write(f"Generated {rfp.total_questions} questions across {len(rfp.sections)} sections.\n\n")

            f.write("### Section Overview\n\n")
            f.write("| Section | Questions | Coverage % |\n")
            f.write("|---------|-----------|------------|\n")

            for section in rfp.sections:
                coverage = (len(section.questions) / rfp.total_questions * 100) if rfp.total_questions > 0 else 0
                f.write(f"| {section.title} | {len(section.questions)} | {coverage:.1f}% |\n")
            f.write("\n")
        else:
            f.write("*RFP questions not generated*\n\n")

        # Section 6: Conclusions
        f.write("## Conclusions and Recommendations\n\n")
        f.write("### Key Takeaways\n\n")

        # Compile recommendations from all analyses
        all_recommendations = []

        if hasattr(result, 'pestle_analysis') and result.pestle_analysis:
            if hasattr(result.pestle_analysis, 'strategic_recommendations'):
                all_recommendations.extend(result.pestle_analysis.strategic_recommendations[:2])

        if hasattr(result, 'porters_analysis') and result.porters_analysis:
            if hasattr(result.porters_analysis, 'strategic_recommendations'):
                all_recommendations.extend(result.porters_analysis.strategic_recommendations[:2])

        if all_recommendations:
            for i, rec in enumerate(all_recommendations[:5], 1):
                f.write(f"{i}. {rec}\n")
        else:
            f.write("*Detailed recommendations available in individual analysis sections*\n")

        f.write("\n---\n\n")
        f.write(f"*Report generated on {format_timestamp()}*\n")

    return filepath


def generate_all_markdown_reports(
    result: Any,
    output_dir: str,
    save_intermediate: bool = True
) -> Dict[str, str]:
    """Generate all markdown reports from pipeline results."""
    ensure_output_dir(output_dir)
    generated_files = {}

    category = getattr(result, 'category', 'Unknown Category')
    region = getattr(result, 'region', 'Unknown Region')

    if save_intermediate:
        # 1. Vendor Discovery
        if hasattr(result, 'vendor_list') and result.vendor_list:
            vendor_file = os.path.join(output_dir, "01_vendor_discovery.md")
            write_vendor_markdown(result.vendor_list, vendor_file, category, region)
            generated_files['vendors'] = vendor_file

        # 2. PESTLE Analysis
        if hasattr(result, 'pestle_analysis') and result.pestle_analysis:
            pestle_file = os.path.join(output_dir, "02_pestle_analysis.md")
            write_pestle_markdown(result.pestle_analysis, pestle_file, category, region)
            generated_files['pestle'] = pestle_file

        # 3. Porter's Five Forces
        if hasattr(result, 'porters_analysis') and result.porters_analysis:
            porters_file = os.path.join(output_dir, "03_porters_analysis.md")
            write_porters_markdown(result.porters_analysis, porters_file, category, region)
            generated_files['porters'] = porters_file

        # 4. SWOT Analyses
        if hasattr(result, 'swot_analyses') and result.swot_analyses:
            swot_file = os.path.join(output_dir, "04_swot_analyses.md")
            write_swot_markdown(result.swot_analyses, swot_file, category, region)
            generated_files['swot'] = swot_file

        # 5. RFP Questions
        if hasattr(result, 'rfp_question_set') and result.rfp_question_set:
            rfp_file = os.path.join(output_dir, "05_rfp_questions.md")
            write_rfp_markdown(result.rfp_question_set, rfp_file, category, region)
            generated_files['rfp'] = rfp_file

    # 6. Complete Report
    complete_file = write_complete_report(result, output_dir)
    generated_files['complete'] = complete_file

    return generated_files