import re
import httpx

async def look(website):
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        try:
            raw = await client.get(website)
        except (httpx.TimeoutException, httpx.RequestError):
            return None
        match = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw.text)
        emails = list(set(match)) if match else None # avoid duplicates
        return emails