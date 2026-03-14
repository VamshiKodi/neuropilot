"""
WebIntelligenceService - Enhanced web search with optional AI summarization.

Provides real search result fetching (not just opening browser) and
optional Gemini-powered summarization of results.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List


class WebIntelligenceService:
    """
    Fetches web search results and optionally summarizes them using AI.
    
    Uses requests + BeautifulSoup for scraping. Falls back gracefully
    if dependencies are missing or network fails.
    """

    def __init__(self) -> None:
        self._session = None
        self._gemini_service = None
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def _get_session(self):
        """Lazy-load requests session."""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update(self._headers)
            except ImportError:
                return None
        return self._session

    def _extract_query(self, message: str) -> str | None:
        """Extract search query from user message."""
        patterns = [
            r"search\s+(?:the\s+)?web\s+(?:for\s+)?(.+)",
            r"search\s+for\s+(.+)",
            r"search\s+(.+)",
            r"google\s+(.+)",
            r"look\s+up\s+(.+)",
            r"find\s+(.+)",
            r"what\s+is\s+(.+)",
            r"who\s+is\s+(.+)",
            r"how\s+(?:to|do)\s+(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # If no pattern matched, use the whole message (minus common prefixes)
        query = message.strip()
        for prefix in ["search the web", "search web", "search", "google", "look up", "find"]:
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip()
        
        return query if query else None

    def _fetch_google_results(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Fetch search results from Google."""
        session = self._get_session()
        if session is None:
            return []

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={encoded_query}&num={max_results * 2}"
            
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            results: List[Dict[str, str]] = []
            
            # Extract search result containers
            for g in soup.select("div.g, div[data-ved], .yuRUbf")[:max_results]:
                try:
                    # Try multiple selectors for title
                    title_elem = g.select_one("h3, .LC20lb, [data-ved] h3")
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    # Try multiple selectors for link
                    link_elem = g.select_one("a[href], .yuRUbf a")
                    link = ""
                    if link_elem:
                        href = link_elem.get("href", "")
                        if href.startswith("/url?q="):
                            link = href.split("/url?q=")[1].split("&")[0]
                        elif href.startswith("http"):
                            link = href
                    
                    # Try multiple selectors for snippet
                    snippet_elem = g.select_one(".VwiC3b, .s3v94d, [data-ved] .st, span:not([class])")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    if title and link:
                        results.append({
                            "title": title,
                            "url": urllib.parse.unquote(link),
                            "snippet": snippet,
                        })
                except Exception:
                    continue
            
            return results
        except Exception:
            return []

    def _summarize_with_gemini(self, query: str, results: List[Dict[str, str]]) -> str | None:
        """Optional Gemini summarization of search results."""
        if not results:
            return None

        # Lazy-load Gemini service
        if self._gemini_service is None:
            try:
                from services.gemini_service import GeminiService
                self._gemini_service = GeminiService()
            except Exception:
                return None

        try:
            # Build context from results
            context_lines = []
            for i, r in enumerate(results[:5], 1):
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                if title or snippet:
                    context_lines.append(f"[{i}] {title}\n{snippet}")
            
            if not context_lines:
                return None

            context = "\n\n".join(context_lines)
            prompt = (
                "You are a helpful assistant. Based on the following web search results, "
                "provide a concise summary answering the user's query.\n\n"
                f"User query: {query}\n\n"
                f"Search results:\n{context}\n\n"
                "Provide a brief, factual summary in 2-4 sentences. Include relevant details from the sources."
            )

            response = self._gemini_service._client.models.generate_content(
                model=self._gemini_service._model,
                contents=prompt,
            )
            return getattr(response, "text", "").strip() or None
        except Exception:
            return None

    async def search(
        self,
        message: str,
        summarize: bool = False,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Perform web search by opening the browser directly.
        
        Scraping is removed to ensure reliability and avoid blocks.
        """
        import webbrowser
        
        query = self._extract_query(message)
        if not query:
            return {
                "ok": False,
                "query": "",
                "results": [],
                "summary": None,
                "error": "Could not extract search query from message."
            }

        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            
            webbrowser.open(url)
            
            return {
                "ok": True,
                "query": query,
                "results": [],  # Results not fetched via scraping anymore
                "summary": f"Searching the web for: {query}",
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "query": query,
                "results": [],
                "summary": None,
                "error": f"Failed to open browser: {str(e)}"
            }

    def open_browser_search(self, query: str) -> str:
        """Legacy: open browser with Google search (for direct system commands)."""
        import os
        import urllib.parse
        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}"
        os.startfile(url)
        return f"SYSTEM ACTION: Opened browser with search for '{query}'."
