"""Web search and page fetching tools for the vendor discovery system."""

import logging
from typing import Iterable, Tuple, List, Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tavily import TavilyClient
import dspy
from config.environment import TAVILY_API_KEY, TAVILY_MAX_EXTRACT_CALLS
from models.citation import Citation


logger = logging.getLogger(__name__)

_extract_call_count = 0


def _get_extract_warning_threshold(limit: int) -> int:
    """Return remaining-call threshold at which we should warn the agent."""
    if limit <= 0:
        return 0
    return min(3, max(1, limit // 5))


def _format_extract_warning(remaining: int, limit: int) -> str:
    """Return a human-friendly warning about remaining extract calls."""
    if remaining <= 0:
        return (
            f"⚠️ tavily_extract budget exhausted: no calls remaining out of {limit}. "
            "Further tavily_extract usage will raise an error."
        )

    return (
        f"⚠️ tavily_extract budget nearly exhausted: {remaining} call(s) remaining out of {limit}. "
        "Prefer tavily_search snippets or cache results before extracting again."
    )


def _normalize_url(url: str) -> str:
    """Return a normalized representation for caching purposes."""
    text = (url or "").strip()
    if not text:
        return ""
    candidate = text if "://" in text else f"https://{text}"
    try:
        parsed = httpx.URL(candidate)
    except Exception:  # pragma: no cover - invalid URLs should not crash tools
        return text.lower()
    return str(parsed.copy_with(fragment=""))


def _domain_from_url(url: str) -> str:
    normalized = _normalize_url(url)
    try:
        return httpx.URL(normalized).host or normalized
    except Exception:  # pragma: no cover - fall back to normalized when parsing fails
        return normalized


def _ensure_url_list(urls) -> list[str]:
    """Coerce tavily_extract inputs into a list for caching and validation."""
    if isinstance(urls, str):
        return [urls]
    if urls is None:
        return []
    if isinstance(urls, Iterable):
        return [str(u) for u in urls if u]
    raise TypeError("tavily_extract expects a string or iterable of strings")


def search_web(query: str, max_results: int = 20):
    """
    Search the web using Tavily API.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of dictionaries with title, url, and snippet suitable for agent triage
    """
    tav = TavilyClient(api_key=TAVILY_API_KEY)
    r = tav.search(query=query, max_results=max_results, include_answer=False)
    return [{"title": it.get("title",""), "url": it["url"], "snippet": it.get("content","")}
            for it in r.get("results", [])]


def create_citation_from_tavily(
    result: Dict[str, Any],
    tool_call: str = "tavily_search",
    confidence: Optional[float] = None
) -> Citation:
    """
    Create a Citation object from a Tavily result.

    Args:
        result: Tavily result dict with url, title, content/snippet
        tool_call: Which Tavily tool was used
        confidence: Optional confidence score

    Returns:
        Citation object with source information
    """
    return Citation(
        url=result.get("url", ""),
        title=result.get("title", ""),
        snippet=result.get("content", result.get("snippet", ""))[:500],  # Limit snippet length
        tool_call=tool_call,
        confidence=confidence
    )


# --------------------------------------------------------------------------- #
# Public Tavily tool wrappers
# --------------------------------------------------------------------------- #

def tavily_search(query: str, max_results: int = 20, return_citations: bool = False):
    """
    Tavily web search.

    Parameters
    ----------
    query : str
        Search query string.
    max_results : int, optional
        Maximum number of search results (default 20).
    return_citations : bool, optional
        If True, return both results and Citation objects.

    Returns
    -------
    list[dict] or tuple[list[dict], list[Citation]]
        List of results with ``title``, ``url`` and ``snippet`` keys.
        If return_citations is True, also returns Citation objects.
    """
    results = search_web(query=query, max_results=max_results)

    if return_citations:
        citations = [create_citation_from_tavily(r, tool_call="tavily_search") for r in results]
        return results, citations

    return results


def tavily_extract(urls, return_citations: bool = False):
    f"""
    Extract full text / metadata from one or more URLs via Tavily Extract API.
    Results are truncated to 200,000 characters per URL.
    This tool is limited to {TAVILY_MAX_EXTRACT_CALLS} calls per process; adjust
    ``TAVILY_MAX_EXTRACT_CALLS`` in your environment to raise or lower the cap.

    Parameters
    ----------
    urls : str | list[str]
        Single URL or list of URLs to extract (maximum of 3 per call).
    return_citations : bool, optional
        If True, return both results and Citation objects.

    Returns
    -------
    dict or tuple[dict, list[Citation]]
        Mapping ``url`` -> extraction result from Tavily.
        Each result's content is truncated to 200,000 characters.
        If return_citations is True, also returns Citation objects.
    """
    url_list = _ensure_url_list(urls)
    if len(url_list) > 3:
        raise ValueError(
            f"❌ tavily_extract received {len(url_list)} URLs, but the maximum is 3 per call.\n\n"
            f"💡 RECOMMENDATION: Are you sure you need to extract the full content of that many pages? "
            f"Typically only a few pages are needed. The tool allows a maximum of 3 URLs per call. "
            f"Try extracting 1-3 most relevant pages first, review the content, then decide if more are needed.\n\n"
            f"📋 You provided: {url_list}\n"
            f"✅ SOLUTION: Call tavily_extract with only the first 3 URLs, or better yet, "
            f"prioritize and select the most relevant ones."
        )
    if not url_list:
        if return_citations:
            return {"results": []}, []
        return {"results": []}

    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY)
        resp = tav.extract(urls=url_list)

        # Truncate content for each URL result to 200,000 characters
        if isinstance(resp, dict):
            results = resp.get("results")
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        # Truncate raw_content if present
                        if "raw_content" in item and item["raw_content"]:
                            item["raw_content"] = item["raw_content"][:200000]
                        # Truncate content if present
                        if "content" in item and item["content"]:
                            item["content"] = item["content"][:200000]

        if return_citations:
            citations = []
            if isinstance(resp, dict) and "results" in resp:
                for result in resp["results"]:
                    if isinstance(result, dict):
                        citations.append(create_citation_from_tavily(
                            result,
                            tool_call="tavily_extract",
                            confidence=0.9  # Extract is more reliable than search
                        ))
            return resp, citations

        return resp
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Tavily extract failed: {e}") from e


def tavily_crawl(url, max_depth: int = 1, max_pages: int = 25):
    """
    Crawl one seed URL and collect discovered links/content.

    Parameters
    ----------
    url : str
        Seed URL to start crawling.
    max_depth : int, optional
        How many link-hops deep to follow (default 1).
    max_pages : int, optional
        Max pages to fetch (default 25).

    Returns
    -------
    dict
        Crawl job summary returned by Tavily.
    """

    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY)
        return tav.crawl(url=url, max_depth=max_depth, max_pages=max_pages)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Tavily crawl failed: {e}") from e


