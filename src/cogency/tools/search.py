import logging
import time
from typing import Any, Dict, Optional

from ddgs import DDGS

from cogency.errors import ToolError, ValidationError, validate_params
from cogency.tools.base import BaseTool
from cogency.tools.registry import tool
from cogency.utils.results import ToolResult

logger = logging.getLogger(__name__)


@tool
class Search(BaseTool):
    def __init__(self):
        super().__init__(
            name="search",
            description="Search the web using DuckDuckGo for current information and answers to questions.",
            emoji="🔍",
            schema="search(query='specific search terms', max_results=5)\nRequired: query | Optional: max_results (1-10)",
            examples=[
                "search(query='latest AI developments 2024')",
                "search(query='Python async programming', max_results=3)",
                "search(query='weather London today')",
            ],
            rules=[
                "Use specific queries, avoid repetitive searches",
            ],
        )
        self._last_search_time = 0
        self._min_delay = 1.0  # Simple rate limit

    async def run(self, query: str, max_results: int = None, **kwargs) -> Dict[str, Any]:
        if max_results is None:
            max_results = 5
        # Input validation
        validate_params({"query": query}, ["query"], self.name)
        if not isinstance(max_results, int) or max_results <= 0:
            raise ValidationError(
                "max_results must be a positive integer",
                error_code="INVALID_MAX_RESULTS",
                details={
                    "max_results": max_results,
                    "type": type(max_results).__name__,
                },
            )
        if max_results > 10:
            max_results = 10  # Cap at 10 results
        # Rate limiting
        import asyncio

        current_time = time.time()
        time_since_last = current_time - self._last_search_time
        if time_since_last < self._min_delay:
            await asyncio.sleep(self._min_delay - time_since_last)
        # Perform search
        ddgs = DDGS()
        try:
            results = list(ddgs.text(query, max_results=max_results))
            if not results:
                logger.warning(f"DDGS returned no results for query: {query}")
        except Exception as e:
            logger.error(f"DDGS search failed for query '{query}': {e}")
            raise ToolError(
                f"DuckDuckGo search failed: {str(e)}",
                error_code="SEARCH_FAILED",
                details={"query": query, "max_results": max_results},
            ) from None
        self._last_search_time = time.time()
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "title": result.get("title", "No title"),
                    "snippet": result.get("body", "No snippet available"),
                    "url": result.get("href", "No URL"),
                }
            )
        if not formatted_results:
            return ToolResult(
                {
                    "results": [],
                    "query": query,
                    "total_found": 0,
                    "message": "No results found for your query",
                }
            )
        return ToolResult(
            {
                "results": formatted_results,
                "query": query,
                "total_found": len(formatted_results),
                "message": f"Found {len(formatted_results)} results for '{query}'",
            }
        )

    def format_human(
        self, params: Dict[str, Any], results: Optional[ToolResult] = None
    ) -> tuple[str, str]:
        """Format search execution for human display."""
        from cogency.utils.formatting import truncate

        query = params.get("query", params.get("q", ""))
        param_str = f"({truncate(query, 35)})" if query else ""
        if results is None:
            return param_str, ""
        # Format results
        if results.failure:
            result_str = f"Error: {results.error}"
        else:
            data = results.data
            search_results = data.get("results", [])
            if not search_results:
                result_str = "No results found"
            else:
                result_str = f"Found {len(search_results)} results"
        return param_str, result_str

    def format_agent(self, result_data: Dict[str, Any]) -> str:
        """Format search results for agent action history - show knowledge gained."""
        if not result_data or not isinstance(result_data, dict):
            return "No results"

        query = result_data.get("query", "unknown query")
        search_results = result_data.get("results", [])

        if not search_results:
            return f"'{query}' → No results found"

        # Show knowledge gained from first 2 results
        knowledge_items = []
        for result in search_results[:2]:
            snippet = result.get("snippet", "").strip()
            if snippet:
                # Extract key info from snippet (first 60 chars)
                key_info = snippet[:60].strip()
                if key_info:
                    knowledge_items.append(f"- {key_info}...")

        if knowledge_items:
            knowledge_str = "\n  ".join(knowledge_items)
            return f"'{query}' → Found:\n  {knowledge_str}"
        else:
            # Fallback to titles if no snippets
            titles = [r.get("title", "Untitled") for r in search_results[:2]]
            titles_str = " | ".join(titles)
            return f"'{query}' → {len(search_results)} results: {titles_str}"
