import httpx
import pytest

from lexi_lens.scraper import ScrapeError, _extract, scrape_article, validate_url


def test_rejects_non_lexi_and_http_urls() -> None:
    with pytest.raises(ScrapeError, match="HTTPS"):
        validate_url("http://lexi.hr/post")
    with pytest.raises(ScrapeError, match="Only lexi.hr"):
        validate_url("https://example.com/post")
    validate_url("https://www.lexi.hr/post")


def test_extracts_main_article_without_navigation() -> None:
    paragraphs = " ".join(
        ["Ovo je sadržaj probnog članka s dovoljno riječi za pouzdanu ekstrakciju."] * 25
    )
    html = f"""
    <html><head><meta property="og:title" content="Naslov testa">
    <meta name="author" content="Ana"></head>
    <body><nav>Proizvodi Blog Kontakt</nav><article><h1>Naslov testa</h1>
    <p>{paragraphs}</p></article>
    <footer>Copyright i newsletter</footer></body></html>
    """
    article = _extract("https://lexi.hr/test", html)
    assert article.title == "Naslov testa"
    assert article.author == "Ana"
    assert "sadržaj probnog članka" in article.text
    assert "Copyright i newsletter" not in article.text


@pytest.mark.asyncio
async def test_revalidates_redirect_target() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "lexi.hr":
            return httpx.Response(302, request=request, headers={"location": "https://example.com"})
        return httpx.Response(200, request=request, headers={"content-type": "text/html"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        with pytest.raises(ScrapeError, match="Only lexi.hr"):
            await scrape_article("https://lexi.hr/post", client=client)
