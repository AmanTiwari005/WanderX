try:
    from ddgs import DDGS
    _HAS_DDGS = True
except ImportError:
    _HAS_DDGS = False

try:
    from googlesearch import search as g_search
    _HAS_GOOGLE = True
except ImportError:
    _HAS_GOOGLE = False

try:
    import wikipedia
    _HAS_WIKI = True
except ImportError:
    _HAS_WIKI = False

import time
import logging

logger = logging.getLogger(__name__)

def search_web(query, max_results=5, region="wt-wt"):
    """
    Performs a web search using DuckDuckGo, falling back to Google.
    """
    results = []
    
    # 1. Try DuckDuckGo
    if _HAS_DDGS:
        try:
            with DDGS(timeout=20) as ddgs:
                # DDGS might return a generator
                ddg_gen = ddgs.text(query, region=region, max_results=max_results)
                if ddg_gen:
                    results = list(ddg_gen)
        except Exception as e:
            logger.warning(f"DuckDuckGo Search failed: {e}")
            results = []

    # 2. Fallback to Google if DDG empty/failed
    if not results and _HAS_GOOGLE:
        try:
            # googlesearch-python's search(advanced=True) returns objects with title/description
            # Note: The library name is `googlesearch-python` but import is `googlesearch`
            # `search` returns a generator of SearchResult objects
            g_gen = g_search(query, num_results=max_results, advanced=True)
            for res in g_gen:
                results.append({
                    "title": res.title,
                    "href": res.url,
                    "body": res.description
                })
        except Exception as e:
            logger.error(f"Google Fallback failed: {e}")

    # 3. Last Resort: Wikipedia
    # Useful for "Paris" or "Eiffel Tower" but not "flights to Paris"
    if not results and _HAS_WIKI:
        try:
            # Simple keyword extraction or just try the query
            # limit to 2 sentences to act as a snippet
            wiki_res = wikipedia.search(query, results=1)
            if wiki_res:
                page_title = wiki_res[0]
                summary = wikipedia.summary(page_title, sentences=3)
                url = wikipedia.page(page_title, auto_suggest=False).url
                results.append({
                    "title": f"[Wiki] {page_title}",
                    "href": url,
                    "body": summary
                })
        except Exception as e:
            logger.error(f"Wikipedia Fallback failed: {e}")

    if not results and not _HAS_DDGS and not _HAS_GOOGLE and not _HAS_WIKI:
        logger.error("No search libraries installed/working.")

    return results[:max_results]

def search_news(query, max_results=5, region="wt-wt"):
    """
    Performs a news search using DuckDuckGo, falling back to Google.
    """
    results = []
    
    # 1. Try DuckDuckGo
    if _HAS_DDGS:
        try:
            with DDGS(timeout=20) as ddgs:
                ddg_gen = ddgs.news(query, region=region, max_results=max_results)
                if ddg_gen:
                    results = list(ddg_gen)
        except Exception as e:
            logger.warning(f"DuckDuckGo News failed: {e}")
            results = []

    # 2. Fallback to Google
    if not results and _HAS_GOOGLE:
        try:
            # Reconstruct query for news
            news_query = f"{query} news"
            g_gen = g_search(news_query, num_results=max_results, advanced=True)
            for res in g_gen:
                results.append({
                    "title": res.title,
                    "date": "Recent", # Google search doesn't easily give date
                    "body": res.description,
                    "url": res.url,
                    "source": "Google Result"
                })
        except Exception as e:
             logger.error(f"Google News Fallback failed: {e}")

    return results[:max_results]

