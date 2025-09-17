"""Web search and page fetching tools for the vendor discovery system."""

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tavily import TavilyClient
import dspy
from config.environment import TAVILY_API_KEY


# Global page cache for efficiency
_page_cache: dict[str, dict] = {}


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
        Mapping ``url`` → extraction result from Tavily.
    """
    if isinstance(urls, str):
        urls = [urls]
    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY)
        resp = tav.extract(urls=urls)
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
        tavily_extract,
        name="tavily_extract",
        desc="Extract page content. Args: urls:list[str]|str, extract_depth:str='basic' -> dict",
    )
    crawl_tool = dspy.Tool(
        tavily_crawl,
        name="tavily_crawl",
        desc="Crawl site(s). Args: urls:list[str]|str, max_depth:int=1, max_pages:int=25 -> dict",
    )
    map_tool = dspy.Tool(
        tavily_map,
        name="tavily_map",
        desc="Knowledge map. Args: queries:list[str]|str, max_results:int=10 -> dict",
    )
    return search_tool, extract_tool, crawl_tool, map_tool