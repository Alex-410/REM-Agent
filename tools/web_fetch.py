import requests
from bs4 import BeautifulSoup
import config


def web_fetch(url: str) -> dict:
    """Fetch and extract the main text content from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(
            url, headers=headers, timeout=30,
            proxies=config.get_proxies()
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        title = soup.title.string.strip() if soup.title else url
        text = soup.get_text(separator="\n", strip=True)
        text = "\n".join(line for line in text.splitlines() if line.strip())[:8000]
        return {"url": url, "title": title, "content": text}
    except requests.Timeout:
        return {"error": "Request timed out"}
    except requests.RequestException as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}
