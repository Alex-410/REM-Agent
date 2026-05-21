import os
import uuid
import time
import requests
import config


def image_search(query: str, max_results: int = 5) -> dict:
    """Search for images on the web. Uses DuckDuckGo image search."""
    try:
        from ddgs import DDGS
        with DDGS(proxy=config.HTTP_PROXY) as ddgs:
            time.sleep(1)  # Avoid rate limiting
            results = []
            for r in ddgs.images(query, max_results=max(max_results, 10)):
                results.append({
                    "title": r.get("title", ""),
                    "image_url": r.get("image", ""),
                    "thumbnail_url": r.get("thumbnail", ""),
                    "source_url": r.get("url", "")
                })
            return {"query": query, "results": results}
    except ImportError:
        return {"error": "ddgs library not installed. Run: pip install ddgs"}
    except Exception as e:
        return {"error": f"Image search failed: {str(e)}"}


def image_fetch(image_url: str) -> dict:
    """Download an image from a URL and save it locally. Returns a local URL for display."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(
            image_url, headers=headers, timeout=30,
            proxies=config.get_proxies()
        )
        resp.raise_for_status()

        ct = resp.headers.get("content-type", "")
        ext_map = {
            "image/jpeg": ".jpg", "image/png": ".png",
            "image/gif": ".gif", "image/webp": ".webp",
        }
        ext = ext_map.get(ct.split(";")[0].strip(), ".jpg")

        filename = f"{uuid.uuid4().hex}{ext}"
        save_dir = os.path.join("static", "images")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        with open(save_path, "wb") as f:
            f.write(resp.content)

        return {
            "success": True,
            "local_url": f"/static/images/{filename}",
            "size": len(resp.content),
            "content_type": ct
        }
    except Exception as e:
        return {"error": f"Image download failed: {str(e)}"}
