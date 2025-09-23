"""RFP generation agent using DSPy best practices."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional, Tuple

import dspy
from dspy import Example, Prediction

from models.rfp import (
    InsightSourceSummary,
    ReferenceDocument,
    RFPQuestionSet,
    RFPInsightExtractionSignature,
    RFPReferenceGatherSignature,
    RFPQuestionGeneratorSignature,
)
from metrics.rfp_scoring import comprehensive_rfp_score, make_rfp_llm_judge_metric
from tools.web_tools import create_dspy_tools

logger = logging.getLogger(__name__)

MetricFunction = Callable[[Any, Any, Any | None, str | None, Any | None], Prediction]

__all__ = [
    "create_rfp_agent",
    "create_rfp_metric",
    "create_rfp_trainset",
    "optimize_rfp_agent",
    "generate_rfp_question_set",
]


class RFPGenerationPipeline(dspy.Module):
    """DSPy module orchestrating insight extraction, reference gathering, and question generation."""

    def __init__(
        self,
        use_tools: bool = True,
        max_iters: int = 40,
        max_reference_documents: int = 10,
    ) -> None:
        super().__init__()
        self.use_tools = use_tools
        self.max_reference_documents = max_reference_documents

        self.insight_extractor = dspy.Predict(RFPInsightExtractionSignature)
        self.reference_gather = dspy.Predict(RFPReferenceGatherSignature)

        if use_tools:
            tools = create_dspy_tools()
            self.question_generator = dspy.ReAct(
                RFPQuestionGeneratorSignature,
                tools=list(tools),
                max_iters=max_iters,
            )
            logger.info("Created RFP ReAct generator with %s tools", len(tools))
        else:
            self.question_generator = dspy.ChainOfThought(RFPQuestionGeneratorSignature)
            logger.info("Created RFP ChainOfThought generator")

    def forward(
        self,
        category: str,
        region: Optional[str] = None,
        pestle_analysis: Optional[dict] = None,
        porters_analysis: Optional[dict] = None,
        swot_analyses: Optional[List[dict]] = None,
        vendor_list: Optional[List[dict]] = None,
        expected_question_count: int = 100,
        max_reference_documents: Optional[int] = None,
    ) -> Prediction:
        logger.info(
            "Running RFP pipeline for category=%s region=%s expected_questions=%s",
            category,
            region or "Global",
            expected_question_count,
        )

        insight_prediction = self.insight_extractor(
            category=category,
            region=region,
            pestle_analysis=pestle_analysis,
            porters_analysis=porters_analysis,
            swot_analyses=swot_analyses,
            vendor_list=vendor_list,
        )
        insight_summaries = list(getattr(insight_prediction, "insight_summaries", []) or [])
        logger.debug("Extracted %s insight bundles", len(insight_summaries))

        vendor_names = []
        if vendor_list:
            vendor_names = [
                (vendor.get("name") if isinstance(vendor, dict) else None)
                for vendor in vendor_list
            ]
            vendor_names = [name for name in vendor_names if name]

        reference_limit = max_reference_documents or self.max_reference_documents
        reference_prediction = self.reference_gather(
            category=category,
            region=region,
            vendor_names=vendor_names or None,
            max_documents=reference_limit,
        )
        references = list(getattr(reference_prediction, "reference_documents", []) or [])
        logger.debug("Summarized %s reference documents", len(references))

        insights_payload = [
            summary.dict() if isinstance(summary, InsightSourceSummary) else summary
            for summary in insight_summaries
        ]
        references_payload = [
            reference.dict() if isinstance(reference, ReferenceDocument) else reference
            for reference in references
        ]

        questions_prediction = self.question_generator(
            category=category,
            region=region,
            insight_summaries=insights_payload,
            reference_documents=references_payload,
            expected_question_count=expected_question_count,
        )

        question_set = getattr(questions_prediction, "question_set", None)
        if question_set is None:
            logger.error("RFP generation failed to return question_set")
            raise ValueError("RFP agent did not produce a question set")

        if isinstance(question_set, dict):
            question_set = RFPQuestionSet(**question_set)

        heuristics = comprehensive_rfp_score(question_set, expected_count=expected_question_count)
        logger.info(
            "Generated RFP question set with %s questions across %s sections",
            question_set.total_questions,
            len(question_set.sections),
        )

        return Prediction(
            question_set=question_set,
            insights=insight_summaries,
            references=references,
            heuristics=heuristics,
        )


def create_rfp_agent(
    use_tools: bool = True,
    max_iters: int = 40,
    max_reference_documents: int = 10,
) -> dspy.Module:
    """Create the RFP generation pipeline module."""
    return RFPGenerationPipeline(
        use_tools=use_tools,
        max_iters=max_iters,
        max_reference_documents=max_reference_documents,
    )


def create_rfp_metric(include_details: bool = True) -> Tuple[MetricFunction, Callable[[], int]]:
    """Build the LLM-based evaluation metric for RFP question sets."""
    llm_metric = make_rfp_llm_judge_metric(include_details=include_details)
    counter: dict[str, int] = {"count": 0}

    def metric(
        gold: Any,
        pred: Any,
        trace: Any | None = None,
        pred_name: str | None = None,
        pred_trace: Any | None = None,
    ) -> Prediction:
        counter["count"] += 1
        result = llm_metric(gold, pred, trace, pred_name, pred_trace)
        logger.info("RFP metric call %s -> score %.3f", counter["count"], float(getattr(result, "score", 0.0)))
        return result

    def get_calls() -> int:
        return counter["count"]

    return metric, get_calls


def create_rfp_trainset(examples: Optional[List[dict]] = None) -> List[Example]:
    """Create RFP trainset examples for optimization."""
    from data.rfp_examples import DEFAULT_RFP_EXAMPLES  # Local import to avoid circular dependency

    payloads = examples or DEFAULT_RFP_EXAMPLES
    trainset: List[Example] = []
    for sample in payloads:
        example = dspy.Example(
            category=sample.get("category"),
            region=sample.get("region"),
            pestle_analysis=sample.get("pestle_analysis"),
            porters_analysis=sample.get("porters_analysis"),
            swot_analyses=sample.get("swot_analyses"),
            vendor_list=sample.get("vendor_list"),
            expected_question_count=sample.get("expected_question_count", 100),
        ).with_inputs(
            "category",
            "region",
            "pestle_analysis",
            "porters_analysis",
            "swot_analyses",
            "vendor_list",
            "expected_question_count",
        )
        trainset.append(example)

    logger.info("Created RFP trainset with %s examples", len(trainset))
    return trainset


def optimize_rfp_agent(
    agent: dspy.Module,
    metric: MetricFunction,
    trainset: List[Example],
    optimizer_class: type = dspy.GEPA,
    **optimizer_kwargs,
) -> dspy.Module:
    """Optimize the RFP agent via the configured DSPy optimizer."""
    default_kwargs = {
        "max_metric_calls": 60,
        "num_threads": 3,
    }
    default_kwargs.update(optimizer_kwargs)

    optimizer = optimizer_class(
        metric=metric,
        **default_kwargs,
    )

    logger.info(
        "Starting %s optimization for RFP agent (trainset=%s)",
        optimizer_class.__name__,
        len(trainset),
    )

    optimized_agent = optimizer.compile(
        student=agent,
        trainset=trainset,
    )
    logger.info("RFP agent optimization completed")
    return optimized_agent


def generate_rfp_question_set(
    category: str,
    region: Optional[str] = None,
    pestle_analysis: Optional[dict] = None,
    porters_analysis: Optional[dict] = None,
    swot_analyses: Optional[List[dict]] = None,
    vendor_list: Optional[List[dict]] = None,
    use_tools: bool = True,
    expected_question_count: int = 100,
) -> RFPQuestionSet:
    """Convenience helper to run the RFP agent end-to-end in isolation."""
    agent = create_rfp_agent(use_tools=use_tools)
    prediction = agent(
        category=category,
        region=region,
        pestle_analysis=pestle_analysis,
        porters_analysis=porters_analysis,
        swot_analyses=swot_analyses,
        vendor_list=vendor_list,
        expected_question_count=expected_question_count,
    )

    question_set = getattr(prediction, "question_set", None)
    if question_set is None:
        raise ValueError("RFP generation failed; question_set missing from prediction")

    if isinstance(question_set, dict):
        return RFPQuestionSet(**question_set)
    return question_set
