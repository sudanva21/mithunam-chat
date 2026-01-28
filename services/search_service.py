"""
SerpApi search service for real-time data retrieval.
"""

import requests
import time
import re
from config import get_config

config = get_config()


class SearchService:
    """Service for performing SerpApi search queries."""
    
    # Cache for search results
    _cache = {}
    
    # Patterns for detecting real-time queries
    REALTIME_PATTERNS = [
        # Price queries
        r'\b(current|latest|today\'?s?|now|live)\b.*\b(price|value|cost|rate)\b',
        r'\b(price|value|cost|rate)\b.*\b(of|for)\b.*\b(bitcoin|btc|ethereum|eth|crypto|stock|gold|silver)\b',
        r'\b(bitcoin|btc|ethereum|eth|dogecoin|crypto)\b.*\b(price|value|worth)\b',
        r'\bhow much is\b.*\b(bitcoin|btc|ethereum|eth|worth|trading)\b',
        
        # Weather queries
        r'\b(weather|temperature|forecast|rain|sunny|cloudy)\b.*\b(in|at|for)\b',
        r'\b(current|today\'?s?|now)\b.*\b(weather|temperature)\b',
        r'\bweather\b',
        
        # News and current events
        r'\b(latest|recent|current|today\'?s?|breaking)\b.*\b(news|update|headline)\b',
        r'\bwhat\'?s? happening\b',
        
        # Sports scores
        r'\b(score|result|match|game)\b.*\b(today|yesterday|last night)\b',
        r'\bwho won\b.*\b(match|game|today|yesterday)\b',
        
        # Stock market
        r'\b(stock|share|nasdaq|dow|s&p)\b.*\b(price|today|now)\b',
        
        # Time-sensitive queries
        r'\bwhat time is it in\b',
        r'\bcurrent time in\b',
    ]
    
    @classmethod
    def is_realtime_query(cls, query):
        """
        Check if a query requires real-time data.
        
        Args:
            query: The user's question
            
        Returns:
            bool: True if query needs real-time data
        """
        query_lower = query.lower()
        
        for pattern in cls.REALTIME_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    @classmethod
    def search(cls, query, num_results=5):
        """
        Perform a SerpApi search.
        
        Args:
            query: Search query string
            num_results: Number of results to return
            
        Returns:
            dict: Search results with title, snippet, and link
        """
        api_key = config.SERPAPI_KEY
        
        if not api_key:
            print("[Search] SerpApi key not configured")
            return {
                'error': 'Search API not configured',
                'results': [],
                'query': query
            }
        
        # Check cache
        cache_key = f"{query}:{num_results}"
        if cache_key in cls._cache:
            cached_result, cached_time = cls._cache[cache_key]
            if time.time() - cached_time < config.SEARCH_CACHE_TTL:
                print(f"[Search] Using cached result for: {query}")
                return cached_result
        
        try:
            print(f"[Search] Searching SerpApi for: {query}")
            
            url = 'https://serpapi.com/search'
            params = {
                'api_key': api_key,
                'q': query,
                'engine': 'google',
                'num': min(num_results, 10)
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for SerpApi errors
            if 'error' in data:
                print(f"[Search] SerpApi error: {data['error']}")
                return {
                    'error': data['error'],
                    'results': [],
                    'query': query
                }
            
            results = []
            
            # Get answer box if available (for direct answers like prices)
            answer_box = data.get('answer_box', {})
            if answer_box:
                answer = answer_box.get('answer') or answer_box.get('snippet') or answer_box.get('result')
                if answer:
                    results.append({
                        'title': answer_box.get('title', 'Quick Answer'),
                        'snippet': str(answer),
                        'link': '',
                        'displayLink': 'Google Answer Box',
                        'type': 'answer_box'
                    })
            
            # Get knowledge graph if available
            knowledge_graph = data.get('knowledge_graph', {})
            if knowledge_graph:
                kg_title = knowledge_graph.get('title', '')
                kg_description = knowledge_graph.get('description', '')
                if kg_title or kg_description:
                    results.append({
                        'title': kg_title,
                        'snippet': kg_description,
                        'link': knowledge_graph.get('website', ''),
                        'displayLink': 'Knowledge Graph',
                        'type': 'knowledge_graph'
                    })
            
            # Get organic results
            for item in data.get('organic_results', [])[:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'link': item.get('link', ''),
                    'displayLink': item.get('displayed_link', ''),
                    'type': 'organic'
                })
            
            result = {
                'results': results,
                'query': query,
                'total_results': data.get('search_information', {}).get('total_results', '0')
            }
            
            # Cache the result
            cls._cache[cache_key] = (result, time.time())
            
            print(f"[Search] Found {len(results)} results for: {query}")
            return result
            
        except requests.exceptions.Timeout:
            print(f"[Search] Timeout for query: {query}")
            return {
                'error': 'Search request timed out',
                'results': [],
                'query': query
            }
        except requests.exceptions.RequestException as e:
            print(f"[Search] Request error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[Search] Response status: {e.response.status_code}")
                try:
                    print(f"[Search] Response body: {e.response.text[:500]}")
                except:
                    pass
            return {
                'error': f'Search request failed: {str(e)}',
                'results': [],
                'query': query
            }
        except Exception as e:
            print(f"[Search] Unexpected error: {e}")
            return {
                'error': f'Unexpected error: {str(e)}',
                'results': [],
                'query': query
            }
    
    @classmethod
    def format_for_context(cls, search_results):
        """
        Format search results for inclusion in AI context.
        
        Args:
            search_results: Results from search() method
            
        Returns:
            str: Formatted string for AI context
        """
        if search_results.get('error'):
            return f"[Search unavailable: {search_results['error']}]"
        
        results = search_results.get('results', [])
        if not results:
            return "[No search results found]"
        
        formatted = f"[Real-time search results for '{search_results['query']}':\n"
        
        for i, result in enumerate(results[:5], 1):
            result_type = result.get('type', 'organic')
            
            if result_type == 'answer_box':
                formatted += f"\n📊 DIRECT ANSWER: {result['snippet']}\n"
            elif result_type == 'knowledge_graph':
                formatted += f"\n📌 {result['title']}: {result['snippet']}\n"
            else:
                formatted += f"\n{i}. {result['title']}\n"
                formatted += f"   Source: {result['displayLink']}\n"
                formatted += f"   {result['snippet']}\n"
        
        formatted += "\nPlease use this real-time information to provide an accurate, up-to-date answer.]"
        
        return formatted
    
    @classmethod
    def clear_cache(cls):
        """Clear the search cache."""
        cls._cache.clear()
