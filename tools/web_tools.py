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
    """Create DSPy tool instances for web search and page fetching."""
    search_tool = dspy.Tool(search_web, name="search_web", desc="Web search")
    fetch_tool = dspy.Tool(get_page, name="get_page", desc="Fetch a page: title, text, links")
    return search_tool, fetch_tool