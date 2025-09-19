"""Main script for vendor discovery optimization using GEPA with Tavily tools."""

import logging
logging.basicConfig(level=logging.INFO)
from typing import Any, Optional
import dspy
from dspy import GEPA, Prediction

from config.environment import (
    validate_environment,
    get_primary_lm_config,
    get_reflection_lm_config,
    get_gepa_settings,
    get_vendor_program_path,
    should_optimize_vendor,
)
from models.pestle import PESTLEAnalysis
from metrics.pestle_scoring import make_pestle_llm_judge_metric
from agents.pestle_agent import (
    create_pestle_agent,
    create_pestle_trainset,
    optimize_pestle_agent
)
from agents.vendor_agent import (
    create_vendor_agent,
    create_vendor_metric,
    create_vendor_trainset,
    optimize_vendor_agent,
    load_vendor_agent,
    save_vendor_agent
)
from config.observability import (
    observability_span,
    set_span_attributes,
    setup_langfuse,
    generate_session_id,
)

logger = logging.getLogger(__name__)



def run(
    category: str = "General Industrial Supplies",
    n: int = 15,
    country_or_region: str | None = "United States",
    reuse_cached_program: bool = True,
    program_path: str | None = None,
    optimize_if_missing: bool | None = None,
    session_id: str | None = None,
) -> dspy.Prediction:
    """
    Run vendor discovery with GEPA optimization.

    Parameters
    ----------
    category : str
        Category of vendors to find
    n : int
        Number of vendors to return
    country_or_region : str | None
        Optional region filter
    reuse_cached_program : bool
        Whether to load a cached optimized program when available
    program_path : str | None
        Optional override for the saved program path
    optimize_if_missing : bool | None
        Whether to run optimization when the cached program is missing. If ``None``,
        the ``VENDOR_OPTIMIZE_ON_MISS`` environment variable controls the behaviour.
    session_id : str | None
        Optional session ID for grouping traces

    Returns
    -------
    dspy.Prediction
        Result containing vendor_list
    """
    validate_environment()
    setup_langfuse()

    # Generate session ID if not provided
    if session_id is None:
        session_id = generate_session_id()

    vendor_program_path = program_path or get_vendor_program_path()
    if optimize_if_missing is None:
        optimize_if_missing = should_optimize_vendor()

    run_span_attrs = {
        "vendor.request.category": category,
        "vendor.request.count": n,
        "vendor.request.country_or_region": country_or_region or "Global",
        "vendor.program.path": vendor_program_path,
        "vendor.program.optimize_requested": optimize_if_missing,
        "session.id": session_id,
    }

    with observability_span("vendor.run", run_span_attrs, session_id=session_id) as run_span:
        primary_config = get_primary_lm_config()
        primary_lm = dspy.LM(**primary_config, num_retries=5)
        dspy.configure(lm=primary_lm)

        reflection_config = get_reflection_lm_config()
        reflection_lm = dspy.LM(**reflection_config, num_retries=5)

        metric_call_count: Optional[int] = None
        program_source = "optimized"
        program_loaded = False

        vendor_program: Optional[dspy.Module] = None
        if reuse_cached_program:
            vendor_program = load_vendor_agent(
                path=vendor_program_path,
                use_tools=True,
                max_iters=50,
            )
            if vendor_program is not None:
                program_source = "cache"
                program_loaded = True

        if vendor_program is None:
            vendor_agent = create_vendor_agent(use_tools=True, max_iters=50)

            if optimize_if_missing:
                vendor_metric, get_metric_calls = create_vendor_metric(
                    max_items=15,
                    include_individual_scores=True,
                )
                trainset = create_vendor_trainset()
                trainset_size = len(trainset)

                gepa_settings = get_gepa_settings()
                vendor_optimizer_class = GEPA
                effective_max_calls = max(trainset_size, gepa_settings["max_metric_calls"])

                try:
                    with observability_span(
                        "vendor.gepa_optimize",
                        {
                            "gepa.max_metric_calls": effective_max_calls,
                            "gepa.num_threads": gepa_settings["num_threads"],
                            "gepa.trainset.size": trainset_size,
                            "gepa.optimizer": vendor_optimizer_class.__name__,
                        },
                        session_id=session_id,
                    ) as gepa_span:
                        vendor_program = optimize_vendor_agent(
                            agent=vendor_agent,
                            metric=vendor_metric,
                            trainset=trainset,
                            optimizer_class=vendor_optimizer_class,
                            reflection_lm=reflection_lm,
                            max_metric_calls=effective_max_calls,
                            num_threads=gepa_settings["num_threads"],
                        )

                        metric_call_count = get_metric_calls()
                        set_span_attributes(
                            gepa_span,
                            {
                                "gepa.metric_calls.actual": metric_call_count,
                            },
                        )

                    save_vendor_agent(vendor_program, vendor_program_path)
                    program_source = "optimized"
                    program_loaded = False
                except KeyboardInterrupt:
                    logger.warning("Vendor optimization interrupted; using base agent without cache.")
                    vendor_program = vendor_agent
                    program_source = "base"
                    program_loaded = False
                except Exception as exc:
                    logger.exception("Vendor optimization failed: %s", exc)
                    vendor_program = vendor_agent
                    program_source = "base"
                    program_loaded = False
            else:
                logger.info(
                    "Vendor optimization disabled via configuration; using base agent without cache."
                )
                vendor_program = vendor_agent
                program_source = "base"
                program_loaded = False

        if vendor_program is None:
            raise RuntimeError("Vendor program could not be instantiated.")

        result = vendor_program(
            category=category,
            n=n,
            country_or_region=country_or_region,
        )

        vendor_list = list(getattr(result, "vendor_list", []) or [])
        attrs = _summarize_vendor_results(vendor_list, metric_call_count)
        attrs.update(
            {
                "vendor.program.source": program_source,
                "vendor.program.loaded": program_loaded,
                "vendor.program.path": vendor_program_path,
                "vendor.program.optimize_requested": optimize_if_missing,
            }
        )
        set_span_attributes(run_span, attrs)

    return result




