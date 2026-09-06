import re
import httpx
from bs4 import BeautifulSoup

async def look(website):
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        try:
            raw = await client.get(website)
        except (httpx.TimeoutException, httpx.RequestError):
            return None
        match = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw.text)
        emails = list(set(match)) if match else None # avoid duplicates
        return emails

ABOUT_PATHS = ["", "/sobre", "/sobre-nos", "/about", "/about-us", "/quem-somos"]

MAX_CHARS = 3000
MIN_USEFUL_CHARS = 200

def _extract_text(html: str) -> str:
    """Turn raw HTML into plain readable text, stripping the noise an LLM doesn't need."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)