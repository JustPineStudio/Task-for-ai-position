from __future__ import annotations

from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from lexi_lens.models import Article

USER_AGENT = "LexiLens/0.1 (+content quality evaluation; contact: repository owner)"


class ScrapeError(RuntimeError):
    pass


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https":
        raise ScrapeError("URL must use HTTPS")
    if host != "lexi.hr" and not host.endswith(".lexi.hr"):
        raise ScrapeError("Only lexi.hr URLs are accepted")


async def scrape_article(url: str, client: httpx.AsyncClient | None = None) -> Article:
    validate_url(url)
    owns_client = client is None
    client = client or httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(20.0),
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
    )
    try:
        response = await client.get(url)
        response.raise_for_status()
        validate_url(str(response.url))
        if "text/html" not in response.headers.get("content-type", ""):
            raise ScrapeError("URL did not return an HTML page")
        return _extract(str(response.url), response.text)
    except httpx.HTTPError as exc:
        raise ScrapeError(f"Could not fetch article: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()


def _extract(url: str, html: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    title = _meta(soup, "property", "og:title") or _meta(soup, "name", "twitter:title")
    if not title:
        title = soup.h1.get_text(" ", strip=True) if soup.h1 else "Untitled article"
    author = _meta(soup, "name", "author")
    published = _meta(soup, "property", "article:published_time")

    text = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_links=False,
        include_images=False,
        include_comments=False,
        favor_precision=True,
    )
    if not text or len(text.split()) < 100:
        raise ScrapeError("Could not identify enough article content on the page")
    return Article(
        url=url, title=title.strip(), author=author, published_at=published, text=text.strip()
    )


def _meta(soup: BeautifulSoup, attribute: str, value: str) -> str | None:
    tag = soup.find("meta", attrs={attribute: value})
    content = tag.get("content") if tag else None
    return str(content).strip() if content else None
