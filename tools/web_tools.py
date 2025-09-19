"""Web search and page fetching tools for the vendor discovery system."""

import logging
from typing import Iterable, Tuple

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tavily import TavilyClient
import dspy
from config.environment import TAVILY_API_KEY


# Global page cache for efficiency
_page_cache: dict[str, dict] = {}

logger = logging.getLogger(__name__)

_MAX_EXTRACT_CALLS = 24
_extract_call_count = 0
_extract_cache: dict[Tuple[str, ...], object] = {}

_crawl_cache: dict[Tuple[str, int, int], object] = {}
_crawl_domain_cache: dict[str, object] = {}

_map_cache: dict[Tuple[str, int], object] = {}
_map_domain_cache: dict[str, object] = {}


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


# --------------------------------------------------------------------------- #
# Public Tavily tool wrappers
# --------------------------------------------------------------------------- #

def tavily_search(query: str, max_results: int = 20):
    """
    Tavily web search.

    Parameters
    ----------
    query : str
        Search query string.
    max_results : int, optional
        Maximum number of search results (default 20).

    Returns
    -------
    list[dict]
        List of results with ``title``, ``url`` and ``snippet`` keys.
    """
    return search_web(query=query, max_results=max_results)


def tavily_extract(urls):
    """
    Extract full text / metadata from one or more URLs via Tavily Extract API.

    Parameters
    ----------
    urls : str | list[str]
        Single URL or list of URLs to extract.

    Returns
    -------
    dict
        Mapping ``url`` -> extraction result from Tavily.
    """
    url_list = _ensure_url_list(urls)
    if not url_list:
        return {"results": []}

    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY)
        resp = tav.extract(urls=url_list)

        # Cache per-URL payloads when possible to avoid duplicate fetches.
        if isinstance(resp, dict):
            results = resp.get("results")
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        key = _normalize_url(item.get("url"))
                        if key:
                            _page_cache[key] = item
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

    normalized_key = tuple(_normalize_url(u) for u in url_list)
    cached = _extract_cache.get(normalized_key)
    if cached is not None:
        logger.debug("tavily_extract cache hit for %s", normalized_key)
        return cached

    global _extract_call_count
    if _extract_call_count >= _MAX_EXTRACT_CALLS:
        logger.warning("tavily_extract budget exhausted; returning cached-only response")
        return {
            "error": "tavily_extract budget exhausted",
            "urls": url_list,
        }

    arg = urls if isinstance(urls, str) else url_list
    response = tavily_extract(arg)
    _extract_cache[normalized_key] = response
    _extract_call_count += 1
    return response


def _tool_tavily_crawl(url: str, max_depth: int = 1, max_pages: int = 25):
    normalized_url = _normalize_url(url)
    key = (normalized_url, max_depth, max_pages)
    cached = _crawl_cache.get(key)
    if cached is not None:
        logger.debug("tavily_crawl cache hit for %s", key)
        return cached

    domain = _domain_from_url(normalized_url)
    domain_cached = _crawl_domain_cache.get(domain)
    if domain_cached is not None:
        logger.debug("Reusing cached crawl for domain %s", domain)
        return domain_cached

    response = tavily_crawl(url, max_depth=max_depth, max_pages=max_pages)
    _crawl_cache[key] = response
    _crawl_domain_cache[domain] = response
    return response


def _tool_tavily_map(url: str, max_results: int = 10):
    normalized_url = _normalize_url(url)
    key = (normalized_url, max_results)
    cached = _map_cache.get(key)
    if cached is not None:
        logger.debug("tavily_map cache hit for %s", key)
        return cached

    domain = _domain_from_url(normalized_url)
    domain_cached = _map_domain_cache.get(domain)
    if domain_cached is not None:
        logger.debug("Reusing cached map for domain %s", domain)
        return domain_cached

    response = tavily_map(url, max_results=max_results)
    _map_cache[key] = response
    _map_domain_cache[domain] = response
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
        desc="Tavily web search. Args: query:str, max_results:int=20 -> list of results",
    )
    extract_tool = dspy.Tool(
        _tool_tavily_extract,
        name="tavily_extract",
        desc="Extract page content (cached/budgeted). Args: urls:list[str]|str -> dict",
    )
    crawl_tool = dspy.Tool(
        _tool_tavily_crawl,
        name="tavily_crawl",
        desc="Crawl site at most once per domain. DO NOT USE unless necessary. Args: url:str, max_depth:int=1, max_pages:int=25 -> dict",
    )
    map_tool = dspy.Tool(
        _tool_tavily_map,
        name="tavily_map",
        desc="Generate site map at most once per domain. DO NOT USE unless necessary. Args: url:str, max_results:int=10 -> dict",
    )
    return search_tool, extract_tool, crawl_tool, map_tool
