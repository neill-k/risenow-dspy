"""Tests for the isolated RFP agent pipeline."""

from __future__ import annotations

from typing import List

from dspy import Prediction

from agents.rfp_agent import (
    create_rfp_agent,
    create_rfp_trainset,
)
from metrics.rfp_scoring import comprehensive_rfp_score
from models.rfp import InsightSourceSummary, RFPQuestion, RFPQuestionSet, RFPSection


class _StubInsightExtractor:
    def __call__(self, **_: object) -> Prediction:
        insights = [
            InsightSourceSummary(source="pestle", key_points=["Regulatory pressure"], confidence_notes="High"),
            InsightSourceSummary(source="porters", key_points=["High buyer power"], confidence_notes=None),
        ]
        return Prediction(insight_summaries=insights, synthesis_notes="Focus on compliance and differentiation")


class _StubReferenceGatherer:
    def __call__(self, **_: object) -> Prediction:
        references = [
            {
                "title": "City Infrastructure Upgrade RFP",
                "url": "https://rfp.example/city",
                "summary": "Large-scale infrastructure modernization reference",
                "extracted_requirements": ["Detail security controls", "Outline implementation roadmap"],
            }
        ]
        return Prediction(reference_documents=references)


class _StubQuestionGenerator:
    def __call__(self, expected_question_count: int, **_: object) -> Prediction:
        sections: List[RFPSection] = []
        questions_per_section = 5
        section_count = max(1, expected_question_count // questions_per_section)
        total_questions = 0

        for index in range(section_count):
            section_label = f"Section {index + 1}"
            section_questions: List[RFPQuestion] = []
            for q_index in range(questions_per_section):
                if total_questions >= expected_question_count:
                    break
                prompt = f"Question {total_questions + 1}: detail capability {q_index + 1}?"
                section_questions.append(
                    RFPQuestion(
                        section=section_label,
                        prompt=prompt,
                        rationale="Covers critical evaluation area",
                        referenced_insights=["pestle:Regulatory pressure"],
                    )
                )
                total_questions += 1
            sections.append(
                RFPSection(
                    name=section_label,
                    description="Auto-generated test section",
                    questions=section_questions,
                )
            )

        question_set = RFPQuestionSet(
            category="Industrial IoT Platforms",
            region="North America",
            sections=sections,
            total_questions=total_questions,
            reference_documents=[],
        )
        return Prediction(question_set=question_set)


def test_rfp_agent_generates_expected_question_count():
    agent = create_rfp_agent(use_tools=False)
    agent.insight_extractor = _StubInsightExtractor()
    agent.reference_gather = _StubReferenceGatherer()
    agent.question_generator = _StubQuestionGenerator()

    prediction = agent(
        category="Industrial IoT Platforms",
        region="North America",
        expected_question_count=100,
    )

    question_set = prediction.question_set
    assert isinstance(question_set, RFPQuestionSet)
    assert question_set.total_questions == 100
    assert len(question_set.sections) >= 5
    assert prediction.heuristics["component_scores"]["count"] == 1.0


def test_comprehensive_rfp_score_balances_components():
    sections = [
        RFPSection(
            name="Section 1",
            description=None,
            questions=[
                RFPQuestion(
                    section="Section 1",
                    prompt="Describe your security posture.",
                    rationale=None,
                    referenced_insights=["compliance"],
                )
                for _ in range(100)
            ],
        )
    ]
    question_set = RFPQuestionSet(
        category="Enterprise Resource Planning",
        region="Europe",
        sections=sections,
        total_questions=100,
        reference_documents=[],
    )

    score_breakdown = comprehensive_rfp_score(question_set)
    assert 0.0 <= score_breakdown["overall_score"] <= 1.0
    assert score_breakdown["component_scores"]["references"] == 1.0
    assert score_breakdown["component_scores"]["balance"] < 1.0  # single section penalty


def test_create_rfp_trainset_uses_default_examples():
    trainset = create_rfp_trainset()
    assert len(trainset) >= 2
    sample = trainset[0]
    assert set(sample.inputs) == {
        "category",
        "region",
        "pestle_analysis",
        "porters_analysis",
        "swot_analyses",
        "vendor_list",
        "expected_question_count",
    }