def run_with_pestle(
    category: str = "General Industrial Supplies",
    n: int = 15,
    country_or_region: str | None = "United States",
    include_pestle: bool = True,
    reuse_cached_program: bool = True,
    program_path: str | None = None,
    optimize_if_missing: bool | None = None,
) -> dspy.Prediction:
    """
    Run vendor discovery with optional PESTLE analysis.

    Parameters
    ----------
    category : str
        Category of vendors to find
    n : int
        Number of vendors to return
    country_or_region : str | None
        Optional region filter
    include_pestle : bool
        Whether to include PESTLE analysis
    reuse_cached_program : bool
        Whether to reuse a cached vendor program when available
    program_path : str | None
        Optional override for the saved vendor program path
    optimize_if_missing : bool | None
        Forwarded to `run()` to control whether optimization should execute when the cache is missing.

    Returns
    -------
    dspy.Prediction
        Result containing vendor_list and optionally pestle_analysis
    """
    logger.info("Starting vendor discovery...")

    vendor_program_path = program_path or get_vendor_program_path()
    optimize_flag = optimize_if_missing if optimize_if_missing is not None else should_optimize_vendor()

    span_attrs = {
        "vendor.request.category": category,
        "vendor.request.count": n,
        "vendor.request.country_or_region": country_or_region or "Global",
        "vendor.program.path": vendor_program_path,
        "vendor.program.optimize_requested": optimize_flag,
        "pestle.include": include_pestle,
    }

    pestle_analysis = None

    with observability_span("vendor.run_with_pestle", span_attrs) as combined_span:
        vendor_result = run(
            category=category,
            n=n,
            country_or_region=country_or_region,
            reuse_cached_program=reuse_cached_program,
            program_path=vendor_program_path,
            optimize_if_missing=optimize_flag,
        )
        vendor_list = list(getattr(vendor_result, "vendor_list", []) or [])
        vendor_attrs = _summarize_vendor_results(vendor_list)
        vendor_attrs["vendor.program.optimize_requested"] = optimize_flag
        set_span_attributes(combined_span, vendor_attrs)

        if include_pestle:
            logger.info("Starting PESTLE analysis...")

            reflection_config = get_reflection_lm_config()
            reflection_lm = dspy.LM(**reflection_config, num_retries=5)

            pestle_agent = create_pestle_agent(use_tools=True, max_iters=30)
            pestle_metric = make_pestle_llm_judge_metric(include_details=True)
            pestle_trainset = create_pestle_trainset()
            trainset_size = len(pestle_trainset)

            gepa_settings = get_gepa_settings()
            pestle_optimizer_class = GEPA

            def gepa_pestle_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
                raw = pestle_metric(gold, pred, trace, pred_name, pred_trace)
                if isinstance(raw, Prediction):
                    score = float(getattr(raw, "score", 0.0) or 0.0)
                    feedback = (getattr(raw, "feedback", "") or "").strip()
                else:
                    score = float(raw.get("score", 0.0) or 0.0)
                    feedback = str(raw.get("feedback", "") or "").strip()
                score = max(0.0, min(1.0, score))
                feedback = feedback or f"Scored {score:.2f}."
                return Prediction(score=score, feedback=feedback)

            optimization_attrs = {
                "pestle.trainset.size": trainset_size,
                "gepa.max_metric_calls": max(trainset_size, gepa_settings["max_metric_calls"]),
                "gepa.num_threads": gepa_settings["num_threads"],
                "gepa.optimizer": pestle_optimizer_class.__name__,
            }

            with observability_span("pestle.gepa_optimize", optimization_attrs):
                optimized_pestle = optimize_pestle_agent(
                    agent=pestle_agent,
                    metric=gepa_pestle_metric,
                    trainset=pestle_trainset,
                    optimizer_class=pestle_optimizer_class,
                    reflection_lm=reflection_lm,
                    max_metric_calls=max(trainset_size, gepa_settings["max_metric_calls"]),
                    num_threads=gepa_settings["num_threads"],
                )

            with observability_span(
                "pestle.generate",
                {
                    "pestle.request.category": category,
                    "pestle.request.region": country_or_region or "Global",
                },
            ) as pestle_span:
                pestle_result = optimized_pestle(
                    category=category,
                    region=country_or_region,
                    focus_areas=None
                )

                if hasattr(pestle_result, "pestle_analysis"):
                    pestle_analysis = pestle_result.pestle_analysis
                    set_span_attributes(pestle_span, _summarize_pestle_analysis(pestle_analysis))
                else:
                    set_span_attributes(pestle_span, {"pestle.has_analysis": False})

    set_span_attributes(combined_span, _summarize_pestle_analysis(pestle_analysis))

    combined_result = dspy.Prediction(
        vendor_list=vendor_result.vendor_list,
        pestle_analysis=pestle_analysis
    )

    return combined_result




