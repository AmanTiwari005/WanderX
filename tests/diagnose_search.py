import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO)

from utils.web_search import search_web

def test_search():
    print("Testing Web Search Module...")
    try:
        from duckduckgo_search import DDGS
        print(f"[Check] duckduckgo-search package found: {DDGS}")
    except ImportError:
        print("[Error] duckduckgo-search NOT found in python environment.")
        return

    try:
        from googlesearch import search as g_search
        print("[Check] googlesearch-python package found.")
        print("Attempting direct Google search...")
        g_results = list(g_search("Paris Travel", num_results=1, advanced=True))
        print(f"Google Direct Count: {len(g_results)}")
        if g_results:
             print(f"  Title: {g_results[0].title}")
    except ImportError:
        print("[Error] googlesearch-python NOT found in python environment.")
    except Exception as e:
        print(f"[Error] Google direct search failed: {e}")

    try:
        import wikipedia
        print("[Check] wikipedia package found.")
        print("Attempting direct Wikipedia search...")
        w_results = wikipedia.search("Paris", results=1)
        print(f"Wikipedia Direct Results: {w_results}")
        if w_results:
             print(f"  Summary: {wikipedia.summary(w_results[0], sentences=1)}")
    except ImportError:
         print("[Error] wikipedia NOT found in python environment.")
    except Exception as e:
         print(f"[Error] Wikipedia direct search failed: {e}")

    print("Attempting combined search query 'Paris Travel'...")
    try:
        results = search_web("Paris Travel", max_results=3)
        print(f"Results type: {type(results)}")
        print(f"Count: {len(results)}")
        
        if results:
            print("[Success] Search returned results.")
            for i, r in enumerate(results):
                try:
                    title = r.get('title', 'No Title')
                    # Handle encoding for printing
                    print(f"  {i+1}. {title.encode('ascii', 'ignore').decode()}")
                except:
                    print(f"  {i+1}. [Print Error]")
        else:
            print("[Warning] Search returned EMPTY list. (Possible blocking/rate limit)")
            
    except Exception as e:
        print(f"[Error] Search failed with exception: {e}")

if __name__ == "__main__":
    test_search()
