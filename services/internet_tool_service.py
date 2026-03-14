import requests
from bs4 import BeautifulSoup
import os
from typing import List, Dict, Any

class InternetToolService:
    """
    Service for internet search and page summarization.
    """
    
    def __init__(self, gemini_service=None):
        self._gemini = gemini_service
        self._user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search the internet using a public search engine (simulated via requests/bs4 or using a simple API if available).
        For this implementation, we'll use a simple DuckDuckGo-style search or similar.
        """
        try:
            # Using a simplified search approach for robustness
            search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            headers = {"User-Agent": self._user_agent}
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for result in soup.select('.result__body')[:max_results]:
                title_tag = result.select_one('.result__title a')
                snippet_tag = result.select_one('.result__snippet')
                
                if title_tag and snippet_tag:
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "url": title_tag['href'],
                        "snippet": snippet_tag.get_text(strip=True)
                    })
            
            if not results:
                return {"ok": False, "error": "No results found."}
                
            return {"ok": True, "results": results}
            
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def summarize(self, url: str) -> Dict[str, Any]:
        """
        Extract text from a URL and summarize it using Gemini.
        """
        if not self._gemini:
            return {"ok": False, "error": "Gemini service not available for summarization."}
            
        try:
            headers = {"User-Agent": self._user_agent}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean up whitespace
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit text length for Gemini
            truncated_text = clean_text[:8000]
            
            summary_prompt = f"Please provide a concise but comprehensive summary of the following webpage content extracted from {url}:\n\n{truncated_text}"
            
            summary = self._gemini.generate_chat_response(summary_prompt, [])
            
            return {"ok": True, "summary": summary, "url": url}
            
        except Exception as e:
            return {"ok": False, "error": str(e)}
