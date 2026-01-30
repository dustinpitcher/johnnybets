"""
X/Twitter Search Tool using xAI Agentic API

Uses Grok's native X search tool for real-time sports betting intel:
- Injury reports from beat reporters
- Insider news and breaking updates
- Line movement chatter from sharps
- Weather updates
- Team announcements

Reference: https://docs.x.ai/docs/guides/tools/overview
"""
import os
import time
import requests
from typing import Optional, List, Dict, Any, Tuple


# =============================================================================
# Exact-Query Cache for X Search Results
# =============================================================================
# Simple in-memory cache with TTL to avoid redundant API calls for identical queries.
# Only exact query+context matches hit cache (no fuzzy matching for safety).

_SEARCH_CACHE: Dict[str, Tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _cache_key(query: str, context: str) -> str:
    """Generate cache key from exact query and context."""
    return f"{query}|{context}"


def _get_cached(query: str, context: str) -> Optional[str]:
    """Get cached result if exists and not expired."""
    key = _cache_key(query, context)
    if key in _SEARCH_CACHE:
        result, timestamp = _SEARCH_CACHE[key]
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            return result
        else:
            del _SEARCH_CACHE[key]  # Expired
    return None


def _set_cache(query: str, context: str, result: str):
    """Cache result for exact query."""
    key = _cache_key(query, context)
    _SEARCH_CACHE[key] = (result, time.time())


class XSearchClient:
    """
    Client for searching X/Twitter via xAI's native agentic tools.
    
    Uses the Responses API with x_search tool enabled for authentic
    X/Twitter search results (not just LLM-generated responses).
    """
    
    # Recommended model for agentic tool calling per xAI docs
    MODEL = "grok-4-1-fast"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY required for X search")
        
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _make_request(self, messages: List[Dict], tools: List[Dict], retries: int = 1) -> Dict[str, Any]:
        """Make a request to the xAI Responses API with tools.
        
        Args:
            messages: Chat messages
            tools: Tools to enable
            retries: Number of retry attempts on timeout (default 1)
        """
        import time
        
        payload = {
            "model": self.MODEL,
            "input": messages,
            "tools": tools,
            "temperature": 0.7,
        }
        
        last_error = None
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/responses",
                    headers=self.headers,
                    json=payload,
                    timeout=45  # Increased for xAI API reliability
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < retries:
                    print(f"   [X Search] Timeout, retrying in 5s... (attempt {attempt + 1}/{retries + 1})")
                    time.sleep(5)
            except requests.exceptions.RequestException as e:
                # Don't retry on non-timeout errors
                raise
        
        # All retries exhausted
        raise last_error
    
    def _extract_text_response(self, response: Dict) -> str:
        """Extract the text response from the API response."""
        output = response.get("output", [])
        text_parts = []
        
        for item in output:
            if item.get("type") == "message":
                content = item.get("content", [])
                for c in content:
                    if c.get("type") == "output_text":
                        text_parts.append(c.get("text", ""))
        
        return "\n".join(text_parts) if text_parts else "No results found"
    
    def _extract_citations(self, response: Dict) -> List[str]:
        """Extract citation URLs from the response."""
        output = response.get("output", [])
        citations = []
        
        for item in output:
            if item.get("type") == "message":
                content = item.get("content", [])
                for c in content:
                    if c.get("type") == "refusal":
                        continue
                    annotations = c.get("annotations", [])
                    for ann in annotations:
                        if ann.get("type") == "url_citation":
                            citations.append(ann.get("url", ""))
        
        return citations
    
    def search(self, query: str, context: str = "sports betting") -> str:
        """
        Search X/Twitter for real-time information using native x_search tool.
        
        Args:
            query: Search query (e.g., "Chiefs injury report", "NFL weather")
            context: Context for the search
            
        Returns:
            Grok's response with X/Twitter insights and citations
        """
        # Check cache first
        cached = _get_cached(query, context)
        if cached:
            return cached
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a sports betting research assistant. Search X/Twitter for the most recent and relevant posts FROM THE LAST 24 HOURS ONLY.

Focus on HIGH-VALUE actionable intel:
- Breaking news from verified accounts (team accounts, beat reporters, insiders)
- Injury updates and practice reports with lineup implications
- Weather conditions for outdoor games
- Sharp money/line movement from known cappers

PRIORITIZE: Verified sources, breaking news, injury confirmations. SKIP: Fan speculation, old news, general discussion.

Context: {context}

Provide a CONCISE summary (max 3-5 bullet points) of actionable intel only. Include source attribution."""
            },
            {
                "role": "user",
                "content": f"Search X for: {query}"
            }
        ]
        
        # Enable native X search tool
        tools = [
            {"type": "x_search"}
        ]
        
        try:
            response = self._make_request(messages, tools)
            text = self._extract_text_response(response)
            citations = self._extract_citations(response)
            
            if citations:
                text += "\n\n**Sources:**\n" + "\n".join(f"- {url}" for url in citations[:5])
            
            # Cache successful result
            if not text.startswith("X search error"):
                _set_cache(query, context, text)
            
            return text
        except requests.exceptions.HTTPError as e:
            return f"X search error (HTTP {e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"X search error: {e}"
    
    def search_with_web(self, query: str, context: str = "sports betting") -> str:
        """
        Search both X/Twitter AND the web for comprehensive intel.
        
        Uses both x_search and web_search tools for maximum coverage.
        """
        messages = [
            {
                "role": "system",
                "content": f"""You are a sports betting research assistant with access to X/Twitter and the web.

Search for the most recent and actionable information about the query.
Cross-reference X posts with web sources for accuracy.

Context: {context}

Provide a concise summary highlighting:
1. Breaking news from X (with source attribution)
2. Corroborating web sources if available
3. Any information that could affect betting lines"""
            },
            {
                "role": "user",
                "content": f"Search X and the web for: {query}"
            }
        ]
        
        # Enable both search tools
        tools = [
            {"type": "x_search"},
            {"type": "web_search"}
        ]
        
        try:
            response = self._make_request(messages, tools)
            text = self._extract_text_response(response)
            citations = self._extract_citations(response)
            
            if citations:
                text += "\n\n**Sources:**\n" + "\n".join(f"- {url}" for url in citations[:8])
            
            return text
        except requests.exceptions.HTTPError as e:
            return f"Search error (HTTP {e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Search error: {e}"
    
    def get_injury_report(self, team: str, sport: str = None) -> str:
        """Get latest injury news for a specific team from X.
        
        Args:
            team: Team name or abbreviation
            sport: Sport context (NHL, NBA, NFL, MLB) for disambiguation
        """
        if sport:
            query = f"{sport} {team} injury report practice status"
            context = f"Looking for {sport} {team} injury updates that could affect betting lines"
        else:
            query = f"{team} injury report practice status"
            context = f"Looking for {team} injury updates that could affect betting lines"
        
        return self.search(query, context)
    
    def get_weather_update(self, teams: str) -> str:
        """Get weather conditions for an outdoor game."""
        return self.search(
            f"{teams} game weather conditions forecast",
            context="Weather impact on over/under totals and game script"
        )
    
    def get_line_movement_intel(self, matchup: str) -> str:
        """Get sharp money / line movement chatter from X."""
        return self.search(
            f"{matchup} line movement sharp money betting",
            context="Looking for steam moves, reverse line movement, or sharp action"
        )
    
    def get_breaking_news(self, sport: str = "NFL") -> str:
        """Get breaking sports news that could affect lines."""
        return self.search_with_web(
            f"{sport} breaking news today",
            context=f"Breaking {sport} news that could move betting lines"
        )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("/Users/dustinpitcher/ai_workspace/.env")
    
    try:
        client = XSearchClient()
        print("Testing native X search with grok-4-1-fast...")
        print("=" * 60)
        
        result = client.get_breaking_news("NFL")
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")
