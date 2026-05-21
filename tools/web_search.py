import time
import config


def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web using DuckDuckGo API (ddgs library)."""
    try:
        from ddgs import DDGS
        with DDGS(proxy=config.HTTP_PROXY) as ddgs:
            time.sleep(1)
            results = []
            for r in ddgs.text(query, max_results=max(max_results, 5)):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            return {"query": query, "results": results}
    except ImportError:
        return {"error": "ddgs library not installed. Run: pip install ddgs"}
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}
