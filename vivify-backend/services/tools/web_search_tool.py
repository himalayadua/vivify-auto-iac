"""
Web Search Tool using Tavily API
"""

from langchain.tools import BaseTool
from typing import Optional
import os

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = """
    Search the web for current information, documentation, or answers to general questions.
    Use this when you need to find recent information about technologies, best practices, or general knowledge.
    
    Input should be a search query string.
    
    Examples:
    - "what is terraform?"
    - "kubernetes best practices"
    - "how to deploy fastapi application"
    """
    
    def __init__(self):
        super().__init__()
        # Store client in a way that doesn't conflict with Pydantic
        api_key = os.getenv("TAVILY_API_KEY")
        object.__setattr__(self, '_client', TavilyClient(api_key=api_key) if api_key and TAVILY_AVAILABLE else None)
    
    def _run(self, query: str) -> str:
        """Execute web search"""
        if not TAVILY_AVAILABLE:
            return "Web search is not available. Tavily package not installed."
        
        client = getattr(self, '_client', None)
        if not client:
            return "Web search is not configured. Please add TAVILY_API_KEY to environment variables."
        
        try:
            results = client.search(query, max_results=3)
            
            if not results.get("results"):
                return "No results found for your query."
            
            # Format results
            summary = []
            for i, result in enumerate(results["results"][:3], 1):
                summary.append(
                    f"{i}. **{result.get('title', 'No title')}**\n"
                    f"   {result.get('content', 'No content')}\n"
                    f"   Source: {result.get('url', 'No URL')}\n"
                )
            
            return "\n".join(summary)
        
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version"""
        return self._run(query)
