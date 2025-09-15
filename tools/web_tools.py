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


def tavily_extract(urls, timeout: float = 10.0, extract_depth: str = "basic"):
    """
    Extract full text / metadata from one or more URLs via Tavily Extract API.

    Parameters
    ----------
    urls : str | list[str]
        Single URL or list of URLs to extract.
    timeout : float, optional
        Request timeout per URL in seconds (default 10.0).
    extract_depth : {\"basic\", \"advanced\"}, optional
        Extraction depth (see Tavily docs). \"advanced\" may consume extra credits.

    Returns
    -------
    dict
        Mapping ``url`` → extraction result from Tavily.
    """
    if isinstance(urls, str):
        urls = [urls]
    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY, timeout=timeout)
        resp = tav.extract(urls=urls, extract_depth=extract_depth)
        return resp
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f\"Tavily extract failed: {e}\") from e


def tavily_crawl(urls, max_depth: int = 1, max_pages: int = 25, timeout: float = 10.0):
    """
    Crawl one or more seed URLs and collect discovered links/content.

    Parameters
    ----------
    urls : str | list[str]
        Seed URL(s) to start crawling.
    max_depth : int, optional
        How many link-hops deep to follow (default 1).
    max_pages : int, optional
        Max pages to fetch (default 25).
    timeout : float, optional
        Request timeout per request (default 10.0).

    Returns
    -------
    dict
        Crawl job summary returned by Tavily.
    """
    if isinstance(urls, str):
        urls = [urls]
    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY, timeout=timeout)
        return tav.crawl(urls=urls, max_depth=max_depth, max_pages=max_pages)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f\"Tavily crawl failed: {e}\") from e


def tavily_map(queries, max_results: int = 10, timeout: float = 10.0):
    """
    Build a knowledge map for given queries using Tavily Map endpoint.

    Parameters
    ----------
    queries : str | list[str]
        Topic(s) to map.
    max_results : int, optional
        Number of results per query (default 10).
    timeout : float, optional
        Request timeout (default 10.0).

    Returns
    -------
    dict
        Map response with nodes/edges describing relationships.
    """
    if isinstance(queries, str):
        queries = [queries]
    try:
        tav = TavilyClient(api_key=TAVILY_API_KEY, timeout=timeout)
        return tav.map(queries=queries, max_results=max_results)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f\"Tavily map failed: {e}\") from e


def get_page(url: str, timeout: float = 12.0):
    """
    Fetch and parse a web page.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with url, title, text, and links extracted from the page
    """
    if url in _page_cache: 
        return _page_cache[url]
    
    with httpx.Client(follow_redirects=True, timeout=timeout,
                      headers={"User-Agent": "SupplyChainAgent/1.0"}) as client:
        r = client.get(url)
        r.raise_for_status()
    
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Remove script, style, and noscript tags
    for tag in soup(["script","style","noscript"]): 
        tag.decompose()
    
    # Extract text
    text = " ".join(soup.get_text(" ").split())
    
    # Extract links
    links = []
    for a in soup.find_all("a", href=True):
        links.append({
            "text": " ".join(a.stripped_strings)[:120], 
            "href": urljoin(url, a["href"])
        })
    
    page = {
        "url": str(r.url), 
        "title": (soup.title.string.strip() if soup.title else ""), 
        "text": text, 
        "links": links
    }
    
    _page_cache[page["url"]] = page
    return page


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
        name=\"tavily_search\",
        desc=\"Tavily web search. Args: query:str, max_results:int=20 -> list of results\",
    )
    extract_tool = dspy.Tool(
        tavily_extract,
        name=\"tavily_extract\",
        desc=\"Extract page content. Args: urls:list[str]|str, extract_depth:str='basic' -> dict\",
    )
    crawl_tool = dspy.Tool(
        tavily_crawl,
        name=\"tavily_crawl\",
        desc=\"Crawl site(s). Args: urls:list[str]|str, max_depth:int=1, max_pages:int=25 -> dict\",
    )
    map_tool = dspy.Tool(
        tavily_map,
        name=\"tavily_map\",
        desc=\"Knowledge map. Args: queries:list[str]|str, max_results:int=10 -> dict\",
    )
    return search_tool, extract_tool, crawl_tool, map_tool