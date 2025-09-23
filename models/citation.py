"""Citation model for tracking sources across all analyses."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Source citation for traceable claims and insights."""

    url: str = Field(
        ...,
        description="Source URL from Tavily or other web tools"
    )
    title: str = Field(
        ...,
        description="Title of the source page or document"
    )
    snippet: Optional[str] = Field(
        None,
        description="Relevant excerpt from the source supporting the claim"
    )
    tool_call: str = Field(
        default="tavily_search",
        description="Which tool retrieved this (tavily_search, tavily_extract, tavily_crawl, tavily_map)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        description="When this source was retrieved (ISO-8601 format)"
    )
    confidence: Optional[float] = Field(
        None,
        description="Source reliability score (0.0 to 1.0)"
    )

    def citation_id(self) -> str:
        """Generate a unique citation ID from the URL."""
        # Use URL as natural ID for deduplication
        return self.url.lower().replace("https://", "").replace("http://", "").replace("/", "_")[:100]

    def to_markdown(self) -> str:
        """Format citation as markdown link."""
        return f"[{self.title}]({self.url})"

    def to_footnote(self, number: int) -> str:
        """Format as numbered footnote."""
        return f"[^{number}]: {self.title}. {self.url} (accessed {self.timestamp[:10]})"