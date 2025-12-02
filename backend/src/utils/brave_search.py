"""
Brave Search API Tool

A wrapper for the Brave Search Web Search API.
Brave Search provides a fast, reliable search API with generous free tier.
"""

import requests
from typing import Optional
import os


class BraveSearch:
    """Search tool using Brave Search API."""
    
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"
    
    def __init__(self, api_key: Optional[str] = None, count: int = 5):
        """
        Initialize Brave Search.
        
        Args:
            api_key: Brave Search API key (reads from env if not provided)
            count: Number of results to return (max 20)
        """
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Brave Search API key not found. "
                "Please set BRAVE_API_KEY in your .env file or pass it to BraveSearch(api_key='...')"
            )
        
        self.count = min(count, 20)  # Brave API max is 20
        
    def search(self, query: str) -> str:
        """
        Search using Brave Search API.
        
        Args:
            query: Search query string
            
        Returns:
            Formatted search results as a string
        """
        try:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            
            params = {
                "q": query,
                "count": self.count,
            }
            
            response = requests.get(
                self.BASE_URL,
                headers=headers,
                params=params,
                timeout=10
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                return (
                    f"Error: Brave Search API rate limit exceeded. "
                    f"You have used your monthly quota of queries. "
                    f"Please check your API usage at https://brave.com/search/api/"
                )
            
            # Handle other errors
            if response.status_code != 200:
                return (
                    f"Error: Brave Search API returned status {response.status_code}. "
                    f"Message: {response.text}"
                )
            
            data = response.json()
            
            # Extract web results
            web_results = data.get("web", {}).get("results", [])
            
            if not web_results:
                return f"No results found for query: '{query}'"
            
            # Format results for the LLM
            formatted_results = []
            for i, result in enumerate(web_results, 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                description = result.get("description", "No description available")
                
                formatted_results.append(
                    f"{i}. {title}\n"
                    f"   URL: {url}\n"
                    f"   {description}\n"
                )
            
            return "\n".join(formatted_results)
            
        except requests.exceptions.Timeout:
            return f"Error: Request timed out while searching for '{query}'"
        except requests.exceptions.RequestException as e:
            return f"Error: Network error occurred: {str(e)}"
        except Exception as e:
            return f"Error: Unexpected error during search: {str(e)}"
    
    def run(self, query: str) -> str:
        """
        Run search (alias for compatibility with LangChain Tool interface).
        
        Args:
            query: Search query string
            
        Returns:
            Formatted search results as a string
        """
        return self.search(query)


# Convenience function for direct usage
def brave_search(query: str, api_key: Optional[str] = None, count: int = 5) -> str:
    """
    Perform a Brave Search.
    
    Args:
        query: Search query string
        api_key: Optional API key (reads from env if not provided)
        count: Number of results to return
        
    Returns:
        Formatted search results as a string
    """
    searcher = BraveSearch(api_key=api_key, count=count)
    return searcher.search(query)


if __name__ == "__main__":
    # Test the search
    print("Testing Brave Search API...")
    print("\n" + "="*80 + "\n")
    
    try:
        query = "AI fitness apps market trends"
        results = brave_search(query, count=3)
        print(f"Query: {query}\n")
        print(results)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set BRAVE_API_KEY in your .env file")