def tavily_map(url, max_results: int = 10):
    """
    Tavily Map traverses websites like a graph and can explore hundreds of paths in parallel with intelligent discovery to generate comprehensive site maps.

    Parameters
    ----------
    url : str
        Seed URL to start crawling.
    max_results : int, optional
        Number of results per query (default 10).

    Returns
    -------
    dict
        Map response with nodes/edges describing relationships.
    """
    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY)
        return tav.map(url=url, max_results=max_results)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Tavily map failed: {e}") from e


# --------------------------------------------------------------------------- #
# DSPy tool call guards to limit redundant Tavily usage
# --------------------------------------------------------------------------- #

def _tool_tavily_extract(urls):
    url_list = _ensure_url_list(urls)
    if not url_list:
        return {"results": []}

    # Check URL count limit BEFORE checking budget
    if len(url_list) > 3:
        raise ValueError(
            f"❌ tavily_extract received {len(url_list)} URLs, but the maximum is 3 per call.\n\n"
            f"💡 RECOMMENDATION: Are you sure you need to extract the full content of that many pages? "
            f"Typically only a few pages are needed. The tool allows a maximum of 3 URLs per call. "
            f"Try extracting 1-3 most relevant pages first, review the content, then decide if more are needed.\n\n"
            f"📋 You provided: {url_list}\n"
            f"✅ SOLUTION: Call tavily_extract with only the first 3 URLs, or better yet, "
            f"prioritize and select the most relevant ones."
        )

    global _extract_call_count
    limit = TAVILY_MAX_EXTRACT_CALLS
    if limit <= 0:
        message = (
            "❌ tavily_extract is disabled because TAVILY_MAX_EXTRACT_CALLS is set to 0.\n\n"
            "💡 RECOMMENDATION: Increase TAVILY_MAX_EXTRACT_CALLS in your environment or rely on tavily_search snippets."
        )
        logger.error(message)
        raise RuntimeError(message)

    if _extract_call_count >= limit:
        message = (
            f"❌ tavily_extract budget exhausted. Limit of {limit} calls reached for this run.\n\n"
            "💡 RECOMMENDATION: Reduce extract usage, cache prior results, or increase TAVILY_MAX_EXTRACT_CALLS."
        )
        logger.error(message)
        raise RuntimeError(message)

    threshold = _get_extract_warning_threshold(limit)
    remaining_before_call = limit - _extract_call_count
    if threshold and remaining_before_call <= threshold:
        logger.warning(_format_extract_warning(remaining_before_call, limit))

    arg = urls if isinstance(urls, str) else url_list
    response = tavily_extract(arg)
    _extract_call_count += 1
    remaining_after_call = max(limit - _extract_call_count, 0)
    if threshold and remaining_after_call <= threshold:
        warning_message = _format_extract_warning(remaining_after_call, limit)
        logger.warning(warning_message)
        if isinstance(response, dict):
            warnings = response.setdefault("warnings", [])
            if isinstance(warnings, list):
                warnings.append(warning_message)
            else:
                response["warnings"] = [warning_message]
    return response