def _get_value(obj: Any, attr: str):
    if isinstance(obj, dict):
        return obj.get(attr)
    return getattr(obj, attr, None)


def _as_sequence(obj: Any, attr: str) -> list[Any]:
    value = _get_value(obj, attr)
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _summarize_vendor_results(vendors: list[Any], metric_calls: int | None = None) -> dict[str, Any]:
    total = len(vendors)
    emails = [len(_as_sequence(v, "contact_emails")) for v in vendors]
    phones = [len(_as_sequence(v, "phone_numbers")) for v in vendors]
    geos = [len(_as_sequence(v, "countries_served")) for v in vendors]
    names = {
        (_get_value(v, "name") or "").strip().lower()
        for v in vendors
        if _get_value(v, "name")
    }

    summary = {
        "vendor.result.count": total,
        "vendor.result.with_email": sum(1 for count in emails if count > 0),
        "vendor.result.with_phone": sum(1 for count in phones if count > 0),
        "vendor.result.with_geo": sum(1 for count in geos if count > 0),
        "vendor.result.emails.total": sum(emails),
        "vendor.result.phones.total": sum(phones),
        "vendor.result.countries.total": sum(geos),
        "vendor.result.unique_names": len(names),
    }

    if metric_calls is not None:
        summary["gepa.metric_calls.actual"] = metric_calls

    return summary


def _summarize_pestle_analysis(analysis: Any | None) -> dict[str, Any]:
    if analysis is None:
        return {"pestle.has_analysis": False}

    summary = {
        "pestle.has_analysis": True,
        "pestle.region": _get_value(analysis, "region") or "Global",
        "pestle.opportunities": len(_as_sequence(analysis, "opportunities")),
        "pestle.threats": len(_as_sequence(analysis, "threats")),
        "pestle.recommendations": len(_as_sequence(analysis, "strategic_recommendations")),
        "pestle.has_executive_summary": bool(_get_value(analysis, "executive_summary")),
    }

    for factor in ("political", "economic", "social", "technological", "legal", "environmental"):
        factor_obj = _get_value(analysis, factor)
        key = f"pestle.{factor}.key_insights"
        if factor_obj is None:
            summary[key] = 0
        else:
            summary[key] = len(_as_sequence(factor_obj, "key_insights"))

    return summary
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file

    # Run with PESTLE analysis
    result = run_with_pestle(
        category="General Industrial Supplies",
        n=15,
        country_or_region="United States",
        include_pestle=True
    )

    print(f"\nVendor discovery completed: Found {len(result.vendor_list)} vendors")

    for i, vendor in enumerate(result.vendor_list, 1):
        print(f"{i}. {vendor.name}")
        print(f"   URL: {vendor.website}")
        if vendor.contact_emails and len(vendor.contact_emails) > 0:
            print(f"   Email: {vendor.contact_emails[0].email}")
        if vendor.countries_served:
            print(f"   Serves: {', '.join(vendor.countries_served[:3])}" +
                  (f" + {len(vendor.countries_served)-3} more" if len(vendor.countries_served) > 3 else ""))
        print()

    # Display PESTLE analysis if available
    if result.pestle_analysis:
        print("\n" + "=" * 60)
        print("PESTLE ANALYSIS")
        print("=" * 60)

        pestle = result.pestle_analysis
        print(f"\nExecutive Summary:")
        print(f"{pestle.executive_summary}")

        print(f"\nKey Opportunities:")
        for i, opp in enumerate(pestle.opportunities[:5], 1):
            print(f"  {i}. {opp}")

        print(f"\nKey Threats:")
        for i, threat in enumerate(pestle.threats[:5], 1):
            print(f"  {i}. {threat}")

        print(f"\nStrategic Recommendations:")
        for i, rec in enumerate(pestle.strategic_recommendations[:5], 1):
            print(f"  {i}. {rec}")