def _tool_tavily_crawl(url: str, max_depth: int = 1, max_pages: int = 25):
    response = tavily_crawl(url, max_depth=max_depth, max_pages=max_pages)
    return response


def _tool_tavily_map(url: str, max_results: int = 10):
    response = tavily_map(url, max_results=max_results)
    return response


# Create DSPy tools
def create_dspy_tools():
    """
    Create and return DSPy Tool instances for Tavily operations.

    Returns
    -------
    tuple[dspy.Tool, ...]
        (search, extract, crawl, map) tools.
    """
    search_tool = dspy.Tool(
        tavily_search,
        name="tavily_search",
        desc="Tavily web search. provides text snippets from pages. accurate queries should provide all the information you need for your retreival efforts. Args: query:str, max_results:int=20 -> list of results",
    )
    extract_tool = dspy.Tool(
        _tool_tavily_extract,
        name="tavily_extract",
        desc=(
            f"Extract page content (budgeted, limit {TAVILY_MAX_EXTRACT_CALLS} calls). "
            "Use sparingly. tavily_search provides text snippets. only use this when search does not provide what you need. "
            "Args: urls:list[str]|str -> dict"
        ),
    )
    crawl_tool = dspy.Tool(
        _tool_tavily_crawl,
        name="tavily_crawl",
        desc="Crawl site. DO NOT USE unless necessary. Args: url:str, max_depth:int=1, max_pages:int=25 -> dict",
    )
    map_tool = dspy.Tool(
        _tool_tavily_map,
        name="tavily_map",
        desc="Generate site map. DO NOT USE unless necessary. Args: url:str, max_results:int=10 -> dict",
    )
    return search_tool, extract_tool, crawl_tool, map_tool
